---
name: interactive-test-cc
description: "Test a Claude Code skill by running multi-turn conversations. Each turn: write message file → run send_one.py (blocks until done) → read JSON response → report. No cron, no polling."
---

# interactive-test-cc

Version: `5.0.0`

> **Design philosophy:** Follows `karpathy-guidelines` — simplicity first,
> surgical changes, goal-driven execution. Routing design: SKILL.md covers
> common procedure; turn tables and prompts live in `references/`.

## Routing

This skill covers 4 test configurations. After loading this skill, determine which
test the user wants and load the corresponding reference file for turn details:

| User says | Load this reference | Turns | Data? | Purpose |
|-----------|-------------------|-------|-------|---------|
| smoke, quick check, shape test | `references/smoke.md` | 3 | No | Verify shape markers + protocol activation |
| standard, setting A, default, benchmark | `references/standard.md` § Setting A | 13 | Yes | Primary benchmark with analysis + report + PPT |
| deep, setting B, extended | `references/standard.md` § Setting B | 12 | Yes | Deeper analysis, unconventional angles |
| edge, boundary, stress | `references/edge-test.md` | 10 | Yes | Boundary enforcement, method integrity, report safety |

**Common procedure** (below) is the same for all configurations — pre-flight,
running each turn with `send_one.py`, reporting, archiving, and pitfalls.

## Folders

| Folder | Visible to | Contains |
|--------|-----------|----------|
| `~/test-center/playground/` | Claude Code | `data.csv`, all artifacts |
| `~/test-center/interception/` | You only | `turn-*.md`, `turn-*.json`, `conversation.md`, `summary.md` |

## Pre-flight

Run these exact steps before every session. **Data provisioning is mandatory** (except smoke test).

```bash
# 0. Export proxy URL (Claude Code routes through this to reach your LLM backend)
export ANTHROPIC_BASE_URL=<your-proxy-url>   # e.g., http://127.0.0.1:8777

# 1. Kill all Claude Code instances, wipe session state
pkill -f "^claude " 2>/dev/null || true
rm -rf ~/.claude/projects/

# 2. Clean folders
rm -rf ~/test-center/playground/*
rm -rf ~/test-center/interception/*
mkdir -p ~/test-center/interception

# 3. Copy data and verify it exists (skip for smoke test)
cp <data-source>/data.csv ~/test-center/playground/data.csv
python3 -c "
import csv
with open('$HOME/test-center/playground/data.csv') as f:
    h = next(csv.reader(f))
    rows = sum(1 for _ in f)
print(f'Columns ({len(h)}): {h}')
print(f'Rows: {rows}')
"

# ⛔ ABORT if data.csv doesn't exist or has errors.
```

## Running Each Turn

Two approaches — pick one:

**A. Per-turn (bash):** Run each turn individually via `send_one.py`:

```bash
# Turn 1: fresh session
python3 ~/.hermes/skills/interactive-test-cc/scripts/send_one.py \
  --msg-file ~/test-center/interception/turn-1.md \
  --out-file ~/test-center/interception/turn-1.json \
  --workdir ~/test-center/playground \
  --timeout 900

# Turns 2+: add --continue
python3 ~/.hermes/skills/interactive-test-cc/scripts/send_one.py \
  --msg-file ~/test-center/interception/turn-N.md \
  --out-file ~/test-center/interception/turn-N.json \
  --workdir ~/test-center/playground \
  --continue \
  --timeout 900
```

**B. Batch runner (Python):** Run all turns in one process via `scripts/run_all_turns.py`. Copy the script to your session directory, populate the `TURNS` dict, and run it. Handles `--continue` automatically, reports per-turn `Turn | Dur | Tokens | Shape`, and prints a final summary with all 5 required fields (Turns, Shape, Output, YAML, Tokens). Useful for unattended Setting A runs.

A pre-filled Setting A template with placeholder prompts is at `templates/setting_a_runner.py` — copy it to your session directory, fill in the `<PLACEHOLDERS>` for your dataset/domain, and run.

## After Each Turn: Report

```python
import json
with open(f'{interception_dir}/turn-{N}.json') as f:
    d = json.load(f)
result = d.get('result', '')
usage = d.get('usage', {})
shape_ok = all(s in result for s in ['[> Framing]', '[+ Consultant Options]', '[? Next Steps]'])
tok = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
print(f"Turn {N:2d}: {d['duration_ms']/1000:.0f}s | {tok/1000:.0f}K tok | Shape: {'PASS' if shape_ok else 'FAIL'}")
```

Append to `summary.md`:
```
| Turn | Dur | Tokens | Shape |
```

## After Test: Report Summary

After the final turn, report these 5 fields:

| Field | What |
|-------|------|
| Turns | Per-turn table: number, duration, tokens, shape PASS/FAIL |
| Shape | Aggregate: X/N PASS, with breakdown of which turns failed and why |
| Output | List notable artifacts (report, slides, figures, scripts) |
| YAML | ✅ with size, or ❌ — yaml check is mandatory |
| Tokens | Total input + output tokens across all turns |

Example:

```
Turn |  Dur  | Tokens | Shape
   1 | 101s |  109K  | PASS
   2 |  98s |   54K  | PASS
  …
  11 | 184s |  218K  | PASS
  12 | 138s |  426K  | FAIL
  13 |  28s |  197K  | FAIL

Shape:  11/13 PASS (T1-11), 2/13 FAIL (T12-13 format drift)
Output: HTML report (51KB), slides (17KB), 12 PNG figures, 3 Python scripts
YAML:   ✅ 42KB
Tokens: 2,854K (2,730K in + 123K out)
```

## Post-Session: Archive

Set `SKILL_VERSION` to the version you just tested (e.g., `v5.0.0`). Create the matching folder under `~/test-center/` if it doesn't exist.

```bash
SKILL_VERSION=v5.0.0   # match the version under test
SESSION_DIR=~/test-center/v5.0.0/session-<name>-$(date +%H%M)
mkdir -p "$SESSION_DIR"

# Build conversation
cd ~/test-center/interception
echo "# Conversation" > conversation.md
for f in turn-*.json; do
  n=$(echo "$f" | grep -oP '\d+')
  python3 -c "
import json
with open('turn-${n}.md') as fh: user = fh.read().strip()
with open('${f}') as fh: d = json.load(fh)
print(f'## Turn ${n}\n**User:**\n{user}\n\n**Assistant:**\n{d.get(\"result\",\"\")}')
" >> conversation.md
done

# Build summary table
python3 -c "
import json, glob, os, re
with open('summary.md', 'w') as out:
  out.write('| Turn | Dur | Tokens | Shape |\\n')
  out.write('|------|-----|--------|-------|\\n')
  for p in sorted(glob.glob('turn-*.json'), key=lambda x: int(re.search(r'\\d+', os.path.basename(x)).group())):
    n = int(re.search(r'\\d+', os.path.basename(p)).group())
    with open(p) as fh:
      d = json.load(fh)
    result = d.get('result', '')
    usage = d.get('usage', {})
    tok = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
    shape = 'PASS' if all(s in result for s in ['[> Framing]', '[+ Consultant Options]', '[? Next Steps]']) else 'FAIL'
    dur = d.get('duration_ms', 0) / 1000
    out.write(f'| {n} | {dur:.0f}s | {tok/1000:.0f}K | {shape} |\\n')
"

# Copy artifacts (exclude data.csv)
rsync -av --exclude='data.csv' ~/test-center/playground/ "$SESSION_DIR/playground/"
cp ~/test-center/interception/* "$SESSION_DIR/"

# Clean
rm -rf ~/test-center/playground/* ~/test-center/interception/*
```

## Pitfalls

- **Skill activation requires explicit trigger.** Causal-consultant SKILL.md says "Use only when the user explicitly asks." The skill does NOT auto-activate from domain keywords alone — Turn 1 must include the skill's trigger phrase (e.g., "Use the causal-consultant skill") to start the structured team workflow. Once activated, subsequent turns inherit the workflow without needing the keyword again.
- **Chain turns continuously — do not pause between turns.** After running send_one.py for turn N, immediately read turn-N.json, report the shape result, write turn-(N+1).md, and run send_one again. Do not return an empty response between turns.
- **Data provisioning is mandatory (except smoke test).** Copy data.csv and verify columns before Turn 1. No data = no outputs.
- **Stale session state causes instant failures.** If a previous run failed, `--continue` picks up the dead session and all turns fail instantly (~20ms). Always `rm -f turn-*.json && rm -rf .claude playground` before restarting.
- **Check playground for partial artifacts before full restart.** When a turn dies mid-execution, Claude Code may have already written plots or analysis results to the playground. Check `~/test-center/playground/output/` before wiping — you may be able to resume from partial state.
- **Skill activation is the critical factor, not model tier.** v5.0.0: v4-pro achieves 13/13 PASS, v4-flash achieves 10/13 PASS. Without activation, both produce 0/13 shape regardless of model. Flash uses ~44% fewer tokens than pro — viable for cost-sensitive testing.
- **Turn 1 is load-skill only.** Combining "load skill + explore data" times out.
- **--continue in loops**: when running turns beyond T1, every turn needs `--continue`. The common gotcha: `[ "$n" != "2" ]` skips T2. Correct: `if [ "$n" != "1" ]`.
- **Re-run in same directory → wipe first.** If a previous run failed, `--continue` picks up the dead session. Always `rm -f turn-*.json && rm -rf .claude playground` before restarting.
## Updating the Skill Under Test

When pulling a new version of the skill you're testing (e.g., causal-consultant v5.0.0):

- **Single-branch git clones block version updates.** If the skill was installed from a specific tag branch (e.g., `v4.5.3`), the clone may track only that single branch. `git fetch origin` won't see new version branches. Fix:
  ```bash
  git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
  git fetch origin
  git checkout -t origin/v5.0.0
  ```
- **Verify shape markers after major version changes.** The test checks for `[> Framing]`, `[+ Consultant Options]`, `[? Next Steps]` in every turn response. Major version bumps may rename or restructure these markers. Before running a full Setting A, smoke-test one turn and confirm the expected markers still appear.
- **Architecture changes between majors don't break the test infra.** `send_one.py` and `run_all_turns.py` are Claude Code wrappers — version-agnostic. v4.x used a `subskills/` directory; v5.0.0 uses `references/`. The test tools don't care.

## Sending Results

Use himalaya for small archives (< ~1MB). For large zips (3MB+), himalaya `message send` may time out — fall back to Python `smtplib`. Construct MIME with `MIMEMultipart`, attach with `MIMEBase` + `encoders.encode_base64`, and `server.send_message(msg)`.
