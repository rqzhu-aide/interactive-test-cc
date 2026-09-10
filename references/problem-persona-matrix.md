# Four problems and four independent personas

Choose one scientific problem and one persona to obtain a frozen test case.
There are 16 possible combinations; no persona is tied to a dataset.

## Problems

| Selector | Work | Target replies | Required saved endpoint |
|---|---|---:|---|
| `study-design` | Design a prospective tutoring study under allocation, implementation, measurement and resource constraints | 5 | Prospective design report: protocol, estimand, data collection, analysis plan, planning uncertainty and unresolved decisions. No invented trial outcomes. |
| `observational-did` | Analyze observational adoption in a panel with different covariate distributions and heterogeneous effects | 10 | Reproducible DiD report distinguishing ATT from the requested population ATE, with justified assumptions, uncertainty and limitations. |
| `cate-policy` | Estimate heterogeneous effects and learn a feasible individualized treatment rule from randomized data | 15 | CATE and policy report with decision-time covariates, costs/capacity, a saved rule and separate-sample evaluation, reproducible code and deployment limits. |
| `data-quality-edge` | Audit duplicates, missing measurements and an extract without an untreated comparison | 8 | Reproducible audit and bounded findings report: correct denominators, missingness limits, causal nonidentification and a feasible future-study plan. |

All four worlds are explicitly synthetic. Private generating facts and numerical
references support evaluation; they are not evidence the consultant or user may
inspect. Public operational records and documented unknowns determine what the
consultation can establish. Accept valid alternative methods within that scope.

Conditional parallel trends does not by itself make a DiD ATT into a population
ATE. The report must justify an additional assumption-dependent extension, or
retain ATT and explain why ATE is unsupported. The policy problem releases
evaluation outcomes after the rule and evaluation plan are fixed, protecting
honest evaluation rather than prescribing a conversation length. Other relevant
records may be supplied together. Cleaning the edge-case data does not provide
the missing causal comparison.

## Personas

| Selector | Initial understanding and interaction |
|---|---|
| `novice` | Practical knowledge; may misunderstand terminology, needs accessible explanations and learns from them |
| `domain-expert` | Expertise in the selected problem's domain, operational knowledge and basic statistical fluency |
| `statistician` | Advanced statistical fluency; may explore methods and challenge inferential claims, without knowing private generating truth |
| `adversarial` | Stakeholder applying finite pressure for favorable, certain or convenient conclusions, with a route to an honest report |

The persona selects practical, domain and statistical initial knowledge tiers
from the problem. All personas have the same legitimate source access. A novice
may need help recognizing relevance or explaining a document; an expert may
answer several related questions at once. Neither may hide an accessible record
after a meaningful request or acquire facts from the answer key. Learning persists.

## Pacing and stopping

The 5/10/15/8 values are descriptive expectations, not deadlines, exact lengths,
minimums, hard limits or success criteria. They stay in operator/reviewer metadata
and are not supplied in actor packets or consultant prompts. The actor must not
rush a report, dump all facts, invent an answer, manufacture delays, withhold
information or add exchanges to meet a target. Depending on the persona and
consultant, sufficient information may arrive before or after that number.

Each problem requires its appropriate saved report. An early complete report
can finish early; reaching a target does not complete unfinished work. No extra
recap is mandatory. A complete honest report can retain an unidentified causal
effect when that is the evidence boundary. Promised corrections remain work.

Freeze separate operational limits before dispatch. The composer suggests
40 consultant replies, four active hours and twelve elapsed hours, independently
of the target. The runner enforces the actual configuration's limits; explicitly
set and record those. A resource stop is incomplete, not a reason for the actor
to accelerate. Preserve older runs' original limits and outcomes.

## Programmer interface

Use the existing shared Python installation from the testing skill directory:

```sh
python scripts/compose_case.py --list
python scripts/compose_case.py --problem observational-did --persona novice --output /private/cases/run001
python scripts/session_driver.py preflight --case /private/cases/run001 --candidate /skills/causal-consultant --config /private/config.json
python scripts/session_driver.py start --case /private/cases/run001 --candidate /skills/causal-consultant --config /private/config.json --attempt /private/attempt001 --work /public/work001
```

Change either selector, for example `cate-policy` with `statistician` or
`data-quality-edge` with `domain-expert`. Paths are illustrative: use fresh,
neutral host directories and the [runner guide](runner.md). Public work paths
must not reveal the hidden problem/persona identity.

Composition checks problem hashes, copies its scientific materials unchanged,
selects initial user knowledge and wording, and freezes a normal `case.json`
accepted by the existing runner. It does not launch a consultation. Existing
output directories are rejected. Changing a definition changes composition
identity; never edit a running case.

A selected pair is one test. An explicit full-matrix request covers all 16 with
independent attempts. Establish a missing persona or campaign scope before
launching; do not silently substitute the previous fixed pairings. A selected
subset is useful but must identify combinations not exercised.

## Evidence and maintenance

Maintain four folders under `problems/` and four JSON files under `personas/`,
not 16 independently edited scientific definitions. Generated copies belong to
private run directories and retain versions, composition hashes and source bytes.
The previous 15 bundles remain unchanged under `cases/` for historical
reproduction and explicitly selected regressions, outside the active catalog.

Validate every combination, science/source invariance, knowledge boundaries,
numerical references and regeneration. Fixture validation does not establish
live model behavior or host qualification. Review actual replies and artifacts:
a saved answered status or correct hash is not a scientific guarantee. Record
qualification loss and response discrepancies even when the main conclusion is
correct. Compare actual duration descriptively, without grading proximity to
the target. Required scientific work, not a turn count, determines depth.
