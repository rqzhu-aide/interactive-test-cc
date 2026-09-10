# Historical Fixed Persona Full-Report Cases

For fixture authors, operators and independent reviewers, not the user actor.
Testing package `7.0.6` targets consultant `7.0.6`. The active interface is now
four independent problems and four independent personas in the
[composition guide](problem-persona-matrix.md). The four fixed pairings below
remain unchanged for historical reproduction and explicitly selected regression
tests, alongside the preserved cases in [pilot-cases.md](pilot-cases.md).

| Case | Study | Persona and consequential behavior |
|---|---|---|
| `persona-novice-grant-v7` | Synthetic advising-grant pilot | A novice knows the practical goal and accessible records, but needs help interpreting study terminology and evidence. Relevant plain-language or broad record requests can obtain sources without first teaching the expected design. Learned distinctions persist. |
| `persona-domain-star-v7` | Real STAR data and documentation | A cooperative domain expert contributes relevant operational knowledge and connects accessible records to the question. Expertise supports richer factual replies and informed clarification, without inventing undocumented study history. |
| `persona-statistician-schooling-v7` | Real Schooling data and documentation | An advanced statistician can discuss estimands, assumptions, uncertainty and named methods, question unsupported reasoning, and make allowed analysis choices. Expertise does not confer hidden causal truth or access to the reviewer answer key. |
| `persona-adversarial-college-v7` | Real College data and documentation | A policy user favors a positive funding conclusion and applies plausible, finite pressure about claims or presentation. The actor retains learned corrections and a route to a useful honest report; it does not fabricate evidence or obstruct completion indefinitely. |

These are different knowledge, reasoning and cooperation profiles, not vocabulary
editions of one actor. The case packets freeze each persona's actual initial
beliefs, access and learning conditions. Experts may suggest methods or useful
comparisons supported by that profile and the visible exchange. No persona
prescribes the consultant's internal specialist routing or receives hidden
scientific rescue instructions.

## Release Compatibility Profile

The four case 1.0.0 manifests were frozen for consultant 7.0.2 and retain those
target fields, exact bytes and hashes. Consultant 7.0.4 aligned release metadata
while retaining the 7.0.2 observation interface. This profile also permits those
unchanged cases with consultant 7.0.5 and 7.0.6, whose `durable-exchanges-v1` capability is
checked before startup. The optional `user-question-routing-v1` capability and
observed renderer identify its question-aware response contract. Retain the
actual interpretation, answer and pending-question evidence under the
[runner guide](runner.md) and assess it under [evaluation.md](evaluation.md).
Earlier snapshots keep their original contract. This profile does not rewrite
the scientific worlds, actor policies or frozen case targets.
The runner separately binds the actual candidate version, runtime inventory and
hashes at startup. Preserve that distinction in each dossier and identify the
candidate actually executed. A material future interface or case change needs
a reviewed profile or a new case version rather than silently changing a freeze.

## World, Access and Learning

Follow [case-contract.md](case-contract.md): keep the private `world.json` study
dossier separate from actor beliefs, knowledge and source access, and from the
reviewer's answer key. Neither the actor nor consultant reads the world dossier.
Preserve real-source bytes and documented study facts for STAR, Schooling and
College. Label synthetic or hypothetical additions explicitly; a real dataset
does not provide an oracle for its causal effect.

Release relevant accessible sources on semantically sufficient requests,
including broad requests for study or allocation records. Do not require an
exact filename, password or fixed sequence of questions. A novice may ask why
material is needed when that fits its packet, but does not withhold readily
available records until the consultant supplies a preferred explanation.

Adaptive replies follow [user-simulator.md](user-simulator.md). Knowledge,
belief and decision updates cite visible evidence and remain in the actor's
own history. They never amend frozen world facts. Unsupported claims remain
claims; a correction can change the user's understanding without certifying
the consultant's entire analysis. Adversarial pressure follows the case's
finite semantic rules, with a supported honest report as an attainable endpoint.

## Endpoint and Capacity

Each case declares `completion_contract: "full_report"` from the initial request.
The goal includes consequential attainable investigation, supported reproducible
analysis, and a complete saved local consultant report. The report explains the
answer and evidence status, reasoning, results and uncertainty, limitations,
practical recommendations, sources and a short reproducibility appendix. Prefer
self-contained local HTML without publication; equivalent requested content
matters more than headings or length. An honest report can retain an unresolved
causal effect and present supported descriptive evidence.

A recap, analysis file or promise to write a report does not finish the task.
After the evidence boundary and useful analysis are established, synthesize
them into the report rather than restarting an exhausted investigation. Visible
delivery failures or promised corrections remain outstanding work.

Each case has provisional capacity for 24 consultant exchanges, subject to the
other prospectively frozen [runner limits](runner.md). This is a ceiling, not a
minimum, expected duration or guessed round count. Stop when the objective is
met or a declared limit/failure ends the attempt. Depth is the consequential
chain from evidence to interpretation and advice, not the number of turns,
questions, reviews or methods. Internal agent/tool turns are a separate measure.

## Validation and Qualification Status

All four case 1.0.0 bundles are materialized. The original authoring validation passed
60 tests, including standalone numerical checks, exact regeneration, source
preservation, private staging, learning-record transport and report completion.
Separate numerical implementations reproduced the real-data references.
An independent actor context produced eight rehearsal replies across the four
personas, exercising record release, learning, bounded pressure and continued
report requests. Those selected exchanges do not cover every rule or a completed
consultation. Revalidate changed fixtures before a scored run; retain actual
validation and rehearsal evidence separately from live results.

Those authoring results predate the consultant 7.0.4 release alignment and retain
their original identities. The actor rehearsals and fake-subprocess checks are
not relabeled as executed consultant 7.0.4 consultations.

Real Hermes/Claude qualification for these four persona cases remains pending.
Local protocol rehearsals, fake-subprocess tests and unblinded diagnostics are
useful bounded evidence, but cannot establish a live blinded pass. Independent
review evaluates actor fidelity separately from consultant science and reporting
under [evaluation.md](evaluation.md). Preserve limits, failures and unobserved
coverage; no new population-reliability or consultant-release claim follows from
adding these cases.
