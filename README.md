# Interactive Test CC v7

Version: `7.0.7`, aligned with causal-consultant. Hermes supplies a simulated user
and Claude Code hosts the consultant. The tester captures actual conversation,
released evidence, analysis and saved reporting for independent review.

The catalog contains **four problems and four independent personas**, freely
combined into 16 possible tests. The old 15 frozen bundles under `cases/` and
their dedicated generators and tests have been removed. Prior versions remain
in Git history and existing frozen run packages.

| Problem | Target replies |
|---|---:|
| `study-design` | 5 |
| `observational-did` | 10 |
| `cate-policy` | 15 |
| `data-quality-edge` | 8 |

Persona selectors are `novice`, `domain-expert`, `statistician` and `adversarial`.
Each has an explicit disclosure policy. Replies address the current issue with
its supporting record or connected bundle. A broad request does not trigger all
facts and files at once. Unanswered requests, prior disclosures, learning and
choices remain available after an interruption. Short necessary answers and
known corrections stay complete; users do not invent delays or access barriers.
Scientific truth and legitimate source access remain the same across personas.

Target lengths are descriptive and stay out of actor instructions. They are
neither deadlines nor minimums. Information and report completion follow the
conversation, without rushing or adding exchanges to meet a target.

```sh
python scripts/compose_case.py --list
python scripts/compose_case.py --problem cate-policy --persona novice --output /private/cases/run001
```

Pass the generated directory as the runner's `--case`. Composition freezes the
selected definitions and does not launch a consultation. See the
[catalog and programmer guide](references/problem-persona-matrix.md).

The consultation keeps returning findings and choices to the user. An initial
report request expresses a goal; concrete analysis and report choices follow
actual proposals and findings. Extensions return to discussion. The passive
observer preserves early-work and early-report breaches even if later approved.
Behavioral compliance, scientific quality and artifact completion are assessed
separately. Natural-language consent and uncaptured host activity still need
independent review.

Start with [SKILL.md](SKILL.md), the [runner guide](references/runner.md) and the
[Hermes/Claude contract](references/hermes-claude.md). The runner supports
preflight, start, step, inspect and finish, including source isolation, snapshot
identity and session continuity. Supported consultant versions are `7.0.0`,
`7.0.1`, `7.0.2`, `7.0.4`, `7.0.5`, `7.0.6` and `7.0.7`; unlisted versions need a
checked compatibility update. Version 7.0.7 requires `consultation-loop-v1`;
7.0.5 through 7.0.7 require `durable-exchanges-v1`.

Local validation covers all 16 compositions, scientific references, source
boundaries, runner behavior and consultation-loop chronology. See the
[implementation and validation record](references/implementation-plan.md) for
current results and coverage limits. Local subprocess tests and actor rehearsals
do not establish live Hermes/Claude performance or typical consultation length.
A missing report or resource-limited attempt is not a completed report test.

Both skills are separate Git repositories under the outer workspace. The active
tester uses `main`; the consultant uses its version-named v7 branch. Pre-v7 local
archives are separate from this shipped catalog. Loading this skill does not
install software, replace an installed consultant or start a live campaign.
