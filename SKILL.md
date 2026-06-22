---
name: interactive-test-cc
description: "Test a Claude Code skill by running multi-turn conversations. Each turn: write message file → run send_one.py (blocks until done) → read JSON response → report. No cron, no polling."
---

# interactive-test-cc

Version: `3.12.0`

> **Design philosophy:** Follows `karpathy-guidelines` — simplicity first,
> surgical changes, goal-driven execution. If you're tempted to add more
> procedure text, ask: "Would this survive a 70% reduction?"

You test a Claude Code skill by running a scripted multi-turn conversation.
Only essential mechanics here — settings, method references, and detailed protocols
live in `references/`. If something feels missing, check there first.

You test a Claude Code skill by running a scripted multi-turn conversation.
Every turn is synchronous: write a prompt, call `send_one.py`, read the
JSON response immediately.

## Folders

| Folder | Visible to | Contains |
|--------|-----------|----------|
| `~/test-center/playground/` | Claude Code | `data.csv`, all artifacts |
| `~/test-center/interception/` | You only | `turn-*.md`, `turn-*.json`, `conversation.md`, `summary.md` |

## Pre-flight

Run these exact steps before every session. **Data provisioning is mandatory.**

```bash
# 0. Export proxy URL (MANDATORY — Claude Code routes through this to reach your LLM backend)
export ANTHROPIC_BASE_URL=<your-proxy-url>   # e.g., http://127.0.0.1:15721

# 1. Kill all Claude Code instances, wipe session state
pkill -f "^claude " 2>/dev/null || true
rm -rf ~/.claude/projects/

# 2. Clean folders
rm -rf ~/test-center/playground/*
rm -rf ~/test-center/interception/*
mkdir -p ~/test-center/interception

# 3. Verify proxy health (backend outages masquerade as "Not logged in")
curl -s $ANTHROPIC_BASE_URL/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4","max_tokens":5,"messages":[{"role":"user","content":"ping"}]}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Proxy OK - model:', d.get('model','?'))"
# ⛔ ABORT if proxy returns HTML (521) or error — the backend is down.

# 4. Copy data and verify it exists
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

**B. Batch runner (Python):** Run all turns in one process via `scripts/run_all_turns.py`. Copy the script to your session directory, populate the `TURNS` dict, and run it. Handles `ANTHROPIC_API_KEY` fallback, `--continue` automatically, and reports per-turn timing. Useful for unattended Setting A runs.

## After Each Turn: Report

```python
import json
with open(f'{interception_dir}/turn-{N}.json') as f:
    d = json.load(f)
result = d.get('result', '')
usage = d.get('usage', {})
shape_ok = all(s in result for s in ['[> Framing]', '[+ Consultant Options]', '[? Next Steps]'])
tok = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
print(f"Turn {N}: {d['duration_ms']/1000:.0f}s | {tok:,} tok | Shape: {'PASS' if shape_ok else 'FAIL'}")
```

Append to `summary.md`:
```
| N | Time | Tokens | Shape | Chars | Notes |
```

## Setting A (13-turn, Default)

Precheck gates on analysis (turns 8, 10), report (turn 12), and PPT summary (turn 13). Reports output HTML by default.

| Turn | What you say |
|------|-------------|
| 1 | Load skill, domain opening |
| 2 | Deeper domain question |
| 3 | **"Here is the data — data.csv, take a look"** |
| 4 | Follow up on data exploration |
| 5 | Causal or method question based on data |
| 6 | Probe a specific finding or edge case |
| 7 | **Ask for analysis** |
| 8 | Confirm analysis (precheck gate) |
| 9 | **Ask for additional analysis** |
| 10 | Confirm additional analysis (precheck gate) |
| 11 | **Ask for report** (HTML by default) |
| 12 | Confirm report (precheck gate) |
| 13 | **Ask for a 3-slide PPT summary** |

## Post-Session: Archive

```bash
SESSION_DIR=~/test-center/v4.5.0/session-<name>-$(date +%H%M)
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
  out.write('| Turn | Time | Tokens | Shape | Chars | Notes |\\n')
  out.write('|------|------|--------|-------|-------|-------|\\n')
  for p in sorted(glob.glob('turn-*.json'), key=lambda x: int(re.search(r'\\d+', os.path.basename(x)).group())):
    n = int(re.search(r'\\d+', os.path.basename(p)).group())
    with open(p) as fh:
      d = json.load(fh)
    result = d.get('result', '')
    usage = d.get('usage', {})
    tok = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
    shape = 'PASS' if all(s in result for s in ['[> Framing]', '[+ Consultant Options]', '[? Next Steps]']) else 'FAIL'
    dur = d.get('duration_ms', 0) / 1000
    out.write(f'| {n} | {dur:.0f}s | {tok:,} | {shape} | {len(result):,} | |\\n')
"

# Copy artifacts (exclude data.csv)
rsync -av --exclude='data.csv' ~/test-center/playground/ "$SESSION_DIR/playground/"
cp ~/test-center/interception/* "$SESSION_DIR/"

# Clean
rm -rf ~/test-center/playground/* ~/test-center/interception/*
```

## Pitfalls

- **Skill activation requires explicit trigger.** Causal-consultant SKILL.md says "Use only when the user explicitly asks." The skill does NOT auto-activate from domain keywords alone — Turn 1 must include the skill's trigger phrase (e.g., "Use the causal-consultant skill") to start the structured team workflow (router, next_step_plan, project_state.yaml). Without this, Claude Code produces useful conversation but skips the protocol entirely. Once activated, subsequent turns inherit the workflow without needing the keyword again.
- **Chain turns continuously — do not pause between turns.** After running send_one.py for turn N, immediately read turn-N.json, report the shape result, write turn-(N+1).md, and run send_one again. Do not return an empty response between turns — the user should not have to tell you "process the results and continue." A 13-turn Setting A run should flow from T1 through T13 without interruption.
- **Data provisioning is mandatory.** Copy data.csv and verify columns before Turn 1. No data = no outputs.
- **Background mode needs ANTHROPIC_API_KEY fix.** When running in `terminal(background=true)`, the subprocess chain loses `ANTHROPIC_API_KEY` (not `ANTHROPIC_BASE_URL` — that propagates fine). Claude Code needs *any non-empty* `ANTHROPIC_API_KEY` to pass its "logged in" gate, even when the proxy replaces it. Fix: set `env["ANTHROPIC_API_KEY"] = "dummy"` in the runner script. See `references/foreground-vs-background.md` for diagnostic and verified fix. With this fix, all 13 Setting A turns complete in background (~10 min total).
- **Stale session state causes instant failures.** If a previous run failed, `--continue` picks up the dead session and all turns fail instantly (~20ms) with "Not logged in." Always run `rm -f turn-*.json && rm -rf .claude playground` before restarting in the same directory.
- **Proxy backend outage masquerades as auth failure.** "Not logged in" from Claude Code often means the backend provider is returning an error, not an actual auth issue. Diagnose by curling the proxy directly. If it returns HTML (521), the backend is down. If it returns valid JSON, check `ANTHROPIC_BASE_URL`, session state, or Claude Code auth.
- **Check playground for partial artifacts before full restart.** When a turn dies mid-execution, Claude Code may have already written plots or analysis results to the playground. Check `~/test-center/playground/output/` before wiping — you may be able to resume from partial state.
- **⛔ Flash/light/mini models are incompatible with causal-consultant.** `deepseek-v4-flash` drops all shape-gate markers (`[> Framing]`, `[+ Consultant Options]`, `[? Next Steps]`) and generates standalone Python scripts instead of inline analysis output. Tested: 0/12 PASS with no diagnostic value. Only use **pro-tier models** for testing.
- **Turn 1 is load-skill only.** Combining "load skill + explore data" times out.
- **--continue in loops**: when running turns beyond T1, every turn needs `--continue`. The common gotcha: `[ "$n" != "2" ]` skips T2. Correct: `if [ "$n" != "1" ]`.
- **Re-run in same directory → wipe first.** If a previous run failed, `--continue` picks up the dead session. Always `rm -f turn-*.json && rm -rf .claude playground` before restarting.

## Other Settings

See `references/settings.md` for the smoke test (4 turns, no data).
