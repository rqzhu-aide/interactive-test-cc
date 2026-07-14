# Smoke test

Use this three-turn test after installation or a small workflow change. It verifies activation, response structure, and clean controller closeout without data or artifacts.

Exact prompts and expected artifact counts live in [`test-cases.json`](test-cases.json).

| Turn | Purpose | Required result |
|---:|---|---|
| 1 | Activate and frame | A new valid project reaches an idle boundary. |
| 2 | Probe the causal boundary | No analysis or artifact is produced. |
| 3 | Request one next input | The project remains valid and idle. |

The shared runner applies the mechanical oracle after every turn: exact required response headings, successful strict state validation, an empty plan, no active operation or warnings, stable project identity, increasing revision, and zero artifacts.

Pass only when all three turns complete and every mechanical check passes.
