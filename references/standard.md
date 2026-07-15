# Standard test

This 13-turn benchmark exercises the ordinary lifecycle with the 777-row College dataset. Exact prompts and cumulative artifact counts live in [`test-cases.json`](test-cases.json).

| Turns | Phase | Required result |
|---:|---|---|
| 1 | Domain review | The policy decision, mechanisms, and domain assumptions are framed before design. |
| 2-4 | Intake and data audit | The policy claim, data roles, quality, support, and timing are examined before execution. |
| 5-6 | First design | Causal and method readiness are reviewed, then an approval-ready average-effect scope is prepared without output. |
| 7 | First approval | Exactly one analysis artifact is completed. |
| 8-10 | Heterogeneity cycle | Causal support is reassessed before a separate scope is prepared; its exact approval produces one additional analysis artifact. |
| 11-12 | Report cycle | An HTML scope is prepared, then its exact approval produces one report artifact. |
| 13 | Derivative communication | No file or new artifact is produced; confirm manually that the response prepares only a slide-style scope. |

The two analysis approvals must refer to the current scope presented immediately before them. Turn 8 is a fresh causal review, not scope preparation. The report must use only completed evidence and preserve its claim boundaries. Turn 13 tests scope preparation, not native slide generation.

Pass mechanically when every turn ends in valid idle state, the response shell is correct, and cumulative `analysis_execution` and `report_writer` manifest counts match the registry. Substantive scientific quality may be reviewed separately; it is not inferred by the runner.
