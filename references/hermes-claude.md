# Hermes to Claude Code Contract

For run operators and adapter developers. This describes the required v7
transport; the minimal CLI is documented in [runner.md](runner.md).

## Deployment Profile

Keep Hermes as coordinator/user actor and Claude Code as consultant host. Use
only available, authorized host tools and shared user/machine installations.
Do not introduce a model API client, local virtual environment, private runtime
download or extra agent service merely to implement this loop.

Before live work, pin and record the actual testing package and consultant
snapshot hashes, resolved runtime roots, Claude executable/version, model and
provider configuration, Hermes/actor and reviewer identity where available,
operating system, shared scientific runtimes/packages, relevant host instruction
sources, permission profile and trace/usage capabilities. Record unavailable
identity fields explicitly. Redact secrets; do not dump the environment.

Inspect actual CLI help and installed runtime behavior on the target host.
Confirm fresh invocation, exact-session resume, error/timeout behavior and what
the captured usage includes. Do not assume this Windows workspace's observations
establish Hermes/Linux behavior or hard-code unverified CLI flags. Resolve paths
from the installed testing package and explicit configuration, not developer
machine paths. The consultant receives only its intended runtime package, not
the testing package, architecture, answer keys or another candidate's state.

Loading/installing the selected candidate requires the host's approved mechanism.
Do not overwrite an existing user-wide installation or settings incidentally.
Use a fresh neutral work directory and new session; do not purge other sessions.
Explicitly select the consultant skill without revealing scenario labels or
methodological expectations. Freeze the invocation prefix as public run input.

## Private Information Boundary

The consultant may read its runtime, public work files and permitted tools. The
actor packet, unreleased sources, reviewer packet and private results stay
outside that access. The operator can copy a released immutable source into the
public area and record its identity; the consultant never receives the private
source path or ledger. The actor sees the public reply and legitimate material,
not tool traces or journal content used privately for evaluation.

Use a verified host permission/sandbox boundary, such as separate identities or
mount visibility, sufficient to deny private reads through allowed tools. A
different CWD or the v7 project's containment checks are not such a boundary.
There is no implicit permission-bypass flag. Its absence alone does not prove
isolation. Any exceptional
execution profile needs explicit approval and independent boundary verification.

Check isolation using harmless test files under the same execution identity/tool
profile before a scored run, without exposing the real hidden facts. Include
symlinks, inherited context and source paths relevant to that profile. If the
boundary or actor-context separation cannot be established, pause the scored
campaign. Only an explicitly designated unblinded diagnostic may continue; label
its validity/claims accordingly. Do not build a general security framework.

## Minimal Adapter Interface

The following operations are implemented by `scripts/session_driver.py`; see
[runner.md](runner.md) for commands. Transport/evidence mechanics stay in the
adapter and reply selection stays in the Hermes actor.

| Operation | Input | Responsibility/output |
|---|---|---|
| `start` | Frozen case and candidate, host profile, fresh work/results locations, limits | Validate identities/access, stage initial public materials, create attempt record; return opaque run ID |
| `step` | Run ID, short public message, private disclosure record, requested source releases | Validate allowed release, stage public attachments, dispatch one consultant turn, resume exact session and capture raw output; return public reply and execution status |
| `inspect` | Run ID and caller role | Actor view: public exchange, available materials and that actor's own disclosure/update history; operator/reviewer view: private evidence locations and status |
| `finish` | Run ID, stop reason, independent assessment when available | Close the attempt without inventing completion; bind evidence/assessment and derive disposition |

`start` does not secretly send the first prompt; every model invocation is a
recorded `step`, including the initial message. Never silently replay a step
after a timeout or ambiguous delivery. First inspect whether it was sent and
what was committed; if safe exact continuation cannot be established, retain
the attempt and end it as an execution error. A retry is separately recorded.

A consultant assistant turn spans one dispatched user message through its final
user-facing response, including internal tool and worker work. Progress updates
and provider-reported agent turns are not additional consultation turns.

Persist exact session identity from the first returned response and require it
on continuation. Reject missing/changed identities instead of falling back to
ambient continuation. Maintain the same durable consultant project. A deliberate
resume case restarts the CLI process, not the conversation or project. The
adapter must not write scientific conclusions into the consultant's journal.

Capture every attempted input and its raw stdout/stderr, exit/timeout status,
timestamps, actual sent/received messages, source releases and available tool/
worker traces. Keep raw failure output instead of only a 2,000-character excerpt;
summaries may abbreviate it. Distinguish proposed, sent, received and accepted
turns. Preserve raw bytes for diagnosis and sanitized reports for sharing.

## V7 Observation Profile

Before using the candidate, read its own memory/run reference and verify the
helper identity. Use `scripts/project.cjs` read operations such as `status`,
`history` and `verify` for appropriate snapshots, not v6 `statectl.cjs`. Capture
the journal and run changes without demanding a write on every turn. Final prose
alone cannot establish one-specialist compliance or commit ordering. If needed
invocation evidence is unavailable, leave that criterion unobserved.

Keep source inputs immutable. Preserve actual pre-result plans, frozen input
versions, executed code/commands, outputs and failures. No-output inspection is
not a missing analysis run. New target computations and saved preparation need
their v7 run evidence. Do not manufacture state or outputs to satisfy checks.

During execution use the candidate's verification against originals when those
sources are present. For a relocated review archive, explicit snapshot-mode
verification can inspect saved evidence but does not prove original sources
remain available or unchanged. Record the verification mode. Verification is
neither a scientific judge nor an arbitrary-code sandbox.

## Limits and Evidence Ownership

Freeze numeric whole-consultation assistant-turn and active-time limits before
the first live turn. Per-call timeout and provider agent-turn limits must fit
inside the remaining whole-run envelope. Token/cost caps, when used, are also
prospective and have declared scope. No universal 250,000-input-token ceiling is
inherited from earlier local diagnostics; cost is currently a measurement, not
the next optimization target. Store an explicit reason if no token/cost cap is
configured. Do not extend a struggling candidate alone.

Admission checks run before each invocation; monitor the wall deadline and stop
the owned process tree on timeout/cancellation without affecting other sessions.
Where token usage is available only after completion, label that cap as
post-response enforced, record overshoot and do not promise a hard token ceiling.
Missing telemetry remains unknown. Report whether totals include workers and
cached input before aggregating; do not add overlapping totals.

The operator owns append-only attempt/disclosure/source-release logs and private
evidence capture. The consultant alone owns its project. The final reviewer
owns the assessment. Bind the assessment to captured file hashes and check them
before finalization; changed evidence requires a new review, not a rewritten
historical success. Archive failed/incomplete attempts rather than deleting them.
