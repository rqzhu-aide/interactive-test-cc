# Causal-Consultant Version Behavior

## v5.0.0 (current)

- **Architecture**: Router-based. Commit `ce05960`: "Release causal consultant v5.0.0." Migrated from subskills to references/ directory. State management via `statectl.cjs` (no direct YAML editing). Added `[! Boundary]` as always-present output marker.
- **Setting A (deepseek-v4-pro, activated)**: 13/13 PASS ✅ — PERFECT SCORE. All 13 turns had ≥2/3 shape markers. College (777×19). 1,799K tokens (1,686K in + 113K out). YAML: 23.7KB. Output: 8 files (report, 2 analysis sets, data audit). Total elapsed: ~31 min. **T13 (PPT summary) passed — first version ever to maintain shape through the final turn.**
- **Setting A (deepseek-v4-flash, activated)**: 10/13 PASS — T1-T9 all PASS, T10 FAIL (heterogeneity confirmation: already-executed shortcut, 1/3 markers), T11 PASS, T12 FAIL (report confirmation: format drift), T13 FAIL (PPT summary: format drift). College (777×19). 1,912K tokens (1,783K in + 129K out). YAML: 19.7KB. Output: 17 files (report, slides, 5 figures). Total elapsed: ~18 min.
- **Smoke (3-turn)**: NOT YET TESTED

## v4.5.3

- **Architecture**: Router-based. Commit `d8c0983`: "Release causal consultant v4.5.3 gate fixes." Simplified core-review gate logic, removed meta-instructions from team_lead, simplified report closeout.
- **Setting A (deepseek-v4-pro, activated)**: 11/13 PASS shape ✅, 13/13 OK substance. T1-T11 all 3/3 markers, T12-T13 0-1/3 (format drift on output turns). College (777×19). 2,854K tokens (2,730K in + 123K out). Produced: YAML (42KB), HTML report (51KB), slides (17KB), 12 PNG figures.
- **Setting A (deepseek-v4-pro, not activated)**: 0/13 PASS shape ⚠️. No markers at all — natural conversation without structured protocol. Same prompts produce 406K tokens (327K in + 79K out) but no YAML, no team workflow. Produces loose artifacts (1 chart, HTML, PPT) but skips the protocol entirely.
- **Setting A (deepseek-v4-flash, activated)**: 12/13 PASS ✅ — T1-T12 all 3/3 markers, T13 FAIL (summary turn format drift). College (777×19). 1,601K tokens (1,501K in + 100K out), 44% fewer than v4-pro. Produced: YAML (37KB), HTML report + PPTX slides, 6 PNG figures, 2 MD analysis. **Previous 0/9 result was a non-activated test — flash handles the protocol fine with explicit activation.**

## v4.5.1

- **Setting A (deepseek-v4-pro)**: 10/13 PASS (T1-10 all PASS, T11-13 FAIL on format drift). Precheck gates held for all analysis confirmation turns (T8, T10). HTML report (48.8KB), HTML slides (13.8KB).
- **Setting A (deepseek-v4-flash, not activated)**: 0/12 PASS — shape collapse because skill was not triggered, not a model limitation.
- **Improvement over v4.5.0**: +1 PASS (T10 now holds shape).

## v4.5.0

- **Setting A (deepseek-v4-pro)**: 9/13 PASS (T1-9 all PASS, T10-13 FAIL on format drift — precheck confirmations and output turns). All substantive outputs produced: HTML report (41KB), HTML slides (12KB), health analysis files.

## Previous Versions

- **v4.2.6**: Both precheck gates hold + outputs reliable. Analysis handoff fix.
- **v4.2.5**: Report gate holds, analysis gate always bypassed. Outputs reliable.
- **v4.3.0**: Best gate behavior but gates didn't lead to execution — reports rarely written.

## Model Compatibility (v5.0.0)

| Model | Activated | Tokens | Shape | Suitability | Notes |
|-------|-----------|--------|-------|-------------|-------|
| deepseek-v4-pro | ✅ | 1,799K | 13/13 | ✅ Best | Perfect score. Richer output (8 files, 23.7KB YAML). |
| deepseek-v4-flash | ✅ | 1,912K | 10/13 | ✅ Good | T1-T9 all PASS, T10-T13 format drift. Lighter touch. |
| deepseek-v4-pro | ❌ | ~400K | 0/13 | ❌ None | No skill → no protocol. Substance only. |
| deepseek-v4-flash | ❌ | ~400K | 0/13 | ❌ None | No skill → raw scripts, no markers. |

**Rule:** Activation is the critical factor, not model tier. Any model needs explicit skill trigger in Turn 1 or it produces 0/13 shape. With activation, v4-pro achieves 13/13 PASS (perfect), v4-flash achieves 10/13 PASS.

## Recommendation

**Activation is everything.** Include "Use the causal-consultant skill" in Turn 1 regardless of model. v4-pro: 13/13 PASS (perfect), 1,799K tokens, 8 output files, 23.7KB YAML. v4-flash: 10/13 PASS, 1,912K tokens, 17 output files, 19.7KB YAML — viable for cost-sensitive smoke/edge testing. Without activation: 0/13 shape regardless of model.
