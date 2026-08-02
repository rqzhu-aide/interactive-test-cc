# interactive-test-cc

[![Version](https://img.shields.io/badge/version-5.3.1-blue.svg)]()

Four reproducible, multi-turn regression tests for `causal-consultant`:

- `college-observational-policy`: observational dose response, heterogeneity,
  report generation, and derivative scope preparation
- `college-discovery-handoff`: bounded discovery followed by independent causal
  review and one approved analysis
- `star-interference-saturation`: school-level exposure mapping, saturation
  support, contamination, policy boundaries, and a report
- `schooling-iv-late`: IV diagnostics, weak-IV validity support, LATE boundaries,
  and a report

The runner resumes one exact Claude Code session and validates the response
shell, idle controller state, scope identity, artifact roles, schema-1 and
schema-2 manifests, execution receipts, immutable files, HTML references, and
run provenance after every turn. It continues past nonblocking findings when
the next registered prompt still has trustworthy prerequisites.

```bash
python3 scripts/run_all_turns.py \
  --test college-observational-policy \
  --workdir <fresh-work-directory> \
  --results-dir <empty-results-directory> \
  --statectl <Claude-visible-causal-consultant-root>/scripts/statectl.cjs
```

The work directory must contain only the case's canonical CSV renamed to
`data.csv`. Dataset dimensions, required columns, and fingerprints are in
[`references/test-cases.json`](references/test-cases.json). The College case
uses the existing cleaned ISLR College export. STAR uses `Ecdat::Star` and the
IV case uses `Ecdat::Schooling`, each exported without its row-name column.
Dataset provisioning and private runtime infrastructure remain outside this
repository.

Before live replay, install or symlink the intended consultant at
`${CLAUDE_CONFIG_DIR:-~/.claude}/skills/causal-consultant`. The evaluator records
the consultant and evaluator versions independently. See [`SKILL.md`](SKILL.md)
for the complete run and assessment procedure.
