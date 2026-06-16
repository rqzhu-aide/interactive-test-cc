---
name: interactive-test-cc
description: "Test a Claude Code skill by running multi-turn conversations. Each turn: write message file → run send_one.py (blocks until done) → read JSON response → report. No cron, no polling."
---

# interactive-test-cc

Version: `3.5.0`

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
# 1. Kill all Claude Code instances, wipe session state
pkill -f "^claude " 2>/dev/null || true
rm -rf ~/.claude/projects/

# 2. Clean folders
rm -rf ~/test-center/playground/*
rm -rf ~/test-center/interception/*
mkdir -p ~/test-center/interception

# 3. Copy data and verify it exists
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

## After Each Turn: Report

```python
import json
with open(f'{interception_dir}/turn-{N}.json') as f:
    d = json.load(f)
result = d.get('result', '')
shape_ok = all(s in result for s in ['[> Framing]', '[+ Consultant Options]', '[? Next Steps]'])
print(f"Turn {N}: {elapsed}s | Shape: {'PASS' if shape_ok else 'FAIL'} | Chars: {len(result)}")
```

Append to `summary.md`:
```
| N | X | PASS/FAIL | N | optional notes |
```

## Setting A (8-turn Standard)

Data at turn 5. Report at turn 7.

| Turn | What you say |
|------|-------------|
| 1 | Load skill, domain opening |
| 2 | Deeper domain question |
| 3 | Causal claim question |
| 4 | Methodological or framing question |
| 5 | **"Here is the data — data.csv, take a look"** |
| 6 | Follow up on exploration and analysis |
| 7 | **Ask for report** |
| 8 | Synthesis / next steps |

## Post-Session: Archive

```bash
SESSION_DIR=~/test-center/v4.2.4/session-<name>-$(date +%H%M)
mkdir -p "$SESSION_DIR"

# Build conversation
cd ~/test-center/interception
echo "# Conversation" > conversation.md
for f in turn-*.json; do
  tn=$(echo $f | grep -oP '\d+')
  python3 -c "
import json
with open('turn-${tn}.md') as fh: user = fh.read().strip()
with open('$f') as fh: d = json.load(fh)
print(f'## Turn {tn}\n**User:**\n{user}\n\n**Assistant:**\n{d.get(\"result\",\"\")}')
" >> conversation.md
done

# Copy artifacts (exclude data.csv)
rsync -av --exclude='data.csv' ~/test-center/playground/ "$SESSION_DIR/playground/"
cp ~/test-center/interception/* "$SESSION_DIR/"

# Clean
rm -rf ~/test-center/playground/* ~/test-center/interception/*
```

## Pitfalls

- **Data provisioning is mandatory.** Copy data.csv and verify columns before Turn 1. No data = no outputs.
- **Shell timeout ≥ 600s** for data/analysis turns (5–7). send_one's --timeout 900 won't fire if the shell kills it first.
- **Format drift is expected** on compute-heavy turns — flag FAIL but note substance if it's good.
- **Turn 1 is load-skill only.** Combining "load skill + explore data" times out.
- **Report precheck gate** (causal-consultant v4.2.4): the assistant should propose scope → get approval → write. **The gate can hold on the first report request** (scope shown, approval asked) but **still bypasses on subsequent report requests and on analysis gates.** The pending `report_writer` entry with `scope_ready` status appears to confuse routing on later turns. When evaluating sessions: check every report and analysis request independently — a hold on turn 6 does not guarantee a hold on turn 10. See `references/gate-behavior-findings.md` for the current state of knowledge.
- **Load RULES.md** alongside this skill during pre-flight for private operational details.

## Other Settings

See `references/settings.md` for Setting S (3-turn smoke) and Setting B (12-turn deep).
See `references/architectural-gate-test.md` for gate-specific test protocols.
