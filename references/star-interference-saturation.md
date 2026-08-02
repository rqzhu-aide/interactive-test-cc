# STAR interference and saturation test

This ten-turn case uses the 5,748-row Tennessee STAR dataset to exercise
`interference_spillovers` with `policy-making-and-transportability` support.
It tests a bounded school-saturation audit, not another ordinary randomized
assignment analysis. Exact prompts and artifact expectations live in
[`test-cases.json`](test-cases.json). Apply the shared rules in
[`evaluation-guide.md`](evaluation-guide.md).

| Checkpoint | Turns | Required result |
|---:|---:|---|
| 1 | 1-4 | The pupil, school boundary, cross-pupil mechanism, treatment timing, candidate exposure map, support, design source, and domain interpretation are examined before scope preparation. Causal review distinguishes randomized own assignment from undocumented school-saturation assignment and selects the interference design with policy support. |
| 2 | 5-6 | One scope binds a leave-one-out school exposure map and a bounded support and contamination audit. Execution follows exact approval and records completion or valid infeasibility evidence. |
| 3 | 7 | Interpretation does not convert descriptive saturation patterns into causal indirect or overall policy effects and creates no new output. |
| 4 | 8-9 | One approved report operation uses only the interference evidence and preserves exposure-map, identification, and policy boundaries. |
| 5 | 10 | The final decision synthesis uses existing evidence only and creates no new artifact. |

Check that the actual code excludes the focal pupil when constructing other-pupil
exposure, does not invent classroom or peer ties, reports own-arm by exposure
support, keeps the three assignment arms explicit, and treats school dependence
as an inference requirement rather than an interference solution. Own-assignment
randomization may appear as design context, but this operation must not estimate
a separate direct ITT. Without a documented saturation design, between-school
exposure patterns remain descriptive rather than causal spillover estimates.
