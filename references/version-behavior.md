# Causal-Consultant Version Behavior

## v4.5.3 (current)

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

## Model Compatibility

| Model | Activated | Tokens | Shape | Suitability | Notes |
|-------|-----------|--------|-------|-------------|-------|
| deepseek-v4-pro | ✅ | 2,854K | 11/13 | ✅ Best | Richer output (22 files, 42KB YAML). Higher token cost. |
| deepseek-v4-flash | ✅ | 1,601K | 12/13 | ✅ Good | Same shape ballpark, 44% fewer tokens. Lighter output (10 files, 37KB YAML). |
| deepseek-v4-pro | ❌ | 406K | 0/13 | ❌ None | No skill → no protocol. Substance only. |
| deepseek-v4-flash | ❌ | ~400K | 0/9 | ❌ None | No skill → raw scripts, no markers. |
| kimi-k2.6 | ✅ | — | 9/13 | ✅ Good | Tested with v4.5.0, active shape gate with full YAML |

**Rule:** Activation is the critical factor, not model tier. Any model — pro or flash — needs explicit skill trigger in Turn 1 or it produces 0/13 shape. With activation, pro achieves 11/13 PASS, flash achieves 12/13 PASS.

## Recommendation

**Activation is everything.** Include "Use the causal-consultant skill" in Turn 1 regardless of model. With activation: v4-pro gives richer output (22 files, 42KB YAML) at 2,854K tokens (11/13 shape); v4-flash gives slightly better shape (12/13) at 44% fewer tokens with lighter artifacts (10 files, 37KB YAML). Without activation: 0/13 shape regardless of model.
