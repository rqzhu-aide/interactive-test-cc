# Claude Code conversation modes

How the runner (`send_one.py`) invokes Claude Code, and the modes it deliberately
does NOT use. One-shot, ambient continuation, and explicit resumption are
different mechanisms — do not conflate them.

## Mode reference

1. **`claude -p "msg"` — one-shot agentic.** The prompt is a standalone
   assignment: the model uses tools, completes the task, and exits. No memory
   of prior turns. This is the runner's per-turn mode.

2. **`claude -c -p "msg"` — AMBIENT continuation.** Each call resumes the most
   recent conversation in the current working directory and responds in
   context. History persists across invocations in that directory. NOT allowed
   in registered tests — the SKILL.md contract says resume with the exact
   returned `session_id`, never ambient continuation.

3. **`claude -p "msg" --resume <session_id>` — EXPLICIT resumption** of one
   exact session. The runner's continuation mode: `send_one.py` appends
   `--resume` when the previous turn returned a session ID. (`-r` is the
   shorthand; an empty ID opens an interactive picker.)

## Why the runner forbids `-c`

Ambient continuation resolves the *most recent* session for the current working
directory, not an exact session ID. Session identity is therefore implicit and
directory-scoped — nothing pins the run to one specific outer conversation.
That breaks the exact-outer-session resumption and provenance checks. Explicit
`--resume` pins a single session ID, which the runner records and validates per
turn.

## `-c -p` behaviors (documented for completeness)

```bash
# Turn 1 — fresh session (no -c)
claude -p "Hi! Can you help me explore a dataset?" --max-turns 5

# Turn 2 — continue the conversation (-c)
claude -c -p "I have a file called data.csv. What's in it?" --max-turns 5

# Turn 3 — continue again
claude -c -p "Now compute the correlation between age and score." --max-turns 5
```

- **Without `-c`:** every prompt is a standalone task (agentic mode). Tools,
  no memory of prior turns.
- **With `-c`:** the model resumes the most recent session for the current
  directory and responds as if in an ongoing conversation. Session transcripts
  live under `~/.claude/projects/<encoded-directory-path>/`, not in
  `~/.claude.json`.
- **JSON capture:** pair with `--output-format json` to extract `.result`,
  `.session_id`, `.num_turns`, and `.duration_ms` programmatically.
  `send_one.py` adds a synthetic `is_error` field on its own transport failures
  (timeout, non-zero exit, invalid JSON) — that is not a Claude Code field.
- **Fresh start:** run `claude project purge <path>` (or delete
  `~/.claude/projects/<encoded-directory-path>/`) to clear a directory's
  session transcripts. Do not delete `~/.claude.json` — it holds user-scope MCP
  servers, settings, and the project index, not the transcripts.

## Pitfalls

1. **`-p` without `-c` is agentic, not conversational.** `claude -p "task"`
   treats the prompt as a standalone assignment. Only `-c -p` (or explicit
   `--resume`) carries conversation across invocations.
2. **PTY interactive mode is unreliable for automation.** Starting `claude`
   without `-p` opens a TUI that does not accept PTY stdin cleanly outside
   tmux. Use `-p` (with or without `-c`) for programmatic calls.
