---
name: interactive-test-cc
description: Run reproducible multi-turn regression tests for the causal-consultant skill. Use for the smoke, standard, mechanical-edge, or causal-edge test, including exact-session execution, controller validation, artifact checks, and result capture.
---

# Interactive causal-consultant tests

Version: `5.1.1`

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

The runner owns prompt delivery, exact session resumption, response-shell checks, strict state validation, artifact-manifest checks, and per-turn snapshots. It stops before the next prompt whenever transport, session identity, response JSON, or the state boundary is uncertain. A shell or artifact mismatch is recorded and may continue only from controller-validated idle state.

The shell oracle requires the exact heading lines `[> Framing]`, `[! Boundary]`, and `[? Next Steps]` once and in that order. `[+ Consultant Options]` is optional and, when present, belongs between Framing and Boundary.

Do not clear global Claude sessions or delete an existing work directory. Start with fresh directories instead.

For `causal-edge`, first require the mechanical run to complete, then use its reference rubric to inspect the saved conversation and report. Save the `safe`, `weak`, or `fail` judgment with brief turn-level reasons as `causal-assessment.md` in the results directory. The runner intentionally does not automate causal judgment.

## Focused transport check

Use `scripts/send_one.py` directly only when a user asks for a single-turn or transport diagnosis. Save the `session_id` returned by the first call and pass that exact value as `--session-id` on later calls; do not use ambient continuation.
