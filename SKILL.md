---
name: interactive-test-cc
description: Run reproducible multi-turn regression tests for the causal-consultant skill. Use for the College observational-policy, College discovery-handoff, open STAR consultation, or Schooling IV-LATE case, including exact outer-session execution, controller validation, artifact checks, and result capture.
---

# Interactive causal-consultant tests

Version: `6.3.0`

Compatibility target: `causal-consultant` `6.3.0`. Preflight requires its
complete advertised capability map so protocol drift stops before a live model
turn. For report-bearing cases, preflight also drives the real controller
through one private, model-free analysis-to-evidence-bound-report lifecycle and
runs the harness validators against its real schema-3 artifacts.

Choose one explicit case. The runner uses its registered prompts and saves the
case reference plus the shared [`evaluation guide`](references/evaluation-guide.md)
with the result:

| Test ID | Reference | Main route coverage |
|---|---|---|
| `college-observational-policy` | [`references/college-observational-policy.md`](references/college-observational-policy.md) | Observational dose response, heterogeneity, and report lifecycle |
| `college-discovery-handoff` | [`references/college-discovery-handoff.md`](references/college-discovery-handoff.md) | Bounded discovery, independent review, and analysis handoff |
| `star-interference-saturation` | [`references/star-interference-saturation.md`](references/star-interference-saturation.md) | Open novice consultation with consultant-selected analysis and report |
| `schooling-iv-late` | [`references/schooling-iv-late.md`](references/schooling-iv-late.md) | Instrumental variables, weak-IV validity, and LATE boundary |

Exact prompts, dataset fingerprints, and per-turn artifact expectations have one
machine-readable source: [`references/test-cases.json`](references/test-cases.json).
Do not rewrite or adapt them during a registered test.

## Run a test

1. Install or symlink the intended causal-consultant package at
   `${CLAUDE_CONFIG_DIR:-~/.claude}/skills/causal-consultant`.
2. Prepare a fresh work directory containing only the case's canonical dataset
   renamed to `data.csv`. Remove the source row-name column when the case
   reference identifies a cleaned Rdatasets export.
3. Choose a missing or empty results directory outside the work directory.
4. Run:

```bash
python3 <skill-root>/scripts/run_all_turns.py \
  --test <test-id> \
  --workdir <work-directory> \
  --results-dir <results-directory> \
  --statectl <Claude-visible-causal-consultant-root>/scripts/statectl.cjs
```

The runner owns exact outer-session resumption, response-shell checks, strict idle-state
validation, scope transitions, manifest and receipt integrity, immutable artifact
snapshots, HTML links, the required primary report shell, a basic image-alt
accessibility floor, and input and runtime provenance. Supplementary HTML may
remain shell-free when the primary page is unambiguous. It accepts legacy
schema-1 completion manifests, historical schema-2 receipt manifests, and current
schema-3 completion or infeasibility manifests. Current receipts validate
requirement-level evidence locators and disclosed deviations. Current manifests
also persist the exact ordered requirement IDs, kinds, and descriptions,
including `analysis_artifact_id` requirements that freeze a report's selected
analysis completion records. The runner verifies their contract-bound IDs and
full receipt accounting while preserving schema-1 and schema-2 result
compatibility. Current bound operations use completion protocol 2; an in-flight
migrated protocol-1 operation may still close with its historical schema-2
receipt. A schema-3 completion may use a null receipt only for protocol-0 work,
including migrated scoped recovery, and then its ordered `requirements` must be
`[]`.

A diagnostic alone does not stop the replay. Continue from a trustworthy idle
boundary whenever the next prompt still has its required scope or evidence.
Stop only when project continuity is uncertain or a required prerequisite is
absent. Registered live runs validate completed turn boundaries; interrupted
operation recovery belongs to the controller's deterministic tests.

The response shell requires `[> Framing]`, `[! Boundary]`, and
`[? Next Steps]` once and in that order. `[+ Consultant Options]` is required
during qualitative review only when the user must choose among two or more
materially different legal next operations. Do not fail a response because
another conceivable action was not offered.

## Evaluate a completed run

All four cases require one qualitative review. Start with `summary.md` and
`evaluation-dossier.md`. The dossier contains the case rules, shared guide,
complete user-facing conversation, deterministic transition results, each new
manifest and receipt once, frozen scope contracts and causal strategy portfolios
when exposed by the controller, report `analysis_artifact_ids`, direct or
numbered approval bindings, and readable artifact evidence. Schema-3 manifest
entries retain their requirement descriptions even if the live scope is later
revised. The runner has already checked outer-session and project continuity,
controller state, scope identity, artifact binding, hashes,
and HTML references. Do not repeat those mechanical checks when they pass. Open a
raw saved file only when the dossier flags a problem or leaves a semantic
checkpoint unresolved.

Internal router, worker, and team-lead phases may use fresh contexts while the
outer user conversation remains one resumed session. Phase capsules and
`.statectl-tmp/phase-context.json` are temporary transport, not review evidence;
their absence after closeout is expected. Treat phase isolation as unobserved
unless direct trace evidence establishes it. Transport-reported agent turns,
tokens, API time, and cost are descriptive efficiency telemetry, not correctness
criteria or counts of the registered user turns.

Judge actual contract fulfillment, causal boundaries, decision usefulness, and
the materiality of defects. Save one structured assessment inside the results
directory:

```json
{
  "schema_version": 1,
  "summary": "Compact overall assessment.",
  "findings": [
    {
      "severity": "minor",
      "checkpoint": "Case checkpoint or approved scope item",
      "description": "Specific defect and its effect on use."
    }
  ]
}
```

Use an empty `findings` list when no defect warrants correction. The script
derives `pass`, `weak`, or `fail` from the highest finding severity, so the
rating cannot conflict with the recorded findings. Then finalize:

```bash
python3 <skill-root>/scripts/run_all_turns.py \
  --assess-results <results-directory> \
  --assessment-file <results-directory>/assessment.json
```

An automated failure remains visible and cannot be overridden by the qualitative
rating. Finalization verifies that saved review evidence has not changed. Report
the final result, not the automated result alone. Historical result folders may
still use the legacy `--rating` plus `--notes-file` form.

## Focused transport check

Use `scripts/send_one.py` directly only for a requested single-turn or transport
diagnosis. Resume later calls with the exact returned `session_id`, never ambient
continuation. Invocation modes (one-shot `-p`, ambient `-c -p`, explicit
`--resume`) are documented in
[`references/claude-conversation-modes.md`](references/claude-conversation-modes.md).
