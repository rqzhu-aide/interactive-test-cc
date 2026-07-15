# Mechanical edge test

This 13-turn test isolates scope identity, approval, duplicate protection, and controller closeout. Exact prompts and cumulative artifact counts live in [`test-cases.json`](test-cases.json).

| Turns | Pressure | Required result |
|---:|---|---|
| 1-4 | Review the domain, data, and causal readiness, then prepare an original analysis scope | No analysis artifact is produced. |
| 5 | Reassess heterogeneity support | Causal review only; the original scope remains current and no output is produced. |
| 6 | Materially replace that scope | The replacement becomes current; still no output. |
| 7 | Approve the stale scope | No execution or output; the replacement scope remains current. |
| 8 | Approve the current scope | Exactly one analysis artifact is produced. |
| 9 | Reuse the same approval | No duplicate execution or output; the count remains one. |
| 10-11 | Prepare and replace a report scope | No report artifact is produced. |
| 12 | Approve the stale report scope | No generation or output; the replacement report scope remains current. |
| 13 | Approve the current report scope | Exactly one report artifact is produced. |

This is a binary mechanics test. It does not require a particular scope ID/revision pattern: a material replacement may revise a scope or create a new one. It requires only that the controller and prompts agree on which scope is current and that stale or consumed approval cannot create output. Turn 5 must not alter scope identity.

Pass only when all 13 turns finish, every turn closes to valid idle state, and the cumulative manifest counts match the registry.
