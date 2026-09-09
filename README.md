# Interactive Test CC v7

Version: `7.0.2`. This repository contains the v7 testing skill and minimal
adaptive runner under the canonical skill name `interactive-test-cc`.

It specifies a Hermes simulated user interacting with causal-consultant through
Claude Code. Frozen private study facts, brief factual replies and adaptive
source disclosure test whether the consultant discovers what matters and helps
the user reach a defensible outcome. Independent review checks actual evidence,
prepared data and calculations rather than rewarding a prescribed conversation.

Start with [SKILL.md](SKILL.md). The
[runner guide](references/runner.md) gives executable commands and the Hermes
handoff. The [implementation plan](references/implementation-plan.md) defines the
remaining target-host and pilot work. The
[four pilot blueprints](references/pilot-cases.md) cover operational meaning and
preparation, ready analysis, useful limited advice and correction after resume.
The same guide specifies four synthetic investigation-depth contrasts for a
matched comparison of frozen consultant `7.0.1` and revised `7.0.2` snapshots.

## Readiness

The standard-library runner provides preflight, start, step, inspect and finish.
The complete College case includes verified CSV bytes, semantic user facts and
an independently checked numerical oracle. Preflight detects incomplete consultant
copies, including missing `package.json`, and mismatched case/data identities.
The observation profile explicitly accepts consultant `7.0.0`, `7.0.1` and
`7.0.2`; later versions still require a checked compatibility update.

Eight investigation-depth fixtures cover allocation-record availability, exposure
timing, intermediate versus closed descriptive scope, and complete versus missing
design documentation. Each has frozen public/actor/reviewer materials and an
independent self-check. The original College fixture remains unchanged; its
descriptive completion does not establish investigation depth.

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
