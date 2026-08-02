# Schooling instrumental-variable LATE test

This nine-turn case uses the 3,010-row Card schooling dataset to exercise the
`instrumental_variables` design with `statistical-validity` support. Exact
prompts and artifact expectations live in [`test-cases.json`](test-cases.json).
Apply the shared rules in [`evaluation-guide.md`](evaluation-guide.md).

| Checkpoint | Turns | Required result |
|---:|---:|---|
| 1 | 1-3 | Instrument, treatment, outcome, timing, missingness, validity assumptions, and weak-instrument needs are reviewed before scope preparation. |
| 2 | 4-5 | One scope binds the `nearc4` instrument, `ed76` treatment, `lwage76` outcome, first stage, reduced form, weak-IV diagnostics, assumption checks, and a local-effect boundary. The approved operation records either completion or valid infeasibility evidence. |
| 3 | 6 | Interpretation does not turn a local complier effect into an average effect for all workers and creates no new output. |
| 4 | 7-8 | One report scope is approved. Its operation uses the IV evidence and records either completed HTML or valid infeasibility evidence while preserving exclusion, monotonicity, and LATE boundaries. |
| 5 | 9 | The final policy synthesis uses existing evidence only and creates no new artifact. |

Check the actual instrument coding, covariate timing, first-stage and reduced-form
evidence, weak-IV inference, analysis population, and local-effect language.
Instrument strength or balance is not proof of exclusion or independence.
