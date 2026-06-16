# Architectural Gate Test (10 turns)

Tests whether the causal-consultant's routing, precheck, and approval gates
fire correctly. Uses Setting A data schedule (data at turn 5).

## Protocol

| Turn | Prompt | Gate Tested |
|------|--------|-------------|
| 1 | "Please load the causal-consultant skill. I study how college characteristics relate to student outcomes." | Router init |
| 2 | "The main outcome I care about is graduation rates. In higher education research, what are the standard ways people measure institutional quality?" | domain_expert trigger |
| 3 | "I want to claim that higher per-student spending causes better graduation rates. Is that a defensible causal claim?" | causal_check shallow |
| 4 | "What kind of study design would actually let me test whether spending causes better outcomes?" | causal_check deep |
| 5 | "Here is the data — data.csv, take a look." | data_audit deep |
| 6 | "Based on what you found, does the raw data support the spending-graduation story?" | exploration review |
| 7 | "What analysis method would you recommend I actually run?" | method recommendation |
| 8 | "OK, run that analysis." | **Analysis precheck gate** |
| 10 | "Can you write up a report of everything we've found?" | **Report precheck gate** |

## Gate Verification

### Analysis precheck (Turn 8)
- **Expected:** Assistant shows analysis scope, sets `analysis_precheck: false`, asks approval. Does NOT execute.
- **Known failure (v4.2.4):** Executes immediately. Check `project_state.yaml` — `analysis_output: exist` on same turn = gate bypassed.

### Report precheck (Turn 10)
- **Expected:** Assistant shows report scope, sets `report_precheck: false`, asks approval. Does NOT write.
- **Known failure (v4.2.4):** Writes `output/report.md` immediately. Check `council_chamber.report_writer.current_status` — `produced` without prior `scope_ready` = gate bypassed.

## Success Criteria

| Invariant | Check |
|-----------|-------|
| Router runs before any work | `project_state.yaml` has `next_step_plan` populated |
| Data audit produces artifact | `output/data_audit_readiness/` exists after Turn 5 |
| Exploration completes | `data_audit_complete`, `domain_knowledge_complete`, `causal_check_complete` all True by Turn 7 |
| Analysis gate | `analysis_output: exist` only after explicit approval (Turn 9) |
| Report gate | `report_output: exist` only after explicit approval (Turn 11+) |
