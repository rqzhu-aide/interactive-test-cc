---
name: interactive-test-cc
description: Run reproducible multi-turn regression tests for the causal-consultant skill. Use for the College observational-policy, College discovery-handoff, open STAR consultation, or Schooling IV-LATE case, including exact-session execution, controller validation, artifact checks, and result capture.
---

# Interactive causal-consultant tests

Version: `6.0.1`

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
during qualitative review only when the user must choose among two or more
materially different legal next operations. Do not fail a response because
another conceivable action was not offered.

## Evaluate a completed run

All four cases require one qualitative review. Start with `summary.md` and
`evaluation-dossier.md`. The dossier contains the case rules, shared guide,
complete conversation, deterministic transition results, each new manifest and
receipt once, frozen scope contracts when exposed by the controller, and
readable artifact evidence. The runner has already checked
session and project continuity, controller state, scope identity, artifact
binding, hashes, and HTML references. Do not repeat those mechanical checks when
they pass. Open a raw saved file only when the dossier flags a problem or leaves
a semantic checkpoint unresolved.

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
continuation.
