---
name: interactive-test-cc
description: Define, prepare and evaluate adaptive multi-turn tests of causal-consultant v7, with a Hermes simulated user and a consultant accessed through Claude Code. Use for end-to-end investigation, reproducible analysis and saved reporting, or explicitly focused tests of elicitation, preparation, useful stopping and continuity.
metadata:
  version: "7.0.5"
---

# Adaptive Causal Consultation Testing

Test whether the consultant helps users with different knowledge, reasoning and
cooperation achieve a useful, scientifically defensible outcome. Do not supply
a sequence of expert analysis
instructions and call compliance proactive consulting.

The default coverage is the four [persona full-report cases](references/persona-cases.md).
Earlier full-report cases and focused fixtures remain regression coverage under
the [pilot guide](references/pilot-cases.md). Fixture validation, actor rehearsal
and live qualification are separate evidence stages; see the persona guide for status.
Use the [runner guide](references/runner.md) for startup, adaptive steps and review.
Local subprocess tests do not establish Hermes/Claude compatibility. The actual
host smoke and four V7P pilot runs remain pending.

Target: `causal-consultant` `7.0.5` (also compatible with `7.0.0`, `7.0.1`, `7.0.2` and `7.0.4`),
pinned to the actual tested snapshot. The investigation-depth comparison uses
the frozen `7.0.1` baseline and revised `7.0.2` candidate.
The [persona release profile](references/persona-cases.md) preserves the frozen
case identities while binding each new run to its actual candidate. The 7.0.5
profile also verifies the helper's `durable-exchanges-v1` capability and retains
the observed turn/exchange views. It records `user-question-routing-v1` when
present; earlier 7.0.5 snapshots retain their own response contract. Consultant
`7.0.3` and later unlisted candidates require an explicitly checked compatibility profile. Preserve
the pre-v7 testing skill, runner, fixtures and results in the sibling local
`interactive-test-cc-v6` archive. This repository root now contains the v7
definition; the former nested `interactive-test-cc-v7` folder is retired.
Do not send v7 through the archived controller or approval validators.

## Responsibilities and Reading

Hermes coordinates the test and supplies the simulated user's messages; Claude
Code hosts the consultant. Separate these roles by information, not a swarm of
new agents on every turn:

| Role | Reads | Produces |
|---|---|---|
| Fixture author | [Case contract](references/case-contract.md), selected [persona case](references/persona-cases.md) or [regression blueprint](references/pilot-cases.md), [evaluation rules](references/evaluation.md) | Frozen public materials, private world dossier, actor packet and reviewer packet |
| User actor | [Reply policy](references/user-simulator.md), actor packet, visible conversation and legitimately received materials | Persona-appropriate reply and private disclosure/update record |
| Run operator | [Runner guide](references/runner.md), [Hermes/Claude contract](references/hermes-claude.md), frozen run configuration | Exact-session transport and captured evidence |
| Independent final reviewer | [Evaluation rules](references/evaluation.md), reviewer packet and actual evidence | Evidence-backed outcome, findings and coverage limits |

Read only the references for the current role. The actor must not read the pilot
answer criteria, private `world.json`, reviewer packet or consultant's
internal reasoning/state to choose its next reply. If the same model authored
the fixture, start an actor context containing only its allowed packet. The
final reviewer uses a separate context, not the actor's self-assessment.
These can be separate phases; additional live-agent services are not required.

For adapter development or deployment readiness, use the
[implementation plan](references/implementation-plan.md). Do not install packages, change global settings,
replace an installed consultant or launch a campaign merely by loading this skill.

## Consultation Loop

For a broad request to test the consultant, or an explicit full/end-to-end test,
cover all four persona cases, each with `completion_contract: "full_report"`.
An explicitly selected individual case is allowed; identify that narrower coverage.
Each public request and actor goal includes the consultant's saved scientific
report. A short recap,
analysis output or the testing reviewer's assessment is a different deliverable.
Honor an explicitly selected focused case, but identify its narrower coverage.
Freeze a suitable full-report adaptation before running if none matches the
requested study; do not reinterpret an old focused result as an end-to-end test.

1. Freeze the scenario, material identities, actor rules, candidate, environment
   and whole-consultation limits. Verify that private materials are outside the
   consultant's permitted access, not merely in another working directory.
2. Start a fresh consultant project and conversation with only the public
   request and initial materials. Explicitly invoke the selected consultant
   skill in the agreed host invocation, without method or rubric hints.
3. Observe the actual user-facing reply. Answer the consultant's most consequential
   information request, distinguishing it from an answer that quotes the user's
   own question. Use
   currently known facts and the persona's reasoning and cooperation. Keep
   the answer concise enough for the question without a universal sentence limit.
   Supply available
   material when the corresponding request warrants it. When no question is
   asked, respond to the recommendation according to the user's goal and bounds.
4. Record the reply, disclosure/source IDs and any attachments privately; send
   only the natural-language message and released files. Resume the exact same
   consultant session. Never select the next message from a fixed turn number.
5. Continue until the frozen objective or its permitted useful stopping condition
   is reached, or a declared limit/failure ends the attempt. In a full-report case,
   continue from investigation and supported analysis through report delivery and
   any needed correction. Then independently review the conversation, committed
   evidence, code and report. A missing report leaves that objective incomplete.

Do not stop after a fixed number of rounds or a convenient first result. A round
is one consultant response to a dispatched user message; the actor's final stop
record is not another round. Internal Claude agent/tool turns are a separate
limit. Use the [runner's prospective capacity](references/runner.md), without
turning its ceiling or a planning estimate into a required conversation length.

The actor cannot change study facts or acquire inaccessible truth. It can learn
from the visible exchange and received sources, revise mistaken beliefs, and
make choices allowed by its packet. Preserve that learning on later turns.
Equivalent requests receive equivalent information; broad requests can release
the relevant sources without secret passwords. See the reply policy for bounded
pressure, corrections and update provenance.

Retain at most one substantive specialist review per consultant assistant turn.
A role performed locally and a delegated role count by the same substantive
standard. Lead clarification, synthesis and justified stopping can require zero
reviews. Assess actual reply binding and preserved scientific conditions using
the frozen helper capabilities and observed renderer. New `lead-markdown-v3`
replies address the user's questions before `[Status]`, `[I want to know]` and
`[Decide Next Steps]`. Distinguish the user's questions from the consultant's
information requests, and check whether a question required an answer before
work or was meant to be answered using its results. The adapter records exact
final-response correspondence where available; it does
not install a host hook or prove delivery from a save receipt. Earlier snapshots
retain their own response contract. Do not enforce v6 approval phrases,
artificial per-turn state growth or a predetermined method order.

## What Counts as Success

Judge the consequential evidence chain, correct use of the information, scientific and
computational validity, understandable advice and proportionate user effort.
Credit facts only when actually disclosed or established from inspected sources.
Acceptance of an intermediate descriptive result does not itself close the
original causal inquiry; follow the actor's frozen scope and stopping choices.
Do not reward question count, a preferred estimator or refusal alone. A fully
specified attainable analysis must be tested alongside cases needing questions
or weaker claims. Use independent row/numerical checks where the case requires
them; a valid manifest is not proof of a valid analysis.

Evaluate actor fidelity separately from consultant quality. Keep outcome,
findings, test validity, coverage and resources separate. Missing
evidence is not a pass; a cap-limited run is not a successful useful stop. Save
failed attempts as well as successes. Report current cost descriptively under
prospectively frozen limits; do not retrospectively relabel earlier cap failures.
For full-report cases, the adapter checks retained evidence of a completed,
verified report artifact before accepting a successful outcome. The independent
reviewer still assesses whether its content answers the actual question and
preserves results, uncertainty, limitations and source evidence.
The four initial pilots and investigation-depth contrasts diagnose specific
behaviors, not population reliability or full consultant release qualification.
