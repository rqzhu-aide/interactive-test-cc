---
name: interactive-test-cc
description: "For a Hermes agent to test a target assistant by running multi-turn conversations in Claude Code. Each turn: write a message file, run send_one.py directly (synchronous), read the JSON output. No cron, no polling — just direct execution."
---

# interactive-test-cc

Version: `3.3.2`

You are a **Hermes agent** tasked with testing a target assistant through
Claude Code. This skill tells you how to set up the environment and run a
multi-turn conversation — writing message files per turn, calling `send_one.py`
directly, and reading the JSON responses immediately.

The target assistant runs as Claude Code in agentic mode (`-p` for fresh,
`--continue` to resume). You call `send_one.py` directly for every turn —
it's synchronous, so you get the response immediately when it exits.

## Folder Architecture

Two folders with different purposes:

| Folder | Purpose | What goes there |
|--------|---------|-----------------|
| `~/test-center/playground/` | Claude Code's working directory | Data (`data.csv`), any files Claude reads/writes, project artifacts |
| `~/test-center/interception/` | Test output (hidden from Claude) | `turn-*.md`, `turn-*.json`, `conversation.md`, `summary.md` |

**Why**: Claude Code runs in `playground/` and sees only what's there.
The test harness (Hermes) reads/writes turn files and summaries in
`interception/` — Claude Code never sees its own test responses.

## Settings

Three pre-defined settings control turn count, gates, and rules.
The user picks one (or specifies a custom override).

| Setting | Turns | Data gate | Report gate | Special |
|---------|-------|-----------|-------------|---------|
| **S** (smoke) | 3 | Never | Never | No data.csv, conversation only |
| **A** (standard) | 8 | ≥ turn 3 | ≥ turn 5 | ≥2 unconventional turns |
| **B** (deep) | 12 | ≥ turn 4 | ≥ turn 8 | HTML report at turn 10, ≥3 unconventional |

See `~/test-center/RULES.md` for full turn-by-turn scaffolds and
per-dataset domain-aligned opening templates.

## Before the Test

The user tells you:
- **Skill name** — the Claude Code skill to test (e.g., `causal-consultant`)
- **Setting** — S, A, or B (see table above)
- **Dataset** — path to the data file (skip for Setting S / smoke)
- **Additional context** — any domain-specific info to include in Turn 1

## Pre-flight (every session)

1. **Re-read the testing procedure**: load this skill and `~/test-center/RULES.md`
   to refresh your memory on gates, turn scaffolds, and quality checks.

2. **Restart Claude Code** — kill all instances and wipe session state:
   ```bash
   pkill -f "^claude " 2>/dev/null || true
   rm -rf ~/.claude/projects/
   ```

3. **Clean both folders:**
   ```bash
   rm -rf ~/test-center/playground/*
   rm -rf ~/test-center/interception/*
   mkdir -p ~/test-center/interception
   ```

4. **Create session folder:**
   ```bash
   SESSION_DIR=~/test-center/v4.2.4/session-$(date +%Y-%m-%d-%H-%M-%S)
   mkdir -p "$SESSION_DIR"
   ```

5. **Prepare data (Settings A/B only):**
   ```bash
   cp <data-source>/data.csv ~/test-center/playground/data.csv
   ```

6. **Verify dataset fit (Settings A/B only):** Quick check that the
   dataset's variables match the domain — treatment, outcome, covariates.
   ```bash
   python3 -c "
   import csv
   with open('$HOME/test-center/playground/data.csv') as f:
       print('Columns:', next(csv.reader(f)))
   "
   ```
   A 5-second peek prevents sessions wasted on mismatched data.

7. **Initialize summary.md** in the interception folder:
   ```bash
   cat > ~/test-center/interception/summary.md << EOF
   # Test Summary

   - **Test started**: $(date -Iseconds)
   - **causal-consultant version**: <detect from SKILL.md>
   - **interactive-test-cc version**: 3.3.2
   - **Setting**: <S|A|B>
   - **Dataset**: <path or "none">

   | Turn | Time (s) | Shape Correct | Characters | Notes |
   |------|----------|---------------|------------|-------|
   EOF
   ```

## Running a Turn

Each turn is direct and synchronous:

1. **Write** the message to `~/test-center/interception/turn-N.md`
2. **Run** `send_one.py` — it blocks until Claude Code finishes
3. **Read** the JSON response from `~/test-center/interception/turn-N.json`
4. **Report** immediately: time cost, shape correctness, character count
5. **Append** a row to `summary.md`
6. **Compose** the next turn

### Turn 1 — Fresh Session

```bash
# 1. Write the message to interception/
cat > ~/test-center/interception/turn-1.md << 'EOF'
Please load the causal-consultant skill.
EOF

# 2. Send it (blocks until done, max 15 min)
START=$(date +%s)
python3 ~/.hermes/skills/interactive-test-cc/scripts/send_one.py \
  --msg-file ~/test-center/interception/turn-1.md \
  --out-file ~/test-center/interception/turn-1.json \
  --workdir ~/test-center/playground \
  --timeout 900
ELAPSED=$(( $(date +%s) - START ))

# 3. Check shape and report
python3 -c "
import json
with open('$HOME/test-center/interception/turn-1.json') as f:
    d = json.load(f)
result = d.get('result','')
shape_ok = all(s in result for s in ['[> Framing]', '[+ Consultant Options]', '[? Next Steps]'])
print(f'Turn 1: {ELAPSED}s | Shape: {\"PASS\" if shape_ok else \"FAIL\"} | Chars: {len(result)}')
# Append to summary.md row
"
```

### Turns 2+ — Continue the Conversation

Same pattern, with `--continue`:

```bash
START=$(date +%s)
python3 ~/.hermes/skills/interactive-test-cc/scripts/send_one.py \
  --msg-file ~/test-center/interception/turn-N.md \
  --out-file ~/test-center/interception/turn-N.json \
  --workdir ~/test-center/playground \
  --continue \
  --timeout 900
```

### Shape Check

After every turn, verify the response contains these three sections:

```
[> Framing]          ← must be present
[+ Consultant Options]  ← must be present
[? Next Steps]       ← must be present
```

Report as `PASS` (all three present) or `FAIL` (one or more missing).

### Per-Turn Report Format

After each turn, tell the user immediately:

```
Turn N: Xs | Shape: PASS/FAIL | Chars: N
```

And append a row to `~/test-center/interception/summary.md`:

```
| N | X | PASS | N | <optional notes> |
```

### What send_one.py Does

Thin wrapper — just sends a message to Claude Code and writes the raw JSON output:

1. Reads the message file (`--msg-file`)
2. Runs `claude -p "<msg>" --output-format json` (or `-c -p` with `--continue`)
3. Writes the complete JSON result to `--out-file`

send_one.py does NOT manage conversation.md, session state, or multi-turn logic.
Those are your responsibility as the calling agent.

### send_one.py Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--msg-file` | required | Path to the message file |
| `--out-file` | required | Where to write the JSON response |
| `--workdir` | required | Working directory for Claude Code |
| `--continue` | off | Continue latest session (`claude -c -p`) |
| `--max-turns N` | 30 | Max Claude Code internal turns |
| `--timeout N` | **900** | Timeout in seconds (15 min) |

### Building conversation.md

After all turns complete, assemble `conversation.md` in `interception/`:

```bash
cd ~/test-center/interception
echo "# Conversation" > conversation.md
for f in turn-*.json; do
  tn=$(echo $f | grep -oP '\d+')
  echo "" >> conversation.md
  echo "## Turn $tn" >> conversation.md
  python3 -c "
import json
with open('turn-${tn}.md') as fh:
    user_msg = fh.read().strip()
with open('$f') as fh:
    d = json.load(fh)
print('**User:**')
print(user_msg)
print()
print('**Assistant:**')
print(d.get('result', 'NO RESPONSE'))
" >> conversation.md
done
```

### Turn Scaffolds Per Setting

Gates and turn-by-turn scaffolds for each setting. See `~/test-center/RULES.md`
for the complete reference with per-dataset opening templates.

**Setting S (3-turn smoke):** No data ever.
| Turn | Action |
|------|--------|
| 1 | Domain-aligned opening (load skill, no data) |
| 2 | Probe reasoning or methodology |
| 3 | Counterfactual or synthesis question |

**Setting A (8-turn):** Data ≥ turn 3, report ≥ turn 5.
| Turn | Gate | Action |
|------|------|--------|
| 1 | No data, no report | Domain-aligned opening |
| 2 | No data, no report | Deepen domain conversation |
| 3 | Data allowed | Natural data introduction |
| 4 | Data allowed | Follow up on context |
| 5 | Report allowed | First analysis request |
| 6–7 | All open | Interpretation, unconventional angle |
| 8 | All open | Synthesis / next steps |

**Setting B (12-turn):** Data ≥ turn 4, report ≥ turn 8, HTML at turn 10.
| Turn | Gate | Action |
|------|------|--------|
| 1 | No data, no report | Domain-aligned opening |
| 2 | No data, no report | Deepen domain conversation |
| 3 | No data, no report | Continue domain discussion |
| 4 | Data allowed | Natural data introduction |
| 5–7 | Data allowed | Discuss dataset, bridge to analysis |
| 8 | Report allowed | First analysis request |
| 9 | All open | Method comparison, interpretation |
| 10 | All open | **Must ask for HTML report** |
| 11 | All open | Unconventional angle |
| 12 | All open | Synthesis / next steps |

**Unconventional quota**: A: ≥2 turns (5–8). B: ≥3 turns (8–12, HTML turn 10 does NOT count). S: no quota.

## After a Session — Archiving

**Copy** (not move) both folders into the session directory under `v4.2.4/`:

```bash
SESSION_DIR=~/test-center/v4.2.4/session-<timestamp>

# Copy playground artifacts (excluding data.csv)
rsync -av --exclude='data.csv' ~/test-center/playground/ "$SESSION_DIR/playground/"

# Copy interception artifacts (turn files, conversation, summary)
cp -r ~/test-center/interception/* "$SESSION_DIR/"

# Final structure:
# v4.2.4/session-YYYY-MM-DD-HH-MM-SS/
# ├── playground/         ← all Claude Code artifacts (reports, plots, etc.)
# ├── turn-*.md           ← message files
# ├── turn-*.json         ← raw JSON responses
# ├── conversation.md     ← assembled conversation
# └── summary.md          ← per-turn table
```

### Clean Up

After archiving, clean both folders **including data**:

```bash
rm -rf ~/test-center/playground/*
rm -rf ~/test-center/interception/*
```

### Fresh Session Between Runs

To start over between test runs:
```bash
rm -rf ~/.claude/projects/
```

## summary.md Format

Written in `~/test-center/interception/summary.md`. Created once at session start,
appended to after every turn.

```markdown
# Test Summary

- **Test started**: 2026-06-15T14:30:00+00:00
- **causal-consultant version**: v4.2.4
- **interactive-test-cc version**: 3.3.2
- **Setting**: A
- **Dataset**: wage

| Turn | Time (s) | Shape Correct | Characters | Notes |
|------|----------|---------------|------------|-------|
| 1 | 24 | PASS | 803 | |
| 2 | 61 | PASS | 2174 | |
| 3 | 163 | PASS | 2366 | |
```

## Pitfalls

- **Don't use cron or polling.** Call `send_one.py` directly per turn.
  It's synchronous — you get the response immediately when it exits.
- **Turn 1: load the skill ONLY.** 40-char "load skill" works in ~19s.
  250-char "load skill + explore dataset" times out. Split into
  separate turns: Turn 1 = load skill, Turn 2 = introduce data.
- **Timeout is 15 minutes (900s).** Set `--timeout 900` on every send_one.py call.
  Most turns finish in 60–180s; the 900s cap catches hangs without slowing normal runs.
  B-setting analysis turns can exceed 300s — the 900s cap handles this.
- **`-c` and `--resume` DO work — even with large tool-use histories.**
  Do NOT work around session continuation — Claude Code handles it.
- **Session-directory binding.** Claude Code ties sessions to the project
  directory. `-c` (continue latest) is directory-scoped. Always run from
  `~/test-center/playground/`.
- **Interception isolation.** Write turn files to `interception/`, NOT `playground/`.
  Claude Code must never see its own test responses — they'd contaminate the session.
- **Session storage**: Claude Code 2.x stores sessions as `.jsonl` files in
  `~/.claude/projects/<project-dir>/<session-id>.jsonl`.
- **`--dangerously-skip-permissions` is baked into `send_one.py`.** Without it,
  Claude Code asks "May I proceed?" and stalls in non-interactive (`-p`) mode.
- **Complex skills need higher `--max-turns` AND longer `--timeout`.**
  Skills that read many reference files need `--max-turns 30 --timeout 900`.
- **Data gate & Report gate**: Varies by setting. See Turn Scaffolds table.
- **Unconventional turns are mandatory** — A: ≥2, B: ≥3.
- **Shape check**: verify `[> Framing]`, `[+ Consultant Options]`, `[? Next Steps]`
  are all present in every response. Report PASS/FAIL immediately.
- **Ad hoc shape check**: Turn 1 additionally checks for `[Causal-Consultant vX Loaded]`.
- **Delete Claude Code sessions between test runs:** `rm -rf ~/.claude/projects/`.
- **"Not logged in" errors are transient.** Claude Code sometimes fails auth on
  the first subprocess call. Just retry — the second attempt usually works.
- **Separation of concerns.** This SKILL.md describes test procedure only — zero
  infrastructure details (no proxy URLs, no provider commands, no API keys,
  no provider config, no concrete dataset paths). All operational private
  information (proxy config, env vars, dataset registry, provider restart
  commands, API key locations) belongs in `~/test-center/RULES.md` under its
  **Operational Details (PRIVATE)** section. Load RULES.md alongside this skill
  during pre-flight to pick up both the procedure and the private runtime details.
- **pkill regex collision.** `pkill -f "claude"` matches the shell itself and
  kills the terminal. Use the anchored form: `pkill -f "^claude " 2>/dev/null || true`.
- **Heredoc quoting for summary.md.** The init template uses `$(date -Iseconds)`.
  Use `<< EOF` (unquoted delimiter) so variables expand — `<< 'EOF'` produces
  a literal `$(date -Iseconds)` string in the output.
- **Pre-flight dataset verification.** Before starting, quickly check the dataset
  has variables that match the domain (treatment, outcome, covariates). A 5-second
  `csv.reader` peek prevents sessions wasted on data mismatches.
- **Format drift on Turn 1.** Some versions of the skill under test (e.g.,
  causal-consultant v4.2.4) may not use the canonical `[> Framing]` format
  on the initial loading message even though the skill loaded successfully.
  The shape check will correctly flag this as FAIL — note it in summary
  and continue. Subsequent turns usually use proper format.
- **Format drift on synthesis turns.** Final/synthesis turns may also drop
  canonical section headers. Record as FAIL per the shape check protocol;
  the content is usually still valid.
- **Pushback verification.** When the shape check is FAIL, especially on
  turns where you deliberately pushed an invalid question, read the actual
  response content before reporting. The assistant may have correctly pushed
  back with strong reasoning but used non-canonical formatting (bold headers,
  plain text sections). The shape FAIL is correct protocol, but the Notes
  column should reflect whether the *substance* of the response was valid.
  Keyword-based detection (`'not manipulable' in r.lower()`) is unreliable —
  the assistant may use different phrasing. Always spot-check the framing
  section manually for boundary-enforcement turns.
- **Invalid push testing.** This skill supports a stress-test scenario where
  turns 6+ deliberately ask invalid causal questions (immutable treatments,
  circular instruments, post-treatment controls) to test the assistant's
  boundary enforcement. See `references/invalid-push-testing.md` for the
  question templates and evaluation criteria. Do NOT use this on every
  session — it's a targeted stress test, not a standard run.
