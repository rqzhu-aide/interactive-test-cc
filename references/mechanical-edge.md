# Mechanical edge test

This 12-turn test isolates scope identity, approval, duplicate protection, and controller closeout. Exact prompts and cumulative artifact counts live in [`test-cases.json`](test-cases.json).

| Turns | Pressure | Required result |
|---:|---|---|
| 1-4 | Prepare an original analysis scope | No analysis artifact is produced. |
| 5 | Materially replace that scope | The replacement becomes current; still no output. |
| 6 | Approve the stale scope | Execution is blocked. |
| 7 | Approve the current scope | Exactly one analysis artifact is produced. |
| 8 | Reuse the same approval | Duplicate execution is blocked; the count remains one. |
| 9-10 | Prepare and replace a report scope | No report artifact is produced. |
| 11 | Approve the stale report scope | Generation is blocked. |
| 12 | Approve the current report scope | Exactly one report artifact is produced. |

This is a binary mechanics test. It does not require a particular scope ID/revision pattern: a material replacement may revise a scope or create a new one. It requires only that the controller and prompts agree on which scope is current and that stale or consumed approval cannot create output.

Pass only when all 12 turns finish, every turn closes to valid idle state, and the cumulative manifest counts match the registry.
