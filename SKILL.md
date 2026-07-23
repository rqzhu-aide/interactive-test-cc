---
name: interactive-test-cc
description: Run reproducible multi-turn regression tests for the causal-consultant skill. Use for the smoke, standard, mechanical-edge, or causal-edge test, including exact-session execution, controller validation, artifact checks, and result capture.
---

# Interactive causal-consultant tests

Version: `5.2.1`

Choose one explicit test and load its reference:

| Test ID | Reference | Purpose |
|---|---|---|
| `smoke` | [`references/smoke.md`](references/smoke.md) | Activation and controller health without data |
| `standard` | [`references/standard.md`](references/standard.md) | Ordinary analysis and report lifecycle |
| `mechanical-edge` | [`references/mechanical-edge.md`](references/mechanical-edge.md) | Scope, approval, duplicate, and closeout gates |
| `causal-edge` | [`references/causal-edge.md`](references/causal-edge.md) | Causal-boundary pressure with manual substantive review |

Exact prompts and per-turn artifact-count expectations have one machine-readable source: [`references/test-cases.json`](references/test-cases.json). Do not rewrite or adapt them during a registered test.

## Run a test

1. Install or symlink the intended causal-consultant package at `${CLAUDE_CONFIG_DIR:-~/.claude}/skills/causal-consultant`. Live replay is supported only after Claude and the oracle resolve the same installed package.
   The `interactive-test-cc` and target `causal-consultant` release numbers are independent and do not need to match.
2. Prepare a fresh work directory. Leave it empty for `smoke`; for every other test, place only the required 777-row `data.csv` there.
3. Choose a missing or empty results directory outside the work directory.
4. Run:

```bash
python3 <skill-root>/scripts/run_all_turns.py \
  --test <test-id> \
  --workdir <work-directory> \
  --results-dir <results-directory> \
  --statectl <Claude-visible-causal-consultant-root>/scripts/statectl.cjs
```

The runner owns prompt delivery, exact session resumption, response-shell checks, strict state and artifact-aware revision-budget validation, scope-identity transitions, immutable artifact snapshots, HTML-reference checks, per-turn snapshots, and suite, input, installed-target, and runtime provenance. It stops before the next prompt whenever transport, session identity, installed-target identity, response JSON, state, or scope identity is uncertain. A shell or artifact mismatch is recorded and may continue only from controller-validated idle state.

Registered live runs validate completed turn boundaries. Interrupted-operation recovery remains part of the causal-consultant controller tests and is not inferred from these results.

The shell oracle requires the exact heading lines `[> Framing]`, `[! Boundary]`, and `[? Next Steps]` once and in that order. `[+ Consultant Options]` is optional and, when present, belongs between Framing and Boundary.

Do not clear global Claude sessions or delete an existing work directory. Start with fresh directories instead.

The initial summaries separate automated checks from workflow assessment. `smoke` needs no qualitative rating. A successful `standard`, `mechanical-edge`, or `causal-edge` run remains `PENDING` until reviewed against the saved `test-reference.md`, conversation, state snapshots, manifests, and outputs. A pending live run exits with code 3 so it cannot be mistaken for a final pass.

For `standard`, save a `pass` or `fail` judgment with brief checkpoint-level reasons using its five-checkpoint rubric; any material checkpoint violation makes the run fail. For `mechanical-edge`, save a `pass` or `fail` judgment with brief turn-level reasons. For `causal-edge`, save a `safe`, `weak`, or `fail` judgment with brief turn-level reasons. Use a new, nonempty notes file inside the results directory. Then finalize the summaries:

```bash
python3 <skill-root>/scripts/run_all_turns.py \
  --assess-results <results-directory> \
  --rating <rating> \
  --notes-file <results-directory>/<assessment-notes>.md
```

Only assess a run whose automated checks passed. Finalization verifies that the saved review evidence has not changed and records the notes digest with the rating. The runner does not judge workflow prose or scientific correctness itself. Report the final result, not the automated result alone.

## Focused transport check

Use `scripts/send_one.py` directly only when a user asks for a single-turn or transport diagnosis. Save the `session_id` returned by the first call and pass that exact value as `--session-id` on later calls; do not use ambient continuation.
