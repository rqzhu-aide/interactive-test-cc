# Report Precheck Gate Verification

The causal-consultant skill has a two-stage report precheck gate. When the
user asks for a report, the assistant should NOT write output immediately.
It must first go through scope approval.

## Expected Gate Flow

```
User asks for report
  → Router plans report_writer with report_precheck: false, mode: shallow
  → report_writer prepares approval-ready scope (no output created)
  → team_lead presents scope: "Here's what the report would cover. Approve?"
  → User approves
  → Router plans report_writer with report_precheck: true, mode: deep
  → report_writer creates actual output
```

## What to Check

After ANY turn where the user asks for a report, verify in
`project_state.yaml`:

1. `council_chamber.report_writer.current_status` should be
   `scope_ready: waiting for report precheck approval` on the FIRST report
   request — NOT `produced`.
2. `report_assembly.planned_structure` should be populated BEFORE any report
   output exists.
3. Report output should only exist AFTER a turn where the user explicitly
   approved the scope.

## Failure Signature (v4.2.4)

The assistant may skip the precheck entirely and jump straight to writing
a report. Look for:

- `report_output: exist` appearing on the same turn as the first report
  request
- `current_status: produced` without prior `scope_ready`
- No `planned_structure` populated before output creation
- `domain_knowledge_complete: false` or `exploration_complete: false` at
  the time of report creation

This happened in the 2026-06-16 college test: the assistant wrote
`output/report.md` immediately on Turn 7 without any precheck approval,
skipping domain knowledge and exploration gates.

## Root Cause

The precheck gate is conditional — it only fires when the router properly
plans `report_writer` with `report_precheck: false` in `next_step_plan`.
If the model shortcuts past the router (loads `report_writer.md` directly
without going through `route_selection_workflow.md` → `report_routing_workflow.md`),
the gate is never triggered and the model writes output immediately.

## Test Protocol

Add this check to the post-session analysis:
- Read `project_state.yaml` after archiving
- Verify `report_precheck` transition path if report output exists
- Flag any session where report was produced without scope approval
