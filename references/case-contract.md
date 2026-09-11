# Frozen Case Contract

For fixture authors and run operators. The four problem/persona compositions
use this contract and the shared validator described in [runner.md](runner.md).

## Information Boundaries

Prepare separately accessible public, world, actor and reviewer materials. The actor packet is private to
the user simulator, not a file to attach to the consultant.

| Packet | Required content |
|---|---|
| Public | Natural initial request; initial files and dictionaries; audience information a real user would share; valid initial history only when the case calls for it |
| World (`world.json`) | Immutable study facts or documented unknowns, real-source provenance or synthetic generation process, and available evidence; separate from actor access and reviewer judgments |
| Actor | User goal and decision constraints; domain/statistical fluency; factual beliefs with certainty and source; facts the user can learn and how; accessible source inventory; disclosure/correction rules; unknown and declined-source replies; allowed action choices and stopping behavior |
| Reviewer | Answer key and independent reference outputs grounded in the world; acceptable alternative paths and claim boundaries; observable success/failure criteria; actor fidelity criteria; required coverage; fixture validation and limitations |

The actor and consultant never receive the world dossier or reviewer key. Freeze
persona differences in initial knowledge, mistaken beliefs, learning conditions,
reasoning and cooperation, rather than fluency alone. Actor-accessible facts are
an explicit subset of the world and accessible source inventory; a true world
fact is not automatically something the user knows or can obtain.

For persona fixtures, `case.json` includes `world: "world.json"`, `world_id`,
`world_version` and `persona_id`. Match the dossier's world identity and the
actor's `persona_id`, and bind the private dossier in the fixture hashes.
The runner can still read older external frozen run packages; do not rewrite them.

Facts are not necessarily identifying assumptions. The user may know how a list
was assembled but cannot establish exchangeability just by agreeing to it.
Separate an inaccurate user belief from the underlying truth and freeze the
event by which the user can learn a correction. Do not secretly alter the world.

The author also supplies a private manifest containing:

- `suite_version`, `case_id`, `case_version`, communication `edition`, author
  and, when relevant, `base_case_id` plus the exact adaptation delta;
- generator identity and seed, and exact hashes of all packets, datasets,
  dictionaries, staged documents and independent reference outputs;
- required shared tools/packages, access conditions, source-release mapping,
  completion conditions, required observations and prospectively set limits.

For an end-to-end report case, set `completion_contract: "full_report"` in
`case.json`. Absence or `"focused"` retains the older case-specific endpoint.
The full-report public request, actor goal/action/stopping rules and reviewer
criteria must agree that a saved consultant report is required. Freeze the
audience and necessary content, allowing equivalent structure and scientifically
justified claims. A complete bounded descriptive report can satisfy the goal
when causal identification is unsupported; a recap alone cannot.

Full-report completion requires captured evidence of a completed, verified
report run and its actual saved output. The reviewer separately checks report
substance, source/result consistency and applicable readback/render validation.
Keep the consultant report separate from the final testing assessment. Older
external packages retain their recorded endpoint; do not change them in place.

For `consultation-loop-v1`, behavioral validity is separate from the scientific
world and report endpoint. Preserve actual proposal, later choice, protected
start, findings discussion and report selection chronology. An initial desire
for a report cannot authorize a later action automatically. An extension has
its own bounded choice and returns to discussion. Scope revisions, questions,
pause/resume and reopening preserve their user meaning when they occur; none is
a mandatory quota in each case. A faithful user stop without a report leaves a
full-report objective incomplete, without automatically being an actor defect.

Keep the manifest and descriptive case IDs away from the consultant. Use neutral
filenames, working directories and session labels, not names such as
`hidden-post-treatment-trap`. Record originals privately. Initial consultant
loading is permitted; injecting expected findings or evaluator instructions is not.

## Fact and Reply Rules

Each actor fact needs a stable `fact_id`, a factual `statement`, `certainty`,
`source`, `available_when` and any `disclosure_condition`. Source references can
be user recollection, a supplied record or a declared contact, with uncertainty
preserved. Unknown/unobtainable information needs an explicit disposition.

Each response rule identifies its semantic condition, fact/source IDs it may
reveal, any constraints on the reply, and the resulting availability change.
Use events such as a request about the recorded event, not exact words or a
particular assistant turn. Combined questions may satisfy several conditions
at once. Repeated questions do not unlock progressively better facts by default.

Source rules specify the immutable file version, what request makes it eligible,
how it becomes available and any genuine prerequisite. Eligibility is not an
instruction to send every eligible source at once. The persona's disclosure
policy supplies the current topic's record or necessary bundle, acknowledges
remaining requests and follows up as those topics arise. A broad request can
establish those requests without a filename password. Keep short necessary
answers and requested files intact; no invented delay or access barrier is
allowed. Record receipt separately from inspection. Preserve pending requests
in the actor's existing disclosure history, not a second editable memory file.

Action rules allow choosing among consultant options without knowing the scoring
key: for example prefer work on existing records, decline new staff contact,
or authorize a specified preparation once its meaning is understood. A bare
unknown is not blanket authorization. Freeze how learning, corrections and
decisions may change with observable evidence. Preserve supported changes across
turns using the [actor update record](user-simulator.md), without changing the
world or automatically treating consultant assertions as facts. Bounded pressure
needs finite semantic conditions and an attainable honest report endpoint; it
must not force endless resistance or a predetermined estimator.

If a question reaches an unspecified fact, the actor says it does not know and
records a fixture gap privately. If that gap materially affects evaluation, mark
the case invalid for that claim. Fix the version and rerun all candidates being
compared; do not invent facts or repair one candidate's run in place.

## Randomization and Reproducibility

Use the four problems and four independent personas in the
[composition guide](problem-persona-matrix.md). Any of those 16 pairings is
supported; the selected scope determines which to run. The same problem's world,
scientific sources and criteria remain invariant across personas. Initial
understanding and natural disclosure differ. Generate no new study world during
a conversation or additional crossed factors without review. The old fixed
case catalog is removed; prior versions remain in Git and frozen run packages.

Composed manifests add `problem_id`, `problem_version`, `persona_version` and
`target_turns`. Private `problem.json`, `persona.json` and `composition.json` are
hash-bound alongside ordinary files. The target is operator/reviewer metadata;
it does not appear in actor packets, govern release or change report completion.
Operational caps remain a separate frozen configuration.

Useful axes include operational definitions, linkage/missingness patterns,
source availability, user knowledge, statistical fluency and wording. A changed
assignment mechanism is a changed scientific edition: regenerate coherent data
and documentation and review its identifying argument. Do not rewrite documented
real-study facts. Label hypothetical adaptations explicitly in fixture records.

Preserve generated bytes and actual replies as well as seeds. A seed does not
guarantee identical language-model behavior. Paired candidates receive the same
world and semantic response policy, not a forced identical transcript. Alternate
candidate order and keep model/configuration/tool conditions matched when the
comparison concerns the skill alone. Cross-system comparisons are separate and
must identify the host/configuration differences.

## Validation Before a Scored Run

Check that public files agree with the world, actor knowledge is attainable, each
planned source can be supplied, and legitimate unknowns have useful dispositions.
Review semantic-equivalence examples and a no-question response before freezing.
Do not require discovery of inaccessible truth or a single preferred route.

For preparation, freeze row IDs, inclusion/exclusion reasons, expected joins and
timing boundaries using an independent calculation. For estimation, define the
target, valid reference calculations and tolerances before consultant output is
seen. Synthetic causal truth is not the same as the realized estimator: do not
fail a sound estimate because it differs from the generating effect, or require
every single confidence interval to contain it. Coverage claims require their
own repeated-simulation design. Real observational data do not supply a known
causal truth merely because a reference analysis exists.

Author-created examples and protocol rehearsals are not live observations. A
reviewed blueprint becomes a runnable case only after actual materials, hashes,
world/actor/reviewer packets, oracle checks and run limits have been frozen.
