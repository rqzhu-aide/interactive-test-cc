# Discovery test

This eight-turn test exercises a legitimate discovery-to-analysis handoff using
the 777-row College dataset. Exact prompts and cumulative artifact counts live
in [`test-cases.json`](test-cases.json).

| Checkpoint | Turns | Required result |
|---:|---:|---|
| 1 | 1-2 | Domain constraints and data readiness are established without discovery, analysis, or output. |
| 2 | 3-4 | Discovery is scoped before it is run. The run preserves the exact controller-bound contract, creates one discovery artifact, and keeps every edge or orientation exploratory and candidate-only. |
| 3 | 5 | Causal review evaluates timing, adjustment validity, design fit, and claim strength independently. Discovery does not validate an adjustment set, select the final method, or open the analysis gate. |
| 4 | 6-7 | One approval-ready analysis scope preserves the causal review boundary, and exact approval creates one analysis artifact without changing that scope. |
| 5 | 8 | The decision synthesis distinguishes discovery hypotheses, completed analysis evidence, and unresolved assumptions without creating another artifact. |

Automated checks require valid idle state after every turn, a scoped discovery
contract at turn 3, one exactly bound and immutable `causal_discovery` artifact
from turn 4, no analysis scope through turn 5, one ready analysis scope at turn
6, exact completion at turn 7, and no later scope or artifact mutation.

Review the saved conversation, sidecar state, discovery artifact, analysis
artifact, and final synthesis. Do not grade the exact graph, numerical estimate,
or preferred method when the workflow remains contract-compliant. Rate `pass`
only when all five checkpoints hold; otherwise rate `fail`. An automated
failure still makes the final result fail.
