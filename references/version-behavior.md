# Causal-Consultant Version Behavior

## v4.5.3 (current)

- **Architecture**: Router-based. Commit `d8c0983`: "Release causal consultant v4.5.3 gate fixes." Simplified core-review gate logic, removed meta-instructions from team_lead, simplified report closeout.
- **Setting A (deepseek-v4-pro)**: 13/13 OK ✅ — all turns complete with coherent responses. College dataset (777×19). Total cost $4.80. Produced: HTML report (30KB), PPT (37KB), EDA chart (633KB). **YAML requires explicit skill activation** — include "Use the causal-consultant skill" in Turn 1 or the structured workflow (router, next_step_plan, project_state.yaml) won't fire. Without activation, Claude Code handles the conversation naturally but skips the team protocol.
- **Setting A (deepseek-v4-flash)**: 0/9 PASS — complete shape collapse. Produced 4.3MB HTML, 1.4MB PPTX, 27 figures but zero structured output. ⛔ Flash models incompatible.

## v4.5.1

- **Setting A (deepseek-v4-pro)**: 10/13 PASS (T1-10 all PASS, T11-13 FAIL on format drift). Precheck gates held for all analysis confirmation turns (T8, T10). HTML report (48.8KB), HTML slides (13.8KB).
- **Setting A (deepseek-v4-flash)**: 0/12 PASS — complete shape collapse.
- **Improvement over v4.5.0**: +1 PASS (T10 now holds shape).

## v4.5.0

- **Setting A (deepseek-v4-pro)**: 9/13 PASS (T1-9 all PASS, T10-13 FAIL on format drift — precheck confirmations and output turns). All substantive outputs produced: HTML report (41KB), HTML slides (12KB), health analysis files.

## Previous Versions

- **v4.2.6**: Both precheck gates hold + outputs reliable. Analysis handoff fix.
- **v4.2.5**: Report gate holds, analysis gate always bypassed. Outputs reliable.
- **v4.3.0**: Best gate behavior but gates didn't lead to execution — reports rarely written.

## Model Compatibility

| Model | Substance | Structured | Suitability | Notes |
|-------|-----------|-----------|-------------|-------|
| deepseek-v4-pro | ✅ Full | ⚠️ Needs activation | ✅ Use | Solid artifacts (HTML, PPT, charts). YAML workflow only fires when skill explicitly invoked in Turn 1 |
| deepseek-v4-flash | ❌ Scripts-only | ❌ None | ⛔ Unusable | Drops all markers, writes standalone .py files, no protocol |
| kimi-k2.6 | ✅ Full | ✅ Full | ✅ Good | Tested with v4.5.0, active shape gate with full YAML |

**Rule:** Only use **pro-tier models**. Flash/light/mini skip the structured workflow and produce junk.

## Recommendation

Use **v4.5.3** with `deepseek-v4-pro` — produces all substantive artifacts. **Include explicit skill trigger** in Turn 1 (e.g., "Use the causal-consultant skill: I'm studying...") to get the full team workflow with `project_state.yaml`.
