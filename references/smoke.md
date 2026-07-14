# Smoke Test — Setting S (3 turns)

Minimal conversation test. No data ever. Quick shape + protocol check.

## When to Use

- After pulling a new skill version — verify shape markers still work
- Before a full Setting A run — catch activation issues early
- Quick regression check after skill edits

## Turn Table

| Turn | Action | Description |
|------|--------|-------------|
| 1 | Domain-aligned opening | Load skill, introduce domain, no data |
| 2 | Probe reasoning | Method or logic question about the domain |
| 3 | Synthesis | Counterfactual or synthesis wrap-up question |

## Prompts

### Turn 1 — Intake
> Use the causal-consultant skill. I'm studying what drives college graduation rates and want to understand the key causal factors.

### Turn 2 — Probe
> How would you think about identifying causal factors here? What's the first thing you'd look at?

### Turn 3 — Synthesis
> If you had to pick one approach to prioritize, what would it be? Just give me your top recommendation.

## Evaluation

Standard 2/3 shape marker check per turn ([> Framing], [+ Consultant Options], [? Next Steps]).

Report: per-turn shape PASS/FAIL + overall smoke-pass/smoke-fail.
