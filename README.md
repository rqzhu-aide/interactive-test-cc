# interactive-test-cc

Test a Claude Code skill by running multi-turn conversations and capturing results.
The setup was created with a Hermes agent that controls and test the skill inside claude code. 
Contains: 
  * pre-flight setup
  * turn-by-turn message delivery via `send_one.py` to claude code
  * shape checking
  * session archiving

It should be modifed when trying to fit a different target testing skill  

**v3.5.0** — Simplified to ~140 lines following Karpathy guidelines.
Added Setting B (12-turn with data at turn 3, two report cycles, HTML conversion).
Extracted reference files for settings and gate test protocols.

For the full procedure, see SKILL.md.

The skill can be combined with a private operational details (datasets, proxy, infrastructure). 
For my Hermes, that is a RULES.md file in the test-center folder.
The file is stripped due to privacy issues. 
