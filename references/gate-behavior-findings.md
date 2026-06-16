# Gate Behavior Findings

Tracking the causal-consultant precheck gate behavior across test sessions.
Updated after each test run with new observations.

## Current State (v4.2.4, post-routing-mandate update)

After the June 16 SKILL.md update that added mandatory routing language
("always run route selection before any substantive work"), gate behavior
changed from "always bypassed" to "context-sensitive":

### Report Precheck Gate

| Session | Turn | Prompt | Result |
|---------|------|--------|--------|
| gate-test (college) | 10 | "Can you write up a report?" | ❌ Bypassed — wrote immediately |
| wage-B | 6 | "Can you write up a report?" | ✅ **HELD** — showed scope, asked approval |
| wage-B | 10 | "Write up a report of heterogeneity" | ❌ Bypassed — wrote immediately |

**Pattern:** The gate holds on the **first** report request in a session, when
no prior `report_writer` entry exists in `next_step_plan`. It fails on
subsequent report requests when a pending shallow `report_writer` with
`scope_ready` status is already in the plan.

### Analysis Precheck Gate

| Session | Turn | Prompt | Result |
|---------|------|--------|--------|
| gate-test (college) | 8 | "OK, run that analysis." | ❌ Bypassed — executed immediately |
| wage-B | 9 | "Can you run a different analysis?" | ❌ Bypassed — executed immediately |

**Pattern:** Analysis precheck is **never observed to hold**. The analysis
routing workflow appears weaker than the report routing workflow — the
`analysis_precheck: false` gate doesn't prevent execution.

## Hypothesis

The new routing mandate ("do not answer directly, write next_step_plan first")
makes the first report request go through the router correctly, which loads
`report_routing_workflow.md` → plans `report_writer` with `precheck: false` →
`report_writer.md` enforces shallow mode → shows scope.

But when a subsequent report request arrives and a pending shallow
`report_writer` entry already exists with `scope_ready` status, the routing
workflow's "Existing Report Writer Work" rules may trigger direct deep-mode
routing instead of re-entering the precheck gate. The model may also simply
skip the router on later turns once it has "momentum."

## Verification

After each session, check `project_state.yaml`:
- `council_chamber.report_writer.current_status` should show `scope_ready` before `produced`
- `council_chamber.report_writer.current_status` going directly to `produced` = gate bypassed
- `analysis_output: exist` appearing without a prior `analysis_precheck: true` turn = gate bypassed
