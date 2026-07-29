# interactive-test-cc

Reproducible multi-turn tests for the `causal-consultant` skill:

- `smoke`: activation and state-controller health
- `standard`: two analysis cycles, one HTML report, and one unexecuted derivative scope
- `mechanical-edge`: stale/current scope approvals and duplicate protection
- `causal-edge`: fixed causal-boundary challenges with a manual safety rubric

The batch runner uses one prompt registry, resumes the exact Claude Code session, checks delivered responses and numbered menus against persisted controller state, validates idle state, revision budgets, scope identity, and immutable artifacts after every turn, checks HTML references, and saves responses, state snapshots, input and runtime provenance, a conversation transcript, and summaries. Completed standard, mechanical-edge, and causal-edge runs keep their workflow assessment pending until the saved rubric is reviewed and recorded through the runner; an automated failure remains a final failure.

```bash
python3 scripts/run_all_turns.py \
  --test standard \
  --workdir <fresh-work-directory> \
  --results-dir <empty-results-directory> \
  --statectl <Claude-visible-causal-consultant-root>/scripts/statectl.cjs
```

`smoke` uses an empty work directory. The other tests require the 777-row College `data.csv` described by the registry. Dataset provisioning, proxy credentials, and other private infrastructure stay outside this repository.

Before live replay, install or symlink the intended causal-consultant package at `${CLAUDE_CONFIG_DIR:-~/.claude}/skills/causal-consultant`. Preflight rejects a controller from any other installation so Claude's instructions and the state oracle cannot drift apart. Matching release numbers identify the consultant and test package intended to be used together.

See [`SKILL.md`](SKILL.md) for the operating procedure and [`references/`](references) for each test's evaluation contract.
