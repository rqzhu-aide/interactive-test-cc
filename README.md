# Interactive Test CC v7

Version: `7.0.6`. This repository contains the v7 testing skill and minimal
adaptive runner under the canonical skill name `interactive-test-cc`.

It specifies a Hermes simulated user interacting with causal-consultant through
Claude Code. Separate world dossiers, realistic user knowledge and beliefs, and adaptive
source disclosure test whether the consultant discovers what matters and helps
the user reach a defensible outcome. Independent review checks actual evidence,
prepared data and calculations rather than rewarding a prescribed conversation.

The active interface is **four problems and four independent personas**, freely
combined into 16 possible tests. Choose a problem and user type; each combination
requires the appropriate saved report. See the
[catalog and programmer guide](references/problem-persona-matrix.md).

| Problem | Target replies |
|---|---:|
| `study-design` | 5 |
| `observational-did` | 10 |
| `cate-policy` | 15 |
| `data-quality-edge` | 8 |

Persona selectors are `novice`, `domain-expert`, `statistician` and `adversarial`.
They change understanding, reasoning, learning and natural disclosure. They do
not change scientific truth or source access. Target lengths are descriptive,
not deadlines, quotas or stopping rules, and stay out of actor instructions.
The user may need fewer or more exchanges. Do not rush completion or manufacture
extra conversation to meet a target.

```sh
python scripts/compose_case.py --list
python scripts/compose_case.py --problem cate-policy --persona novice --output /private/cases/run001
```

Pass the generated directory as the existing runner's `--case`; composition does
not launch a consultation. This release aligns both skills at version 7.0.6.
Earlier case identities and evidence
remain unchanged in the [historical persona guide](references/persona-cases.md).

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
`7.0.2`, `7.0.4`, `7.0.5` and `7.0.6`; `7.0.3` and future versions remain unsupported until a
checked compatibility update.

The 7.0.5 and 7.0.6 profiles verify `durable-exchanges-v1` before startup. Each turn binds
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

Eight historical investigation-depth fixtures cover allocation-record availability, exposure
timing, intermediate versus closed descriptive scope, and complete versus missing
design documentation. Each has frozen public/actor/reviewer materials and an
independent self-check. The original College fixture remains unchanged; its
descriptive completion does not establish investigation depth.

Two historical full-report adaptations cover the College study and synthetic recoverable
allocation study, preserving their original scientific materials and references.
These and the focused cases remain regression tests with their own endpoints.
No fixed four-round stop exists: some earlier short endpoints asked for a recap.
The old fixed persona cases retain their recorded capacity. New compositions
use separately configurable operational caps and finish when the actual report
objective is met. The runner guide distinguishes caps, descriptive targets and
observed completion.

The new persona specifications keep private world truth separate from actor
beliefs, knowledge and access, and from the reviewer's answer key. Visible
learning and corrections persist through private actor update records. Fixture
validation and protocol rehearsal do not establish live performance; the persona
guide records their status separately from real Hermes/Claude qualification.

All 87 local automated tests passed, including all 16 compositions, numerical
fixture checks, session continuity, failures, disclosure, limits and review
binding. Two isolated actor rehearsals used supplied consultant messages; they
do not establish live consultant behavior or typical conversation lengths.
The real Hermes/Claude smoke, four V7P pilots and matched
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
separately. The historical layout move did not install either skill or qualify
live behavior.
