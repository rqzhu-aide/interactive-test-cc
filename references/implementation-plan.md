# Implementation Plan for the V7 Testing Skill

- Class: implementation record
- Status: consultation-loop testing and evidence corrections implemented and locally verified; live qualification pending
- Date: 2026-09-11
- Package: `interactive-test-cc`, `7.0.8`
- Current consultant target: an identified `7.0.8` snapshot

## Active testing contract

Four reusable problems combine with four independent personas, producing 16
possible pairings. The problems are study design, observational DiD/ATE,
CATE/individualized treatment rules, and data quality/causal suitability. Their
5/10/15/8 target lengths describe expectations for review; they never pace actor
replies, force completion, establish minimum rounds or replace operational caps.

The actor is an ordinary user with limited attention, knowledge and access.
Provide relevant information in response to the actual discussion. A broad
request is not a reason to dump all hidden facts or all available files at once.
The novice, domain expert, statistician and bounded adversarial persona differ
in language, priorities and cooperation while retaining the same problem facts.
Learning, earlier disclosures and unanswered questions survive session resume.

Each composition freezes distinct public materials, actor knowledge, a private
world dossier, reviewer criteria and independent numerical references. The
actor never sees world truth, oracle answers or target turns. The consultant
receives only public messages and legitimately released sources. See
[case-contract.md](case-contract.md), [user-simulator.md](user-simulator.md) and
[problem-persona-matrix.md](problem-persona-matrix.md).

The 15 old frozen cases, their four dedicated generators, four dedicated test
modules and two old catalog/pilot guides have been removed. The current package
has no alternate legacy case catalog. Git history and retained run packages
preserve earlier cases and results with their original labels. The generic
runner still understands its explicit older observation profiles and focused
endpoint contract for interpreting compatible external run inputs.

## Consultation loop and evidence

An initial request for a report expresses the user's objective, without granting
standing permission for every analysis or report. The actor responds to actual
scope offers, findings and next-step menus. It can ask for explanations, choose
further work, pause, reopen or choose a final report when that option is offered.
The operator must not manufacture consent or extra turns to complete a schedule.

The read-only `consultation_observer.py` reconstructs first protected starts
from per-reply journals and plans. It matches a scope's substantive terms to an
actual earlier public response, retains later actual user text for semantic
review, and checks that report findings were discussed. It tracks early report
artifacts even when a plan or manifest is registered later. Later consent does
not erase a prior breach. Saved approval and delivery records alone do not prove
the real conversation followed the protocol.

Current proposal inputs bind source hashes before the user chooses. The observer
checks scope/plan consistency, updated evidence and governing assumptions,
withdrawals, superseded offers and captured findings. Missing or damaged
captures stay unobserved and cannot erase earlier retained failures. The
observer never writes consultant records or repairs the conversation.

Assessment keeps protocol, saved report completion, scientific validity,
actor fidelity and execution validity distinct. An actual material consultant
breach can fail even in a diagnostic run. Structural success still needs human
or independent model review of the whole reply, scientific claims and artifacts.
A user pause is respected while an undelivered report remains incomplete.

## Retained implementation

| Component | Responsibility |
|---|---|
| `scripts/generate_problem_bank.py` | Reproduce four scientific problem definitions and their source identities |
| `scripts/compose_case.py` | Bind any problem/persona pair into a private, hashed run input |
| `scripts/problem_oracle_template.py` | Supply independent source and numerical self-checks |
| `scripts/session_driver.py` | Freeze inputs, stage permitted sources, preserve exact resume and actor history, capture evidence and derive outcomes |
| `scripts/claude_transport.py` | Capture actual subprocess output, identity, failures and available usage |
| `scripts/consultation_observer.py` | Reconstruct consultation chronology from independent public and filesystem captures |
| `tests/test_modular_cases.py` | Check all 16 compositions, identity, source invariance and actor contracts |
| `tests/test_consultation_loop.py` | Exercise loops, pause/reopening, deceptive records and early protected work |
| `tests/test_session_driver.py` | Exercise staging, transport integration, disclosure continuity, real helper artifacts and independent assessment |
| `tests/test_claude_transport.py` | Check exact session identity and transport failure handling |

Session-driver tests compose the existing observational problem with the domain
expert persona. Focused-endpoint checks change only a temporary test manifest's
contract. No fifth scientific problem or copied legacy dataset is retained.
The fake Claude process and current-policy helper are explicitly test-only;
they do not represent live consulting behavior.

## Version 7.0.7 validation and remaining qualification

Problem/case definitions are `1.0.2`; persona definitions are `1.0.1`. All
scientific public sources, numerical oracles and checkers remain byte-identical
to the prior commit. The public `available-records.md` wording changes to
describe progressive access. World scientific facts remain unchanged.

Two fresh actor contexts produced three replies to supplied consultant messages.
The novice released the rollout record first, then the dictionary after an
explanation, retaining its learning and pending questions without repeating the
attachment. The domain expert gave a relevant known fact and released only the
rollout record. Neither dumped the complete available dossier after a broad
request. These are limited actor-policy rehearsals, not live consultations,
evidence of scientific adequacy or measured report-completion lengths. Their
records are retained with the local test results.

The catalog-simplification validation passed all **88 tests in 163.991 seconds**, using the
existing shared Python and Node runtimes. The suite contains 22 modular checks,
21 consultation chronology checks, 42 session-driver integration checks and
three transport checks. It validates all 16 compositions, deterministic
regeneration, numerical/source invariance, manifest identities, retained loop
regressions and actor resume/privacy. The migrated driver module also passed
separately, 42 tests in 149.600 seconds. Skill validation and `git diff --check`
passed; the active Markdown links resolve. The previous 112-test snapshot
included 26 tests for removed cases; the current suite adds two regressions for
disclosure policy and actor continuity.

The final release review additionally found that review-based findings needed
their source and assumption dependencies preserved, and that a closed consultant
turn must stop further protected output until later user steering. Consultant
regressions cover both fixes, including historical-review reconciliation. The
tester independently follows raw review dependencies and checks stale discussion
and missing assumption bindings. Final release validation passed **90 tests in
106.965 seconds**: 22 modular, 23 chronology, 42 driver and three transport tests.
The consultant's final suite passed all **244 tests**. Both skill validators and
the consultant distribution validator passed. These results include the release
review fixes and supersede the earlier 88-test snapshot for this release.

Before making a live reliability or round-count claim, use the actual target
host, demonstrate runtime loading, exact resume, tools and private isolation,
then run the selected pairs with independent review and prospectively frozen
limits. Diagnostic mode cannot qualify a blinded comparison. A local test pass
is evidence about the adapter, not about real user behavior or scientific
performance. See [runner.md](runner.md) and [evaluation.md](evaluation.md).

## Version 7.0.8 tester correction, September 11, 2026

The CATE novice review exposed premature held-out source release, false stale
permission and report-timing flags, review prose written before final checks,
and missing raw captures in the exported package. This revision adds
source-specific commitment receipts, retained actor inputs and current-choice
records, final observation snapshots with explicit reviewer dispositions, and
verified complete or explicitly partial package export. The observer uses typed
record identities, separates reply correspondence from consent evidence, and
retains missing turns. The 7.0.8 consultant profile requires captured-delivery
and proposal-preflight capabilities without writing consultant receipts on its
behalf. Earlier compatible profiles preserve their own capability requirements.

The four problems and four personas remain independently selectable. Scientific
data, public source bytes and numerical oracles are unchanged. The generator
identity and world-file hashes were refreshed for the added source metadata.
Both skill versions are aligned at 7.0.8. Historical fixture identities and
earlier frozen attempts retain their original version records.

Correction validation ran 136 tests in 140.519 seconds: 135 passed and one filesystem
symlink-creation test was skipped because the host did not grant that permission.
ZIP link and traversal rejection checks passed. The suite covers all 16
compositions, 34 chronology checks, source prerequisites, actor continuity,
review ordering and complete package export against the updated consultant.
A fresh integration test refused an early held-out release without dispatch,
accepted it after a prior saved/public commitment, finalized its diagnostic
assessment, and exported and checked its complete evidence package.

The final 7.0.8 release suite ran 137 tests in 140.512 seconds: 136 passed
and the same OS symlink-creation test was skipped. The added regression verifies
each required 7.0.8 capability while preserving the earlier 7.0.7 profile.
Skill validation, active Markdown links and the whitespace check also passed.

A read-only diagnostic replay of the earlier nine-turn CATE archive removed
the false stale-permission and premature-report findings while retaining missing
capture and reply-correspondence coverage limits. This does not repair that
archive or qualify its science. Actual host isolation, actor invocation evidence
and a live full-report consultation remain separate qualification work.
