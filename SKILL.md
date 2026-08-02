---
name: interactive-test-cc
description: Run reproducible multi-turn regression tests for the causal-consultant skill. Use for the College observational-policy, College discovery-handoff, STAR interference-saturation, or Schooling IV-LATE case, including exact-session execution, controller validation, artifact checks, and result capture.
---

# Interactive causal-consultant tests

Version: `5.3.1`

Choose one explicit case and load its case reference plus the shared
[`evaluation guide`](references/evaluation-guide.md):

| Test ID | Reference | Main route coverage |
|---|---|---|
| `college-observational-policy` | [`references/college-observational-policy.md`](references/college-observational-policy.md) | Observational dose response, heterogeneity, and report lifecycle |
| `college-discovery-handoff` | [`references/college-discovery-handoff.md`](references/college-discovery-handoff.md) | Bounded discovery, independent review, and analysis handoff |
| `star-interference-saturation` | [`references/star-interference-saturation.md`](references/star-interference-saturation.md) | Interference exposure mapping, saturation support, and policy boundary |
| `schooling-iv-late` | [`references/schooling-iv-late.md`](references/schooling-iv-late.md) | Instrumental variables, weak-IV validity, and LATE boundary |

Exact prompts, dataset fingerprints, and per-turn artifact expectations have one
machine-readable source: [`references/test-cases.json`](references/test-cases.json).
Do not rewrite or adapt them during a registered test.

## Run a test

1. Install or symlink the intended causal-consultant package at
   `${CLAUDE_CONFIG_DIR:-~/.claude}/skills/causal-consultant`.
2. Prepare a fresh work directory containing only the case's canonical dataset
   renamed to `data.csv`. Remove the source row-name column when the registry
   describes the cleaned Ecdat export.
3. Choose a missing or empty results directory outside the work directory.
4. Run:

```bash
python3 <skill-root>/scripts/run_all_turns.py \
  --test <test-id> \
  --workdir <work-directory> \
  --results-dir <results-directory> \
  --statectl <Claude-visible-causal-consultant-root>/scripts/statectl.cjs
```

The runner owns exact session resumption, response-shell checks, strict idle-state
validation, scope transitions, manifest and receipt integrity, immutable artifact
snapshots, HTML links, and input and runtime provenance. It accepts legacy
schema-1 completion manifests and current schema-2 completion or infeasibility
manifests according to the installed controller's declared capabilities.

A diagnostic alone does not stop the replay. Continue from a trustworthy idle
boundary whenever the next prompt still has its required scope or evidence.
Stop only when project continuity is uncertain or a required prerequisite is
absent. Registered live runs validate completed turn boundaries; interrupted
operation recovery belongs to the controller's deterministic tests.

The response shell requires `[> Framing]`, `[! Boundary]`, and
`[? Next Steps]` once and in that order. `[+ Consultant Options]` is required
during manual review only when the user must choose among two or more materially
different legal next operations. Do not fail a response because another
conceivable action was not offered.

## Evaluate a completed run

All four cases require manual review. Read the saved case reference, shared
evaluation guide, conversation, state snapshots, manifests, receipts, code, and
outputs. Judge actual contract fidelity rather than treating a receipt as proof,
and distinguish decision-impacting failures from minor, decision-equivalent
defects.

Save a brief assessment file inside the results directory, then finalize:

```bash
python3 <skill-root>/scripts/run_all_turns.py \
  --assess-results <results-directory> \
  --rating <pass|weak|fail> \
  --notes-file <results-directory>/<assessment-notes>.md
```

An automated failure remains visible and cannot be overridden by the manual
rating. Finalization verifies that saved review evidence has not changed. Report
the final result, not the automated result alone.

## Focused transport check

Use `scripts/send_one.py` directly only for a requested single-turn or transport
diagnosis. Resume later calls with the exact returned `session_id`, never ambient
continuation.
