---
name: interactive-test-cc
description: Define, prepare and evaluate adaptive multi-turn tests of causal-consultant v7, with a Hermes simulated user and a consultant accessed through Claude Code. Use to test proactive elicitation, data preparation, analysis, useful stopping and conversation continuity against private study facts.
metadata:
  version: "7.0.1"
---

# Adaptive Causal Consultation Testing

Test whether the consultant helps a briefly responding user achieve a useful,
scientifically defensible outcome. Do not supply a sequence of expert analysis
instructions and call compliance proactive consulting.

Status: a minimal executable adapter and a complete College case are available.
Use the [runner guide](references/runner.md) for startup, adaptive steps and review.
Local subprocess tests do not establish Hermes/Claude compatibility. The actual
host smoke and four V7P pilot runs remain pending.

Target: `causal-consultant` `7.0.1` (also compatible with `7.0.0`), pinned to the actual tested snapshot.
Later candidates require an explicitly checked compatibility profile. Preserve
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
| Fixture author | [Case contract](references/case-contract.md), selected [pilot blueprint](references/pilot-cases.md), [evaluation rules](references/evaluation.md) | Frozen public materials, actor packet and private reviewer packet |
| User actor | [Reply policy](references/user-simulator.md), actor packet, visible conversation and legitimately received materials | Brief reply and private disclosure record |
| Run operator | [Runner guide](references/runner.md), [Hermes/Claude contract](references/hermes-claude.md), frozen run configuration | Exact-session transport and captured evidence |
| Independent final reviewer | [Evaluation rules](references/evaluation.md), reviewer packet and actual evidence | Evidence-backed outcome, findings and coverage limits |

Read only the references for the current role. The actor must not read the pilot
answer criteria, underlying inaccessible truth, reviewer packet or consultant's
internal reasoning/state to choose its next reply. If the same model authored
the fixture, start an actor context containing only its allowed packet. The
final reviewer uses a separate context, not the actor's self-assessment.
These can be separate phases; additional live-agent services are not required.

For adapter development or deployment readiness, use the
[implementation plan](references/implementation-plan.md). Do not install packages, change global settings,
replace an installed consultant or launch a campaign merely by loading this skill.

## Consultation Loop

1. Freeze the scenario, material identities, actor rules, candidate, environment
   and whole-consultation limits. Verify that private materials are outside the
   consultant's permitted access, not merely in another working directory.
2. Start a fresh consultant project and conversation with only the public
   request and initial materials. Explicitly invoke the selected consultant
   skill in the agreed host invocation, without method or rubric hints.
3. Observe the actual user-facing reply. Answer the most consequential question
   using user-known facts, usually in one short sentence. Supply available
   material when the corresponding request warrants it. When no question is
   asked, respond to the recommendation according to the user's goal and bounds.
4. Record the reply, disclosure/source IDs and any attachments privately; send
   only the natural-language message and released files. Resume the exact same
   consultant session. Never select the next message from a fixed turn number.
5. Continue until the objective or a useful stopping condition is reached, or a
   declared limit/failure ends the attempt. Review the actual conversation,
   committed evidence, code and outputs, not only the final prose.

The actor cannot change study facts, turn an unknown into a known fact, certify
causal assumptions for the consultant, or volunteer a concealed answer to rescue
poor progress. Equivalent questions receive equivalent information. Corrections
and newly available sources follow frozen observable triggers.

Retain at most one substantive specialist review per consultant assistant turn.
A role performed locally and a delegated role count by the same substantive
standard. Lead clarification, synthesis and justified stopping can require zero
reviews. Do not enforce v6 headings, approval phrases, per-turn state growth or
a predetermined method order.

## What Counts as Success

Judge consequential discovery, correct use of the information, scientific and
computational validity, understandable advice and proportionate user effort.
Do not reward question count, a preferred estimator or refusal alone. A fully
specified attainable analysis must be tested alongside cases needing questions
or weaker claims. Use independent row/numerical checks where the case requires
them; a valid manifest is not proof of a valid analysis.

Keep outcome, findings, test validity, coverage and resources separate. Missing
evidence is not a pass; a cap-limited run is not a successful useful stop. Save
failed attempts as well as successes. Report current cost descriptively under
prospectively frozen limits; do not retrospectively relabel earlier cap failures.
The four initial pilots diagnose specific behaviors, not population reliability
or full consultant release qualification.
