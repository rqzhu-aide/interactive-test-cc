# Standard test

This 13-turn benchmark exercises the ordinary lifecycle with the 777-row College dataset. Exact prompts and cumulative artifact counts live in [`test-cases.json`](test-cases.json).

| Checkpoint | Turns | Required result |
|---:|---:|---|
| 1 | 1-4 | The decision, causal assumptions, data roles, quality, support, and timing are examined before design or execution. |
| 2 | 5-7 | Readiness review precedes an approval-ready scope, and exact approval produces an analysis that honors its bound target, estimand, required strategy, diagnostics, outputs, and claim boundary. |
| 3 | 8-10 | Causal support and the non-causal boundary are reassessed without computing the new target or preparing its scope; the next turn prepares the scope, and exact approval produces the separate analysis. |
| 4 | 11-12 | The approved report uses only completed evidence and honors its purpose, audience, required outputs, and claim boundary. Source data do not replace a promised rendered display, and audience-facing prose does not expose internal workflow mechanics. |
| 5 | 13 | The response prepares only the requested slide-style scope, creates no file or artifact, leaves the controller idle, and keeps the derivative scope ready for later approval. |

The two analysis approvals must refer to the current ready scope presented immediately before them, and the presented default must match the stored scope. Before approval, core routes may assess readiness and route-owned evidence, but they must not compute a new result that answers the target analysis. Turn 8 uses one causal review operation to establish the design, heterogeneous-effects support, and non-causal boundary for a bounded exploratory comparison; it may use completed evidence but must not compute the new target or prepare a scope. Turn 9 consumes that recommendation to prepare one new ready scope without rerunning causal review or analysis. The report must use only completed evidence and preserve its claim boundaries. Turn 13 tests scope preparation, not native slide generation.

Automated checks pass when every turn ends in valid idle state, the response shell is correct, scope identities follow the registered lifecycle, prior artifacts remain unchanged, and expected artifact growth and manifests match. A passing automated run remains pending until the five checkpoints above are reviewed manually. A material violation at any checkpoint makes the overall rating `fail`; otherwise rate the run `pass`. Judge fidelity to the workflow contract, including bound scope and method requirements. Do not grade numerical correctness or substitute reviewer preference for an otherwise contract-compliant method.
