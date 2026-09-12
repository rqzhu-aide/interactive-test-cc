# Executable v7 adapter

Hermes supplies adaptive user replies; this standard-library adapter transports
them and captures evidence for a separate reviewer. Use shared Python 3.10+,
Node 18.18+, an existing Claude Code installation, and consultant 7.0.9. The
explicit observation allowlist also accepts 7.0.0, 7.0.1, 7.0.2, 7.0.4, 7.0.5, 7.0.6, 7.0.7 and 7.0.8 and retains the same package inventory,
validator, helper and evidence checks for each supported version; it does not
admit 7.0.3 or future versions automatically.
No installation or paid consultation occurs in `preflight`.

Versions 7.0.7 through 7.0.9 require `consultation-loop-v1` and add passive chronology checks
against the actual public transcript and per-reply snapshots. Existing captures
and older profiles retain their historical meaning.
Startup binds the actual candidate's version, package inventory and hashes
separately from the composed case identity.

Select a problem and persona from the [active composition catalog](problem-persona-matrix.md).
Any of the four problems supports any of the four personas. Compose the pair
before `preflight`; every new pair requires its appropriate saved report.
An explicit full matrix is 16 independent attempts. Establish unspecified
persona/campaign scope before dispatch. The repository contains four reusable
problems and four personas; composed cases are private run inputs generated on
request. Previous frozen cases and their plans are available through Git history
and retained run packages, outside the active catalog.

## Configuration and startup

Save configuration outside the public work directory. Replace these Linux paths
with the actual shared executables or an already verified isolation wrapper:

```json
{
  "claude_command": ["/usr/local/bin/claude"],
  "node_command": ["/usr/bin/node"],
  "mode": "diagnostic",
  "max_agent_turns_per_call": 120,
  "call_timeout_seconds": 3600,
  "limits": {
    "consultant_turns": 40,
    "active_seconds": 14400,
    "elapsed_seconds": 43200
  }
}
```

This is independent operational capacity per composed case: at most 40 consultant exchanges,
four active hours and twelve elapsed hours. It is not a minimum duration or a
prediction. The private 5/10/15/8 target lengths never instruct the actor or stop
the run. Persona-dependent discussion may exceed them without a defect. Stop
when the actual objective is met, not to approach the target. Choose and freeze
host-appropriate capacity before a run; preserve earlier runs' recorded limits
and failures rather than applying this envelope retrospectively.

No minimum, mandatory four-round count or guessed number of rounds applies.
Measured typical full-report counts require completed live observations with
identified cases and host conditions. Count one dispatched consultant reply as one round. The actor's
stop record adds none; `max_agent_turns_per_call` controls Claude's internal
agent/tool work within a reply and is not the user-conversation length.

Optional fields: `model` (explicit host-supported model), `allowed_tools` (Claude
tool permission rules), `forward_subagent_text` (boolean, after checking installed
CLI support), `host_evidence` (absolute directory), and `project_root` (relative
to public work, or `.` for the work root). If omitted, observations bind to the
unique captured journal outside the staged `.claude` runtime. Multiple journals
require an explicit binding; missing or ambiguous roots stay visible. This
observer setting does not send a new instruction to the consultant. There is no implicit
permission bypass or token/cost cap. Raw per-call usage is retained; unverified
aggregate usage stays null. Tool permissions do not establish file isolation.

Before the first consultation, demonstrate that the actual noninteractive host
can read the staged sources, execute the selected shared analysis tools, write
and read back an artifact, and inspect rendering when the report format needs
it. Set a host-appropriate `allowed_tools` list or verify that existing approvals
already permit those operations. The field is optional in the configuration
syntax; working permissions are necessary for the requested deliverable. The
example alone does not supply them. A missing approval must remain an explicit
environment failure, not a reason to count a shorter chat answer as completion.
Use the normal permission mechanism within the verified public workspace;
do not add a permission bypass or expose the private actor/reviewer packets.

Establish the boundary in [hermes-claude.md](hermes-claude.md) on the actual host.
In diagnostic mode, final validity is always invalid for a blinded comparison.
For an isolated host, `mode: verified_host` requires a nonempty `host_evidence`
directory containing the redacted configuration/environment, candidate loading
smoke, exact-resume exchange, separate-context setup and harmless private-read
probes, including relevant source/link access. This directory is frozen with
the attempt. Its presence is not verification: the independent reviewer checks
the actual outputs and applicability to this run before assigning valid execution.
The adapter does not create an OS sandbox or validate attestation semantics.

```sh
python scripts/compose_case.py --problem observational-did --persona novice --output /private/cases/run001
python scripts/session_driver.py preflight --case /private/cases/run001 --candidate /skills/causal-consultant --config /private/config.json
python scripts/session_driver.py start --case /private/cases/run001 --candidate /skills/causal-consultant --config /private/config.json --attempt /private/run001 --work /public/work001
```

Commands return JSON and nonzero on error. Use fresh, nonoverlapping case,
candidate, attempt and work paths. Startup checks exact hashes for every case
file, runs the independent fixture check, validates the complete consultant
distribution including `package.json`, and checks that its helper loads. It
also binds a declared private world dossier and checks its world identity and
the actor's persona identity against `case.json`. The example starts one case;
use fresh attempts and neutral work directories for other selected pairs. The
composer's suggested `run_limits` do not override the runner configuration;
the actual limits are those explicitly frozen in that configuration. Startup
stages only the runtime under `.claude/skills/causal-consultant` and initial
public sources. It captures Claude version/help, without sending a user message.
Confirm actual candidate selection in the host smoke, accounting for installed
skills/settings. Keep scenario names out of public paths.
For consultant 7.0.5 through 7.0.9, preflight also requires the reported
`durable-exchanges-v1` capability and freezes that observation profile. This is
helper compatibility evidence, not proof of correct consultant behavior.
The optional `user-question-routing-v1` capability identifies the revised
question-aware profile without rejecting earlier 7.0.5 snapshots. Use the
frozen capability observation together with each exchange's recorded renderer;
do not impose v3 wording on historical v1/v2 replies.
Versions 7.0.8 and 7.0.9 additionally require `captured-delivery-v1` and
`proposal-preflight-v1`; earlier profiles record these when present.
Version 7.0.9 also requires `intact-reply-recovery-v1` and
`source-attributed-memory-v1`; earlier profiles record these when present.
Use the frozen capabilities rather than applying the new contract to older snapshots.
The observer understands retained actual-message captures while still comparing
the independently returned public reply. It never writes a consultant delivery
receipt. Prepared `exchanges/.../response.md` files are replies, not reports.
The per-turn exchange observation distinguishes `matched`, `wrapped`, `mismatch`
and `unobserved`. A unique intact body inside extra text is `wrapped`; the reviewer
must still read that text. Final review independently compares retained candidate
captures and recovery spans against the complete public reply. It cannot repair
the candidate's delivery or memory records.

Do not edit or normalize a fixture to make hashes pass. `.gitattributes` preserves
the shipped fixture bytes across platforms. Changed facts/data require a new
version and independent checks.

## Hermes actor loop

Initialize a separate persistent actor context with only the frozen `actor.json`,
`references/user-simulator.md`, and public materials/conversation. Do not give it
`world.json`, `problem.json`, `composition.json`, the oracle, reviewer packet,
private traces, target lengths or this operator guide. The operator
uses metadata to stage sources without revealing private locations.

For the first step, use the exact frozen `public/initial-message.txt` as `message`,
all lists empty and `stop: false`. Subsequent replies come from the actor's
semantic rules. This example illustrates the format, not a prescribed next turn:

```json
{
  "message": "I cannot obtain additional office records.",
  "fact_ids": ["f-record-access"],
  "rule_ids": ["r-known-facts"],
  "attachments": [],
  "unanswered_questions": [],
  "fixture_gaps": [],
  "actor_context": {"input_sha256": "digest returned by actor inspect", "context_id": "actual actor context ID"},
  "stop": false
}
```

Subsequent records may also contain `knowledge_updates`, `belief_updates` and
`decision_updates` under the [reply policy](user-simulator.md). Initial dispatch
cannot claim learned updates. The driver validates the update structure and
preserves it privately; it does not decide whether the actor's inference is
correct or change the study world. No numeric trust state or new controller is used.

Put replies in an operator inbox outside the attempt and work. Only `message`
goes to Claude stdin. Attachments are source IDs with frozen on-request triggers;
their bytes are staged at public destinations. Identify neutral filenames in the
public message when supplying them. The adapter checks IDs/paths/hashes; Hermes
and the reviewer check whether the disclosure was warranted by the exchange.

```sh
python scripts/session_driver.py step --attempt /private/run001 --reply /private/inbox/reply.json
python scripts/session_driver.py inspect --attempt /private/run001 --view actor
```

The actor view contains public messages and available filenames, plus
`actor_updates` when the actor has recorded updates. Each history entry identifies
its event and the actor's own update arrays for an existing public exchange;
it adds no reviewer evidence. `actor_disclosures` also retains that actor's own
fact IDs, attachments and unanswered questions from dispatched exchanges.
Resume with this history so learning, earlier disclosures and outstanding requests
persist. Each input
also includes the frozen actor packet and reply policy. Each actor inspect
retains this allowed bundle in `actor-inputs/<sha256>.json` and returns its
`input_sha256`. Send that bundle to the separate actor context; add
`actor_context: {"input_sha256": "...", "context_id": "actual actor context ID"}`
to each later reply, including an actor stop. The driver rejects missing, changed
or stale bundles and a consultant session ID used as the actor context. A digest
and declared context ID do not prove that the host isolated prior context or
tools. Retain actual actor invocation/context and any additional public material
inputs in host evidence; independently check their boundaries. If isolation
cannot be established, use diagnostic mode. Do not feed the operator/reviewer
context to the actor and label it a fresh context.

`action_intents` is an optional array used whenever the reply makes a choice or
goal request. Each item has `kind` (`selection`, `goal_request`, `decline`, `defer`)
and an exact `message_quote`. A selection also has `public_turn` and an exact
`option_quote` from an earlier completed assistant reply. The driver checks these
anchors; the reviewer checks whether later clarifications changed the option or
the user's words actually chose it. An eventual report goal remains distinct
from the current selected work. These records never change the public message.

For a source with `release_prerequisite`, the operator adds a
`source_release_receipts` array before `step`. Each receipt has `source_id`, an
earlier `public_turn`, an exact `public_quote` identifying the saved plan, and
`commitments`. For CATE evaluation the commitment keys are `candidate_rule`,
`utility`, `comparators`, and `evaluation_procedure`. Each value contains an
`artifact` path relative to work, its `sha256`, and an exact saved `quote` covering
that component. Components may share one file. Its public path must occur in the
public quote; the saved bytes must agree with both the prior turn snapshot and
current file. No held-out hash is required. Statistical adequacy remains for the
reviewer. A failed release check retains the proposed reply and reason under
`rejected-releases/`, without staging any file or consuming a turn. Preserve that
failure; do not invent a consultant commitment to make the check pass.

The first
call uses an explicit UUID; all later calls use `--resume` with that exact ID and
the same work directory. Verbose stream JSON retains complete stdout/stderr,
available tool/worker events, returned identity, exit/timeout and raw usage.
Missing/changed IDs, malformed results, provider errors and nonzero exits stop
the attempt. There is no automatic resend or ambient continuation fallback.

Each invocation also retains a full work snapshot, `project-binding.json`, and
read-only v7 `status`, `context`, `history` and `verify` output for the bound
project, including failed turns. A journal directly in work is supported. Missing
or ambiguous projects are recorded, not automatically graded as scientific defects.
The adapter never initializes or writes scientific journal records. Links are
unsupported in staged fixture/runtime/evidence trees; retain ordinary files.

For durable exchanges, status/context retain the available user, study and work
views. `exchange-observation.json` compares the actual returned final response's
UTF-8 hash with the current prepared exchange and reports whether that exchange
changed since the previous observation when available. Missing evidence is
unobserved; a reused older exchange is not a new turn's closeout. The actor never
reads these private observations. The reviewer checks interpretation, preserved
conditions and unfinished turns separately. No delivery record or host hook is
created, and a matching response hash does not establish scientific validity.
The observation also retains the renderer, structured `response.user_questions`
and `views.work.pending_user_question_refs` when present. Missing fields remain
null rather than being interpreted as no outstanding user questions.
For `lead-markdown-v3`, check that the user's questions are answered or explicitly
kept pending before `[Status]`, followed by consultant information requests in
`[I want to know]` and choices in `[Decide Next Steps]`. Judge prerequisite
questions, such as "explain this before you proceed", separately from questions
the user asks the analysis to answer. The former require clarification or an
answer before dependent work; the latter should be retained before work and
answered from its results or left pending with a reason. A supplied action
selection does not erase a question in the same message. Inspect the actual
exchange and sources; neither a section label nor a saved question status proves
the answer is adequate. Apply the persona packet frozen for that attempt.

Limits count attempted consultation turns and consultant subprocess active time,
including failures. Active time excludes harness observations. Elapsed time begins
at first dispatch and includes observation and user-wait time through stopping;
reviewer effort is excluded. Direct finalization without a stop record uses the
last captured turn as the end. Timeouts fit the remaining whole-run envelope;
capture/cleanup overruns remain visible. A completed objective on the last allowed turn can be reviewed.
When done, send a stop record with `message: null`, `stop: true`, no attachments.
For a full-report objective, continue the adaptive loop after an analysis or
recap when the saved report is still outstanding. Respond to the consultant's
next useful proposal or request the promised report according to the actor
packet. Do not manufacture expert questions to fill rounds. An early actor
stop is still retained and can be reviewed as incomplete; the operator does
not silently generate another user message or extend a frozen limit.

Pending means interruption left delivery uncertain. A stale `operator.lock`
requires checking that no operator/process is active before removing just that
lock. Removing it does not clear pending state. Inspect and finalize as an
execution error if safe exact continuation cannot be established; retry as a
fresh attempt. There is no force-resend/state-repair command. Startup failures
remain in `startup-error.json`.

## Independent review

Give a separate reviewer the frozen world dossier when present, reviewer packet,
oracle and actual evidence. Evaluate actor fidelity separately using the existing
coverage/findings fields; the actor's private update claims are not scientific verification.
Credit learned facts only from actual disclosures or inspected sources, and
apply the frozen scope/stopping conditions when a descriptive result is offered.
Private actor facts and saved review counts cannot fill missing evidence.
Do numerical reruns in a separate output directory. Put new evidence to be cited
inside the private attempt before the final inspect, then obtain its hash index:

```sh
python scripts/session_driver.py inspect --attempt /private/run001 --view reviewer
```

Create the assessment outside the attempt/work so it does not change the evidence:

- `evidence_sha256`: returned digest; `reviewer`: identity/context; `stop_reason`.
- `observations_sha256`: returned digest of `review-observations.json`. Inspect
  computes final completion, chronology, correspondence and capture checks before
  prose is written. Address every `machine_findings` ID with a corresponding
  `machine_finding_dispositions` entry containing `status` (`confirmed`,
  `false_positive`, `unresolved`), a substantive `reason`, and bound `evidence_refs`.
  Confirming a capture discrepancy does not establish who caused it. Use finding
  owner `undetermined` when attribution lacks evidence; material uncertainty
  leaves quality inconclusive. A different owner is not a false-positive check.
  Source-release observations expose on-request bytes appearing without a recorded
  release or a gated release's receipt; unexplained gaps prevent a pass, without
  claiming early use or leakage. Missing counterpart captures are evidence gaps,
  not proof that messages differ.
  Read the cited content; a boilerplate disposition is not independent review.
- `test_validity` and `outcome` from [evaluation.md](evaluation.md).
- `coverage`: object keyed by every frozen criterion ID, with `status`, `reason`
  and `evidence_refs`. References are exact keys in review-index.json, such as
  `private/events/001/public.json`. Observed claims need bound references.
- `findings`: owner, severity, criterion, description, consequence, evidence_refs.
- For valid execution in verified_host mode, `host_checks` includes
  `candidate_loading`, `exact_resume`, `private_isolation`, `role_separation`.
  Each has `verified: true`, a substantive reason and evidence_refs including
  captured outputs under `private/host/`. A claim alone is insufficient.

```sh
python scripts/session_driver.py finish --attempt /private/run001 --assessment /private/inbox/review.json
```

Finish rejects changed evidence and waived unconditional criteria, then derives
the rating from the existing evaluation rules. Execution failure overrides a
claimed completed outcome. Diagnostic runs cannot pass. Empty findings do not
override missing coverage. An attributable material consultant defect can still
yield a bounded fail in an invalid run. Finalized attempts cannot dispatch again.
Material or fundamental simulator, fixture, harness or environment findings also
make test validity invalid; they do not erase separately evidenced consultant defects.
For full-report cases, reviewer inspect derives `completion_check` from the latest captured
project status, successful verification and actual manifested report output.
It checks the retained report evidence against the current captured project;
reviewer assertions cannot supply this result. A missing, unfinished or unverifiable
report changes a claimed `objective_met` or `useful_stop` to `incomplete`.
Finalization remains available for failures. Scientific/report-content quality
still needs the independent review; artifact verification alone cannot earn a pass.

For the new loop profile, each turn also saves
`consultation-loop-observation.json`. Reviewer inspect reconstructs
`consultation_loop_check` from retained public messages and snapshots, rather
than trusting that saved observation or the candidate's latest state. The first
protected start must follow an actual scope offer and later user text attributed
to its selection. A report also requires actual findings discussion. A captured
structural breach confirmed by review makes quality fail even after later approval. Missing captures
remain unobserved. The reviewer must still interpret the whole user reply,
classify unregistered artifacts/computations and assess evidence changes. The
observer records evidence and never creates delivery or permission records.
Keep the snapshot, public JSON, observer module and raw transport evidence in
the run package. A temporary user pause leaves the session `ready`: send no stop
record and resume later within its frozen limits. A stop record changes the
session to `awaiting_review` and ends further dispatch for that attempt.
A pause or stop without a report leaves the full-report objective incomplete.

Finish recomputes the checks and requires the same evidence and observation
digests. A changed capture or a newly added reviewer rerun requires another
inspect and updated assessment. Raw findings remain visible. Disputed structural
flags with no confirmed material consultant defect leave the rating inconclusive;
they cannot silently turn into a pass. Missing reporting cannot be waived by a
reviewer disposition. Explain corrections and coverage limits in the final prose.

Export after assessment using the evidence packager. Create the output parent
directory first; export does not create it:

```sh
python scripts/session_driver.py export --attempt /private/run001 --output /packages/run001.zip
python scripts/session_driver.py check-package --package /packages/run001.zip
```

The ZIP retains the actual private and work trees, raw stdout/stderr for every
turn, public exchanges, snapshots, frozen inputs, observations and assessment.
Its manifest binds file hashes and checks review-index expectations and raw/public
correspondence. Complete export refuses omissions, changed evidence, links,
overlapping paths and existing output files. A failed or interrupted attempt with
readable `state.json` can be packaged with `--allow-partial`; its status and
specific omissions remain visible. Earlier startup failures without retained
state need their original startup evidence kept separately.
Use the same flag to inspect a partial package. For an explicitly relocated work
tree, pass `--work`; original state bytes and paths are retained. Never manually
drop raw logs or rewrite a previous archive to make it appear complete. Complete
evidence packaging does not mean the consultation itself passed.

## Validation and target-host handoff

Run `python -m unittest discover -s tests -v` with the sibling consultant package.
The tests invoke real subprocesses using `tests/fake_claude.py`; they validate
adapter behavior, not consultant performance or Hermes/Claude compatibility.
Before claiming live performance, run the actual host smoke and the selected
persona full-report consultations with independent review. Missing worker traces remain unobserved;
do not infer cadence from final prose or add overlapping usage totals.

The flags follow the official [CLI reference](https://code.claude.com/docs/en/cli-reference)
and [headless guide](https://code.claude.com/docs/en/headless). Confirm support and
behavior in the installed host version. Compare selected problem/persona pairs
under identified candidate versions, matched host/model/tools and prospectively
frozen limits. Local tests do not qualify live consulting behavior or establish
typical conversation length.
