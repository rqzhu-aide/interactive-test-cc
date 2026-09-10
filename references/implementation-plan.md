# Implementation Plan for the V7 Testing Skill

- Class: planning
- Status: modular four-problem/four-persona revision implemented and locally validated; live qualification remains pending
- Date: 2026-09-10
- Package: `interactive-test-cc`, `7.0.6`
- Current consultant target: identified `7.0.6` snapshot, with `7.0.0`, `7.0.1`, `7.0.2`, `7.0.4` and `7.0.5` compatibility; not any directory
  merely labelled v7

## Scope and Current Deliverables

The entrypoint and references define an adaptive Hermes-user/Claude-consultant
procedure with independent [problems and personas](problem-persona-matrix.md),
separate world/actor/reviewer contracts and independent evaluation. Four problem
definitions support all four personas through a composition helper and the
existing runner. Old pairings and pilot fixtures remain unchanged historical
regressions. The [runner](runner.md) implements the minimal adaptive transport
and ships a College adaptation with exact hashes and an independent numerical
self-check. Local subprocess checks do not establish a real-host consultation.
Release 7.0.6 aligns the testing and consultant package versions without
installing either skill or launching a live campaign.

The 7.0.6 modular revision creates study-design, observational DiD/ATE,
CATE/policy and data-quality problems, with target lengths 5/10/15/8. The user
confirmed these are descriptive expectations and explicitly rejected pacing
that tries to finish within them. Targets remain outside actor context;
scientific completion and separate operational caps determine stopping. Initial
knowledge and natural disclosure differ by persona, while the problem's world,
source access, numerical references and report endpoint remain invariant.

Local validation on September 10 passed all 87 tests, including 20 modular tests
covering all 16 compositions and independent numerical checks. Two isolated
actor rehearsals exercised novice policy discussion and adversarial study-design
discussion, with two replies each. These used supplied consultant messages;
they are not live Hermes/Claude consultations or evidence of typical turn counts.

The 7.0.2 investigation-depth revision adds four paired synthetic contrasts and
evidence-based review of investigation and scope closure. Its staged comparison
of frozen 7.0.1 and 7.0.2 candidates is defined in [pilot-cases.md](pilot-cases.md),
beginning with 12 consultations. That later addition preserves the original
College fixture and V7P01-V7P04 blueprints; the remaining sections record the
broader V7P implementation plan rather than completed live results.

The 7.0.3 endpoint revision added two full-report child cases as the then-default
broad/end-to-end tests. A saved consultant report is distinct from
the actor's conversational recap and the independent test assessment. The
adapter checks actual completed report evidence before accepting a successful
full-report outcome. Original cases and the staged 12-consultation comparison
retain their focused endpoints. New full-report limits are prospective; the
live-host evidence and measured round-count distribution remain pending.

The 7.0.4 persona revision made the novice grant, cooperative STAR domain expert,
advanced Schooling statistician and bounded-pressure College user the then-default
broad full-test set. Explicit individual selection remains allowed. Separate
private world dossiers from actor knowledge, beliefs and access, and from reviewer
answer keys. Preserve learning and corrections through evidence-cited optional
actor update records, without numeric trust or another controller. Each case has
provisional 24-exchange capacity, with no minimum or guessed round count. The
earlier 7.0.3 and focused fixtures retain their identities and endpoints.

The 7.0.4 release alignment named consultant 7.0.4. Its metadata change
retains the 7.0.2 observation interface; the runner explicitly accepts 7.0.4 while
continuing to reject unlisted versions, including 7.0.3. Frozen persona case 1.0.0
targets and hashes stay unchanged. Each new attempt binds the actual candidate
identity under the [persona release profile](persona-cases.md); prior validation,
rehearsals and 7.0.1/7.0.2 comparisons are not relabeled as 7.0.4 consultations.

The 7.0.5 compatibility revision binds observations to the actual project root
and captures durable interpretations, exchanges and exact final-response
correspondence. Its optional question-aware capability distinguishes user
questions from consultant information requests, retaining answer timing and
pending questions for independent review. Earlier snapshots retain their own
renderers; no delivery record is created by the observer. Full-report completion
still requires the completed, verified saved artifact. Frozen persona cases and
earlier evidence remain unchanged; live qualification is still pending.

The 7.0.6 release retains the durable-exchange observation contract, including
optional question routing and earlier renderer behavior. Explicit compatibility
tests accept 7.0.6 and reject unlisted versions and previews. Its evaluation
clarifies that complete design documentation does not waive available data
consistency checks or justify unsupported claims that all checks passed.

The September 7 reorganization makes this definition the testing repository's
root skill. Pre-v7 files and results are preserved in the sibling local
`interactive-test-cc-v6` archive, with Git history/remotes retained here. Do not
modify those archive files or import their controller validators into v7.
The consultant is likewise at its formal repository root, with its v6 files in
`causal-consultant-v6`. Layout promotion does not qualify the consultant;
keep consulting behavior unchanged while testing.

The consultant architecture remains owner of product behavior and release gates.
This package owns the portable test procedure. Existing N/P/T fixed cases,
CQ01-CQ06 and elicitation variants keep their original identities and history.
New V7P pilots are adaptations with explicit mappings, not replacements or
retroactive passes. The user's acceptance of current token cost defers further
optimization; it does not change recorded cap failures.

## 1. Freeze a Small Pilot and Host Profile

Use [case-contract.md](case-contract.md) and [persona-cases.md](persona-cases.md)
for the default four-case full-report set. The preserved V7P01-V7P04 authoring
plan remains in [pilot-cases.md](pilot-cases.md) for selected regressions.
Provide public, world, actor and reviewer materials separately. Preserve seed/generated
bytes, source hashes, scenario versions, user fluency and semantic triggers.
The earlier V7P diagnostic plan uses two fresh repetitions per case.
Do not generate a large random campaign yet.

Review the scientific worlds and independent checks before consultant execution.
Confirm the ready-analysis case really permits useful work without another user
fact; confirm the unavailable-information case permits useful advice. Exercise
alternate valid questions and a no-question recommendation against the actor
rules. A source can be requested without its exact filename. The actor must not
need the expected estimator or grader instructions.

On the actual Hermes target, identify existing shared tools and the authorized
candidate-loading mechanism. Verify CLI capabilities, role/context boundaries,
private-file isolation, session continuity and trace/usage availability under
[hermes-claude.md](hermes-claude.md). Request missing global/user-wide dependencies
instead of downloading private tool copies. Freeze numeric run limits suitable
for complete objectives; do not inherit the earlier bounded-audit token ceiling.

Acceptance: four versioned material bundles with passing row/numeric self-checks
where required, reviewed actor rules, and a documented host profile. A blueprint
alone does not meet this step.

## 2. Implement the Small Adaptive Adapter

Implemented files (see runner.md for the callable interface):

- `scripts/session_driver.py`: `start`, `step`, `inspect`, `finish` entrypoints,
  neutral public staging, private source/disclosure binding and attempt storage;
- `scripts/claude_transport.py`: one explicit-session invocation, raw capture,
  timeout/cancellation and verified host options;
- `tests/test_session_driver.py` and `tests/test_claude_transport.py`: deterministic
  adapter tests with fake subprocesses and temporary contained projects.

Use the standard library and shared installed tools where possible. Reuse the
ideas in the sibling archive's `scripts/send_one.py` for exact session transport
and selected provenance/evidence utilities in its `scripts/run_all_turns.py`.
These are `../interactive-test-cc-v6/` paths relative to this repository root,
not existing v7 scripts. Avoid importing its large v6 run loop or hidden
controller dependencies. Any copied utility needs focused tests against the
new artifact layout.

Do not carry forward automatic permission bypass, truncated-only failure logs,
missing-usage-as-zero, implicit installation, fixed prompt order, response-shell
checks, idle-state/revision-growth demands, numbered approvals or fixed artifact
counts. Put v7 structural checks in a small candidate-specific observation
profile, separate from the semantic evaluator. The driver transports actor
messages; it must not generate study facts or choose causal routes.

Acceptance checks:

- Fresh session and exact resume succeed; changed/missing session identity stops
  before another turn. No ambient fallback or silent resend after uncertainty.
- Unauthorized source release and private-path leakage are rejected; allowed
  releases preserve hashes and give the actor/consultant only their allowed view.
- Timeout, cancellation, invalid/empty JSON and nonzero exit retain raw evidence;
  process cleanup affects only that attempt. Whole-run limits include failures.
- Missing telemetry stays unknown; worker/parent totals are not double-counted.
- Evidence-only synthesis without a journal write is allowed. An honestly
  unfinished run is visible; it is not magically completed by an artifact check.
- Finalization detects changed review evidence and cannot turn incomplete or
  unobserved work into a pass because no defect was listed.

Mocked transport tests establish adapter logic only. They do not establish that
the actual host resumes Claude correctly or exposes worker usage.

## 3. Connect the Actor and Independent Review

Hermes uses one persistent actor context initialized with only the user packet
and reply policy. Keep the author/reviewer context separate. Each actor reply
has a private explanation through fact/rule IDs, but no chain-of-thought demand.
Optional knowledge, belief and decision updates retain visible evidence and are
carried in the actor's own history, without adding the hidden world or reviewer
key to that context. Only public text and released materials are dispatched. If the host cannot
support the intended information separation, record it and do not present the
run as a blinded test.

Build a compact dossier from actual messages, disclosures, source releases,
candidate/configuration identities, v7 evidence and trace coverage. Retain raw
artifacts for focused inspection. A separate reviewer uses the frozen scientific
criteria and independent references, never the actor's satisfaction as the score.
Review actor fidelity as separate coverage/findings, including supported learning,
semantic source release and finite pressure with an honest report route.
Implement the outcome/validity/coverage/rating rules in
[evaluation.md](evaluation.md) with explicit missing-evidence cases.

Acceptance: protocol rehearsals demonstrate equivalent questions, compound
questions, brief unknowns, legitimate source release, no-question direction,
goal completion and correction. They must also show that unrequested hidden
facts are not supplied to rescue the consultant. Label these rehearsals as
simulated; do not mix them with live records.

## 4. Run a Host Smoke Test, Then the Four Pilots

After authorized host setup, perform a small real transport/isolation smoke test
using harmless public materials. Verify candidate loading, session resume and
captured telemetry semantics. Do not reveal real pilot answers in that test.
Record its actual output; a unit test named live is not a substitute.

Run the selected problem/persona pairs to their declared report objectives.
An explicit full matrix contains all 16 pairs. Record
fixture self-checks, simulated actor rehearsals and actual live results separately;
local/fake execution cannot establish a live pass.

The preserved V7P diagnostic plan runs V7P01-V7P04 to each declared objective, two fresh repetitions
per case/candidate. Stop at the objective, case-permitted useful stopping, a
frozen cap or a continuity/environment failure. Preserve all attempts and do
not patch the consultant during a run. Any correction produces a new candidate
identity and a fresh affected-case evaluation.

Inspect the actual preparation rows, ordinary estimate and uncertainty, helpful
limits and revised advice after resume. Review one-specialist cadence using
available substantive trace evidence. Keep missing observability explicit.
Report complete-objective cost descriptively before considering more optimization.

Acceptance for this diagnostic pilot: every repetition has valid execution,
required observations, a met objective or allowed useful stop, no cap breach and
no material/fundamental consultant defect. Minor findings remain visible. A
failure is useful evidence for revision but not pilot qualification. These eight
runs for one candidate do not complete the consultant's release requirements.

## 5. Add Targeted Variants and Broader Scientific Coverage

After a trustworthy pilot, add a small declared set of random seeds/communication
editions and source-availability variants. Hold back some variants from tuning.
Compare paired candidates on the same world and response rules, allowing their
questions and conversation lengths to differ. Keep failures, fixture gaps and
resource-censored attempts in the report.

The College policy adaptation is now at `cases/college-policy-v7`, version 1.1.0;
the historical diagnostic remains unchanged. The persona revision adapts STAR and
Schooling with documented scientific facts and data fingerprints preserved while
replacing expert turn scripts with user goals and semantic disclosure. Further
discovery coverage remains a separate extension. Review expected claims
and analysis checks independently. Keep old v6 approvals and workflow grades in
the v6 baseline only. A shared scientific comparison must name the versions and
profile differences rather than call the two procedural suites identical.

Extend to the full CQ cases and parent release gates with explicit coverage
mapping. Cross-system trials and real-user feedback remain needed before making
claims about general user usefulness or skill-only performance effects.

## Definition Validation and Handoff

Before publishing this definition, run the shared skill validator, check local
links and role-routing consistency, and independently rehearse the actor policy.
These are document/protocol checks, not executed pilot results. When code is
added, run its tests plus the legacy suite if any shared legacy file changed.
Update this status only with inspectable evidence.

Git staging, commit and push are separate actions. At handoff, identify the new
package and changed design pointers so another programmer can review/stage only
the intended files. Do not describe uncommitted local work as backed up remotely.
