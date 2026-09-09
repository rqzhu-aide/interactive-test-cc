# Executable v7 adapter

Hermes supplies adaptive user replies; this standard-library adapter transports
them and captures evidence for a separate reviewer. Use shared Python 3.10+,
Node 18.18+, an existing Claude Code installation, and consultant 7.0.0, 7.0.1 or
7.0.2. The explicit observation allowlist retains the same package inventory,
validator, helper and evidence checks for each supported version; it does not
admit later versions automatically.
No installation or paid consultation occurs in `preflight`.

The complete case at `cases/college-policy-v7` (case 1.1.0) contains unchanged
College data, semantic actor rules, an explicit unknown policy timetable and an
independent descriptive oracle/self-check. It supplies no causal-effect truth.
It is an adaptation of the recorded local diagnostic, not one of V7P01-V7P04.
Keep that fixture unchanged. The versioned synthetic investigation-depth cases
and first comparison stage are listed in [pilot-cases.md](pilot-cases.md).

## Configuration and startup

Save configuration outside the public work directory. Replace these Linux paths
with the actual shared executables or an already verified isolation wrapper:

```json
{
  "claude_command": ["/usr/local/bin/claude"],
  "node_command": ["/usr/bin/node"],
  "mode": "diagnostic",
  "max_agent_turns_per_call": 40,
  "call_timeout_seconds": 600,
  "limits": {
    "consultant_turns": 10,
    "active_seconds": 1800,
    "elapsed_seconds": 2700
  }
}
```

Optional fields: `model` (explicit host-supported model), `allowed_tools` (Claude
tool permission rules), `forward_subagent_text` (boolean, after checking installed
CLI support), and `host_evidence` (absolute directory). There is no implicit
permission bypass or token/cost cap. Raw per-call usage is retained; unverified
aggregate usage stays null. Tool permissions do not establish file isolation.

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
python scripts/session_driver.py preflight --case cases/college-policy-v7 --candidate /skills/causal-consultant --config /private/config.json
python scripts/session_driver.py start --case cases/college-policy-v7 --candidate /skills/causal-consultant --config /private/config.json --attempt /private/run001 --work /public/work001
```

Commands return JSON and nonzero on error. Use fresh, nonoverlapping case,
candidate, attempt and work paths. Startup checks exact hashes for every case
file, runs the independent fixture check, validates the complete consultant
distribution including `package.json`, and checks that its helper loads. It
stages only the runtime under `.claude/skills/causal-consultant` and initial
public sources. It captures Claude version/help, without sending a user message.
Confirm actual candidate selection in the host smoke, accounting for installed
skills/settings. Keep scenario names out of public paths.

Do not edit or normalize a fixture to make hashes pass. `.gitattributes` preserves
the shipped fixture bytes across platforms. Changed facts/data require a new
version and independent checks.

## Hermes actor loop

Initialize a separate persistent actor context with only the frozen `actor.json`,
`references/user-simulator.md`, and public materials/conversation. Do not give it
the oracle, reviewer packet, private traces or this operator guide. The operator
uses metadata to stage sources without revealing private locations.

For the first step, use the exact frozen `public/initial-message.txt` as `message`,
all lists empty and `stop: false`. Subsequent replies come from the actor's
semantic rules. This example illustrates the format, not a prescribed next turn:

```json
{
  "message": "The board has not agreed how colleges would use the extra money.",
  "fact_ids": ["f-policy"],
  "rule_ids": ["r-answer"],
  "attachments": [],
  "unanswered_questions": [],
  "fixture_gaps": [],
  "stop": false
}
```

Put replies in an operator inbox outside the attempt and work. Only `message`
goes to Claude stdin. Attachments are source IDs with frozen on-request triggers;
their bytes are staged at public destinations. Identify neutral filenames in the
public message when supplying them. The adapter checks IDs/paths/hashes; Hermes
and the reviewer check whether the disclosure was warranted by the exchange.

```sh
python scripts/session_driver.py step --attempt /private/run001 --reply /private/inbox/reply.json
python scripts/session_driver.py inspect --attempt /private/run001 --view actor
```

The actor view contains only public messages and available filenames. The first
call uses an explicit UUID; all later calls use `--resume` with that exact ID and
the same work directory. Verbose stream JSON retains complete stdout/stderr,
available tool/worker events, returned identity, exit/timeout and raw usage.
Missing/changed IDs, malformed results, provider errors and nonzero exits stop
the attempt. There is no automatic resend or ambient continuation fallback.

Each invocation also retains a full work snapshot and read-only v7 `status`,
`history` and `verify` output for `consultation/`, including failed turns. A
missing project is recorded, not automatically graded as a scientific defect.
The adapter never initializes or writes scientific journal records. Links are
unsupported in staged fixture/runtime/evidence trees; retain ordinary files.

Limits count attempted consultation turns and consultant subprocess active time,
including failures. Active time excludes harness observations. Elapsed time begins
at first dispatch and includes observation and user-wait time through stopping;
reviewer effort is excluded. Direct finalization without a stop record uses the
last captured turn as the end. Timeouts fit the remaining whole-run envelope;
capture/cleanup overruns remain visible. A completed objective on the last allowed turn can be reviewed.
When done, send a stop record with `message: null`, `stop: true`, no attachments.

Pending means interruption left delivery uncertain. A stale `operator.lock`
requires checking that no operator/process is active before removing just that
lock. Removing it does not clear pending state. Inspect and finalize as an
execution error if safe exact continuation cannot be established; retry as a
fresh attempt. There is no force-resend/state-repair command. Startup failures
remain in `startup-error.json`.

## Independent review

Give a separate reviewer the frozen reviewer packet, oracle and actual evidence.
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

## Validation and target-host handoff

Run `python -m unittest discover -s tests -v` with the sibling consultant package.
The tests invoke real subprocesses using `tests/fake_claude.py`; they validate
adapter behavior, not consultant performance or Hermes/Claude compatibility.
Before larger tests, run the actual host smoke and one complete College
conversation with independent review. Missing worker traces remain unobserved;
do not infer cadence from final prose or add overlapping usage totals.

The flags follow the official [CLI reference](https://code.claude.com/docs/en/cli-reference)
and [headless guide](https://code.claude.com/docs/en/headless). Confirm support and
behavior in the installed host version. The four V7P pilots and investigation-depth
campaign remain pending. For the latter, compare frozen 7.0.1 and 7.0.2 snapshots
under matched host/model/tools and prospectively frozen limits, starting with
the 12-consultation stage in the pilot guide. Local tests do not qualify these
consulting behaviors.
