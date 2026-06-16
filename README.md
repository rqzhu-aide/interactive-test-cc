# interactive-test-cc

Test a Claude Code skill by running multi-turn conversations and capturing results.
A Hermes agent orchestrates: pre-flight setup, turn-by-turn message delivery via
`send_one.py`, shape checking, and session archiving.

**v3.5.0** — Simplified to ~140 lines following Karpathy guidelines.
Added Setting B (12-turn with data at turn 3, two report cycles, HTML conversion).
Extracted reference files for settings and gate test protocols.

For the full procedure, see SKILL.md.
For private operational details (datasets, proxy, infrastructure), place a RULES.md in the test-center folder.
