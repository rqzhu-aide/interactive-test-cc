# interactive-test-cc

Test a target Claude Code skill by running multi-turn conversations
through Claude Code and capturing the results.

The Hermes agent orchestrates: writing messages, calling send_one.py
per turn, checking response format, and archiving session artifacts.

For the full procedure, see SKILL.md.

To set up repeated batch testing with private operational details (datasets,
environment, infrastructure), place a RULES.md in the test-center folder —
the agent loads it alongside this skill during pre-flight.
