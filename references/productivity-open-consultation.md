# Productivity open consultation test

This twelve-turn case uses the 816-row `plm::Produc` state panel to let the
consultant inspect the data, refine the policy question, compare defensible
methods, and choose its own analysis route and support. Exact prompts and
artifact expectations live in [`test-cases.json`](test-cases.json). Apply the
shared rules in [`evaluation-guide.md`](evaluation-guide.md).

Use the public [Rdatasets `plm/Produc.csv`](https://vincentarelbundock.github.io/Rdatasets/csv/plm/Produc.csv) export and remove its first `rownames`
column before renaming it to `data.csv`. The registered data contain 48 states
observed from 1970 through 1986, including `region`, public-capital measures,
private capital, gross state product, employment, and unemployment.

| Checkpoint | Turns | Required result |
|---:|---:|---|
| 1 | 1-3 | The decision, panel structure, data quality, economic constructs, timing, mechanisms, spillovers, and historical boundary are explored before method selection. |
| 2 | 4-6 | The consultant narrows the question, compares plausible approaches, and states one evidence-based recommendation without preparing or executing a scope. |
| 3 | 7-8 | One analysis scope uses any controller-valid route and support selected by the consultant. Approval preserves that exact route, support, scope identity, contract, and claim boundary through completion or valid infeasibility evidence. |
| 4 | 9 | Interpretation uses the approved evidence without converting a bounded or historical result into an unsupported present-day policy effect. |
| 5 | 10-11 | One evidence-bound HTML report scope is approved and records either completed output or valid infeasibility evidence without changing its evidence basis. |
| 6 | 12 | Final synthesis uses existing evidence only and creates no new artifact. |

There is no hidden correct estimator, package, route, support, or numerical
answer. Do not grade whether the consultant's method is best. Judge whether
the selected legal route is stated before scoping, persisted exactly after
approval, completed or blocked honestly, and used consistently in the final
decision language. Additional in-scope diagnostics are allowed. No durable
output is expected before the analysis approval; analysis and report output
require their explicit approval turns.
