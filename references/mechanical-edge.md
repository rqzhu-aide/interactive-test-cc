# Mechanical edge test

This 13-turn test isolates scope identity, approval, duplicate protection, and controller closeout. Exact prompts and cumulative artifact counts live in [`test-cases.json`](test-cases.json).

| Turns | Pressure | Required result |
|---:|---|---|
| 1-4 | Review the domain, data, and causal readiness, then prepare an original analysis scope | Turn 2 is state-only data audit; no artifact is produced. |
| 5 | Reassess heterogeneity support | Causal review only; the original scope remains current and no output is produced. |
| 6 | Materially replace that scope | The replacement becomes current; still no output. |
| 7 | Approve the stale scope | No execution or output; the replacement scope remains current. |
| 8 | Approve the current scope | Exactly one analysis artifact is produced. |
| 9 | Reuse the same approval | No duplicate execution or output; the count remains one. |
| 10-11 | Prepare and replace a report scope | No report artifact is produced. |
| 12 | Approve the stale report scope | No generation or output; the replacement report scope remains current. |
| 13 | Approve the current report scope | Exactly one report artifact is produced. |

This test has a binary workflow rating. A material replacement may create a new scope ID or advance the existing scope revision. The runner verifies the fixed scope sequence: turn 5 preserves the original scope, turns 6 and 11 change the relevant scope reference, stale approvals preserve the replacement, current approvals complete that exact reference, and stale or duplicate turns cannot change prior artifact bytes. It does not judge the scope's substantive quality.

Automated checks pass only when all 13 turns finish, every turn closes to valid idle state, cumulative manifest counts match the registry, and the fixed scope-continuity oracle passes. Then review the saved conversation and state snapshots to confirm that turns 2, 3, and 5 used the requested core work, and that stale or duplicate requests were not described as completed execution. Record `pass` or `fail` before reporting the final result.
