# Interactive Test CC v7

Version: `7.0.5`. This repository contains the v7 testing skill and minimal
adaptive runner under the canonical skill name `interactive-test-cc`.

It specifies a Hermes simulated user interacting with causal-consultant through
Claude Code. Separate world dossiers, realistic user knowledge and beliefs, and adaptive
source disclosure test whether the consultant discovers what matters and helps
the user reach a defensible outcome. Independent review checks actual evidence,
prepared data and calculations rather than rewarding a prescribed conversation.

Broad and end-to-end test requests cover all four [persona cases](references/persona-cases.md):
a novice with the synthetic grant pilot, a cooperative STAR domain expert, an
advanced Schooling statistician, and a College policy user applying bounded
pressure. Individual case selection is allowed. Personas change knowledge,
reasoning and cooperation, not just vocabulary. The simulated user
continues past analysis and conversational summaries until the promised saved
report is delivered. Finalization checks actual verified report artifacts, with
scientific quality assessed separately. Both the testing package and current
consultant target are 7.0.5. Frozen case identities and earlier evidence remain
unchanged under the [persona release profile](references/persona-cases.md).

Start with [SKILL.md](SKILL.md). The
[runner guide](references/runner.md) gives executable commands and the Hermes
handoff. The [implementation plan](references/implementation-plan.md) defines the
remaining target-host and pilot work. The
[regression pilot blueprints](references/pilot-cases.md) cover operational meaning and
preparation, ready analysis, useful limited advice and correction after resume.
The same guide specifies four synthetic investigation-depth contrasts for a
matched comparison of frozen consultant `7.0.1` and revised `7.0.2` snapshots.

## Readiness

The standard-library runner provides preflight, start, step, inspect and finish.
The complete College case includes verified CSV bytes, semantic user facts and
an independently checked numerical oracle. Preflight detects incomplete consultant
copies, including missing `package.json`, and mismatched case/data identities.
The observation profile explicitly accepts consultant `7.0.0`, `7.0.1`,
`7.0.2`, `7.0.4` and `7.0.5`; `7.0.3` and future versions remain unsupported until a
checked compatibility update.

The 7.0.5 profile verifies `durable-exchanges-v1` before startup. Each turn binds
its read-only observations to an explicitly configured project root or the
unique captured journal, including a journal directly in the work directory.
Missing or ambiguous roots remain explicit. Status and context retain turn,
exchange and memory views; an observational check compares the actual final
response with the prepared exchange hash. The profile records optional
`user-question-routing-v1` support. For `lead-markdown-v3`, capture retains the
user's question answers and pending question references separately from the
consultant's information requests. Earlier v1/v2 renderers keep their original
contract. This provides review evidence, not
host enforcement, proof of reading or a scientific pass.

Eight investigation-depth fixtures cover allocation-record availability, exposure
timing, intermediate versus closed descriptive scope, and complete versus missing
design documentation. Each has frozen public/actor/reviewer materials and an
independent self-check. The original College fixture remains unchanged; its
descriptive completion does not establish investigation depth.

Two earlier full-report adaptations cover the College study and synthetic recoverable
allocation study, preserving their original scientific materials and references.
These and the focused cases remain regression tests with their own endpoints.
No fixed four-round stop exists: some earlier short endpoints asked for a recap.
Each new persona case has provisional capacity for 24 consultant exchanges and
ends when the actual requested work is complete. There is no minimum or guessed
round count. The runner guide distinguishes capacity from observed completion.

The new persona specifications keep private world truth separate from actor
beliefs, knowledge and access, and from the reviewer's answer key. Visible
learning and corrections persist through private actor update records. Fixture
validation and protocol rehearsal do not establish live performance; the persona
guide records their status separately from real Hermes/Claude qualification.

Local subprocess tests exercise session continuity, failures, disclosure, limits
and review binding. The real Hermes/Claude smoke, four V7P pilots and matched
investigation-depth consultations remain pending.
An unverified or unblinded local diagnostic cannot become a passing blinded test.
Do not execute the old v6 runner as a v7 test.

## Repository Layout and Legacy Work

The former nested `interactive-test-cc-v7` folder has been promoted here.
Pre-v7 skill files, scripts, cases and results are preserved in the sibling local
`interactive-test-cc-v6` directory. That archive also holds older testing skills
and historical test results. The active consultant is in the sibling
`causal-consultant` repository; its pre-v7 files are in `causal-consultant-v6`.

Git history and the existing GitHub remote remain with this active repository.
The archive is a filesystem snapshot, not a separate Git repository or remote
backup. Its modified pre-v7 files will not be included in a v7 commit here.
Do not commit from the outer workspace by mistake; review each active repository
separately. No commit, push, installation or live test accompanies the move.
