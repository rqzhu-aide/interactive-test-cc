# Schooling instrumental-variable LATE test

This ten-turn case uses the 3,010-row Card schooling dataset to exercise the
`instrumental_variables` design. `statistical-validity` support is allowed when
concerns exceed the IV route's normal diagnostics, but it is not mandatory.
Exact prompts and artifact expectations live in
[`test-cases.json`](test-cases.json). Apply the shared rules in
[`evaluation-guide.md`](evaluation-guide.md).

| Checkpoint | Turns | Required result |
|---:|---:|---|
| 1 | 1-4 | Instrument, treatment, outcome, timing, missingness, domain context, validity assumptions, and weak-instrument needs are reviewed before scope preparation. |
| 2 | 5-6 | One scope binds the `nearc4` instrument, `ed76` treatment, `lwage76` outcome, first stage, reduced form, weak-IV diagnostics, assumption checks, and a local-effect boundary. The approved operation records either completion or valid infeasibility evidence. |
| 3 | 7 | Interpretation does not turn a local complier effect into an average effect for all workers and creates no new output. |
| 4 | 8-9 | One report scope is approved. Its operation uses the IV evidence and records either completed HTML or valid infeasibility evidence while preserving exclusion, monotonicity, and LATE boundaries. |
| 5 | 10 | The final policy synthesis uses existing evidence only and creates no new artifact. |

Check the actual instrument coding, covariate timing, first-stage and reduced-form
evidence, weak-IV inference, analysis population, and local-effect language.
Instrument strength or balance is not proof of exclusion or independence.
