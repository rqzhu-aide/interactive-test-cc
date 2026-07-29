---
name: interactive-test-cc
description: Run reproducible multi-turn regression tests for the causal-consultant skill. Use for the smoke, standard, discovery, mechanical-edge, or causal-edge test, including exact-session execution, controller validation, artifact checks, and result capture.
---

# Interactive causal-consultant tests

Version: `5.2.7`

Choose one explicit test and load its reference:

| Test ID | Reference | Purpose |
|---|---|---|
| `smoke` | [`references/smoke.md`](references/smoke.md) | Activation and controller health without data |
| `standard` | [`references/standard.md`](references/standard.md) | Ordinary analysis and report lifecycle |
| `discovery` | [`references/discovery.md`](references/discovery.md) | Exploratory discovery to causal review and analysis handoff |
| `mechanical-edge` | [`references/mechanical-edge.md`](references/mechanical-edge.md) | Scope, approval, duplicate, and closeout gates |
| `causal-edge` | [`references/causal-edge.md`](references/causal-edge.md) | Causal-boundary pressure with manual substantive review |

Exact prompts and per-turn artifact-count expectations have one machine-readable source: [`references/test-cases.json`](references/test-cases.json). Do not rewrite or adapt them during a registered test.

## Run a test

1. Install or symlink the intended causal-consultant package at `${CLAUDE_CONFIG_DIR:-~/.claude}/skills/causal-consultant`. Live replay is supported only after Claude and the oracle resolve the same installed package.
   Use the same release number for `interactive-test-cc` and the target `causal-consultant`.
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

The runner owns prompt delivery, exact session resumption, response-shell checks, strict state and artifact-aware revision-budget validation, scope-identity transitions, immutable artifact snapshots, HTML-reference checks, per-turn snapshots, and suite, input, installed-target, and runtime provenance. It checks the delivered response shell and numbered menu against the persisted decision, and records exact receipt divergence as a diagnostic. A diagnostic alone neither fails nor stops the run. Before a registered approval, the full committed response must match. For a pending menu, omission of one displayed scope identifier bound to a pending option is the only tolerated difference. The run continues from a trustworthy idle boundary when the next registered prompt still has its required scope or evidence, and stops only when continuity is uncertain or a required prerequisite is absent.

Registered live runs validate completed turn boundaries. Interrupted-operation recovery remains part of the causal-consultant controller tests and is not inferred from these results.

The shell oracle requires the exact heading lines `[> Framing]`, `[! Boundary]`, and `[? Next Steps]` once and in that order. `[+ Consultant Options]` is structurally optional and, when present, belongs between Framing and Boundary. During manual review, require it only when the response asks the user to choose among two or more materially distinct legal next operations. Each option should represent one next operation, and Next Steps should only ask for the choice. Do not fail a response merely because another conceivable action was not offered.
During manual workflow review, resolve each response diagnostic against the persisted decision. Allow wording and supporting-detail differences only when the completed action, material scope, claim and authorization boundaries, and visible choices remain decision-equivalent.

Do not clear global Claude sessions or delete an existing work directory. Start with fresh directories instead.

The initial summaries separate automated checks from workflow assessment. `smoke` needs no qualitative rating. Every completed `standard`, `discovery`, `mechanical-edge`, or `causal-edge` run awaits review against the saved `test-reference.md`, conversation, state snapshots, manifests, and outputs. An automated pass remains `PENDING` and exits with code 3 until reviewed; an automated failure remains `FAIL` and exits with code 1.

For `standard` or `discovery`, save a `pass` or `fail` judgment with brief checkpoint-level reasons using its five-checkpoint rubric; any material checkpoint violation makes the run fail. For `mechanical-edge`, save a `pass` or `fail` judgment with brief turn-level reasons. For `causal-edge`, save a `safe`, `weak`, or `fail` judgment with brief turn-level reasons. Use a new, nonempty notes file inside the results directory. Then finalize the summaries:

```bash
python3 <skill-root>/scripts/run_all_turns.py \
  --assess-results <results-directory> \
  --rating <rating> \
  --notes-file <results-directory>/<assessment-notes>.md
```

Assess any completed registered run. A workflow rating never overrides an automated failure. Finalization verifies that the saved review evidence has not changed and records the notes digest with the rating. The runner does not judge workflow prose or scientific correctness itself. Report the final result, not the automated result alone.

## Focused transport check

Use `scripts/send_one.py` directly only when a user asks for a single-turn or transport diagnosis. Save the `session_id` returned by the first call and pass that exact value as `--session-id` on later calls; do not use ambient continuation.
