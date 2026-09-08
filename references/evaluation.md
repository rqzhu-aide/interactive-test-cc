# Evaluate Useful Consultation

For the fixture author and independent final reviewer, not the user actor.
Freeze criteria before execution. Review the complete objective from actual
conversation, disclosures, artifacts and available invocation evidence.

## Main Judgments

| Dimension | Ask | Evidence of a consequential problem |
|---|---|---|
| Investigation and proactivity | Did the consultant choose an attainable high-value question, source or review and use its answer? | An answerable, consequential fact the user was unlikely to volunteer is left unasked and affects the result; an uninformative review substitutes for the needed question |
| Scientific and computational quality | Do data meaning, preparation, target, identification, estimator, uncertainty and claims agree? | Wrong rows or dates, post-treatment adjustment, unsupported identification, incorrect computation, or silent target substitution |
| Continuity and user usefulness | Does the user receive understandable, actionable advice consistent with corrections and earlier evidence? | Old rejected advice remains current; the plain-language summary broadens the claim; requested feasible work never reaches a useful conclusion |
| Complete-objective effort | Was user effort and investigation proportionate to progress? | Repeated answered questions, requests for explicitly unavailable material, redundant reviews or unnecessary confirmation before clear work |

Trace the relevant chain: identified uncertainty, specialist finding when
needed, lead disposition, factual contribution/source, interpreted meaning, and
changed or explicitly preserved preparation, strategy or advice. Do not require
every link on every turn. Direct supported work, evidence-only synthesis and
useful stopping are positive controls, not elicitation failures.

Materiality depends on the consequence, not whether an expected sentence
appeared. Comparable valid investigation choices and estimators are allowed.
If the consultant resolves an issue from a reliable accessible source, it need
not ask the user the same question. If an issue cannot be resolved, conditional
advice can be correct. Calling an unasked resolvable issue a limitation does not
excuse a resulting wrong or unnecessarily unhelpful conclusion.

## Independent Checks

Open actual saved code and outputs for material numerical claims. Apply the
case's independent row-level or estimator/uncertainty references and declared
tolerances. Check input versions, event timing, exclusions, joins, model settings,
uncertainty units and the reported population. A run manifest proves neither
that code ran nor that the estimator or interval is correct. Use real execution
logs and, when needed, a rerun in a fresh permitted output folder, leaving the
consultant's completed run intact.

For a valid unanticipated method, review its identifying argument and compatible
numerical reference without moving the target or adding facts. If a necessary
oracle is absent, record missing coverage, not an automatic pass or failure
because it differs from the preferred method. A later fixture revision is new
evidence, not a repair to the original score.

Assess comprehension from the actual user-facing explanation: can this user
identify the comparison, finding or limitation, and next action? Actor agreement
or satisfaction alone is not evidence. Any optional blind-reader comprehension
check receives only the public exchange and audience profile, not the answer key.

## V7 Behavioral and Evidence Checks

Count at most one substantive specialist review per assistant turn, whether
local or delegated. Related diagnostics or several guides can serve one bounded
review. Two independent reviews inside one worker are still two. Clarification,
correction and synthesis may use zero. Do not infer compliance from agent names,
final prose or provider-reported agent-turn counts alone. Missing trace coverage
remains unobserved.

Use the candidate's read-only v7 verification and captured journal/run records
for project continuity, pre-result plans, immutable completed work, input lineage
and truthful incomplete/failure states. Do not impose v6 headings, approval
phrases, scope/receipt schemas, fixed artifact counts or a state revision on
every turn. Ordinary no-output audits need no run; saved preparation and new
target computation do. A returned user-facing answer need not make every open
question disappear or close an honestly incomplete operation.

## Outcomes Without False Passes

Keep these fields separate in the assessment:

| Field | Values and meaning |
|---|---|
| `test_validity` | `valid`, `invalid`, `unverified`: whether fixture execution, private-information boundaries and required continuity are established |
| `outcome` | `objective_met`, `useful_stop`, `incomplete`, `execution_error`: what the consultation actually achieved |
| `coverage` | Each required criterion is `observed`, `unobserved` or `not_applicable`, with evidence/reason; a counterexample is observed, not missing |
| `findings` | Defects with `owner` (`consultant`, `simulator`, `harness`, `fixture`, `environment`), `severity`, `criterion`, `description`, consequence and actual `evidence_refs` |
| `quality_rating` | Derived as below, not chosen to conceal a finding or incomplete objective |
| `resources` | Actual measured work, provider coverage, limits and any breaches, distinct from scientific validity |

Use `not_applicable` only for a predeclared conditional criterion whose trigger
does not apply. Do not waive a required behavior because the consultant did not
reach it; that coverage remains `unobserved`. An early valid discovery may earn
credit while leaving a case's required later correction mechanism unexercised.

Derive the rating in this order:

1. An attributable material/fundamental consultant defect yields `fail`, even
   if a later cap prevents completion. With invalid/unverified execution, retain
   that bounded defect but do not claim a valid whole-case comparison.
2. Otherwise an invalid/unverified test, unobserved required criterion, resource
   breach or execution error yields `inconclusive`. So does an outcome that is
   neither `objective_met` nor a `useful_stop` satisfying the case's frozen
   stopping criteria; such a useful stop need not deliver an unattainable estimate.
3. With valid execution, required coverage, no cap breach and `objective_met`
   or a case-permitted `useful_stop`, minor consultant defects yield `weak`;
   no consultant defects yield `pass`.

A useful stop must answer what the user can conclude or do within the declared
limits. Refusal alone is insufficient. An attainable ready-analysis case cannot
pass by refusing or providing only general advice. An empty findings list does
not override missing evidence. An attempt ending at a cap before completion is
`incomplete`, not `useful_stop`.

Severity meanings: `minor` leaves the substantive decision equivalent;
`material` changes scientific support, requested utility or a meaningful user
decision; `fundamental` destroys trustworthy continuity/evidence or represents
unperformed work as completed. Simulator leaks, inconsistent worlds and transport
errors remain owned by the responsible component, not blamed on the consultant.
Retain the original failed record when a defect is corrected.

## Reporting and Comparison

Produce a compact outcome summary, evidence-linked findings, criterion coverage
and resource table, with the complete private dossier available for inspection.
The dossier binds fixture/candidate/configuration identities to every sent and
received message, disclosure, source release, run artifact and failed attempt.
Do not include secret credentials in captured configuration or reports.

Count user messages, consultant turns, substantive reviews, repeated/repair work,
active wall time and user-wait time separately. Report input, cached input,
output, provider time and cost only with their collection scope and semantics.
Unavailable telemetry is `null`/unknown, not zero. Avoid double-counting worker
usage already included in provider totals. Count failed attempts too.

For the initial pilot use two fresh repetitions per case/candidate after a host
smoke test; compare under frozen matched limits. Current token cost is accepted
for exploration, not a reason to optimize before testing utility. Set any new
token/cost envelope before these runs, without changing historical failures.
Report protocol and scientific results separately for any v6/v7 comparison.
Cross-host/model results do not isolate a skill effect. Small pilots are
diagnostic evidence, not release qualification, population reliability or proof
that simulated users match real people. Follow up with real-user trials later.
