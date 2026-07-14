# interactive-test-cc

Reproducible multi-turn tests for the `causal-consultant` skill:

- `smoke`: activation and state-controller health
- `standard`: two analysis cycles, one HTML report, and one unexecuted derivative scope
- `mechanical-edge`: stale/current scope approvals and duplicate protection
- `causal-edge`: fixed causal-boundary challenges with a manual safety rubric

The batch runner uses one prompt registry, resumes the exact Claude Code session, validates the causal-consultant state after every turn, and saves responses, state snapshots, artifact manifests, a conversation transcript, and summaries.

```bash
python3 scripts/run_all_turns.py \
  --test standard \
  --workdir <fresh-work-directory> \
  --results-dir <empty-results-directory> \
  --statectl <Claude-visible-causal-consultant-root>/scripts/statectl.cjs
```

`smoke` uses an empty work directory. The other tests require the 777-row College `data.csv` described by the registry. Dataset provisioning, proxy credentials, and other private infrastructure stay outside this repository.

Before live replay, install or symlink the intended causal-consultant package at `${CLAUDE_CONFIG_DIR:-~/.claude}/skills/causal-consultant`. Preflight rejects a controller from any other installation so Claude's instructions and the state oracle cannot drift apart. The two repositories release independently; their version numbers do not need to match.

See [`SKILL.md`](SKILL.md) for the operating procedure and [`references/`](references) for each test's evaluation contract.
