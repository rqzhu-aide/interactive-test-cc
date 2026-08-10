# STAR open consultation test

This twelve-turn case uses the 5,748-row Tennessee STAR dataset for an open
consultation with a school-board user who knows little causal inference. The
consultant explores the data, selects one useful analysis, executes it after
approval, and turns the evidence into an HTML report and decision recommendation.
Exact prompts and artifact expectations live in
[`test-cases.json`](test-cases.json). Apply the shared rules in
[`evaluation-guide.md`](evaluation-guide.md).

| Checkpoint | Turns | Required result |
|---:|---:|---|
| 1 | 1-3 | The decision, data, study design, outcomes, affected pupils, and historical boundary are explained in plain language before method selection. |
| 2 | 4-6 | The consultant distinguishes useful questions, recommends one defensible direction, and explains its comparison, population, assumptions, and claim boundary without preparing a scope. |
| 3 | 7-8 | One analysis scope uses any controller-valid route and support selected by the consultant. Approval preserves the exact route, support, scope identity, contract, and claim boundary through completion or valid infeasibility evidence. |
| 4 | 9 | Interpretation explains the existing evidence, uncertainty, and present-day policy limits to a novice without new computation. |
| 5 | 10-11 | One evidence-bound HTML report scope is approved and records either completed output or valid infeasibility evidence without changing its evidence basis. |
| 6 | 12 | Final synthesis gives an understandable decision implication and next evidence step using existing evidence only. |

There is no hidden correct target, treatment definition, outcome, population,
contrast, estimator, package, route, support, or numerical answer.
Do not grade whether the consultant's method is best. Judge
whether the selected question fits the audited data and board decision, the
selected legal route is persisted exactly after approval, execution or blocking
is represented honestly, and the report and final advice remain within the same
evidence and claim boundary. Infeasibility is acceptable when its unmet
requirement is genuine, tied to the same scope, and used honestly afterward.

Treat the documented within-school random assignment, post-assignment outcomes,
three class conditions, school identifier, and missing classroom and peer-network
identifiers as fixed facts. These facts constrain claims rather than dictate a
route. A direct randomized analysis must not be penalized merely because
interference is conceivable. An interference-oriented analysis must not invent
classroom or peer ties or treat an undocumented school-level exposure as
randomized. A descriptive analysis is acceptable when its noncausal boundary is
explicit.

Manual review should check that a causal-inference novice can understand the
comparison, result or unmet requirement, uncertainty, assumptions, limits, and
recommended action. Define unavoidable technical terms, but do not require
specific jargon or a Consultant Options menu when the consultant can responsibly
recommend a direction. A valid compact data-audit artifact may be created only
on turn 2 and must remain immutable. Analysis and report output require their
explicit approval turns.
