#!/usr/bin/env python3
"""Batch runner for multi-turn causal-consultant tests using send_one.py.

Writes all turn prompt files and runs each turn sequentially, passing
--continue for turns 2+. Handles ANTHROPIC_API_KEY fallback for
background/subprocess contexts where the env var isn't inherited.

Usage:
    cd ~/test-center/v4.5.0/session-<name>
    export ANTHROPIC_BASE_URL=http://127.0.0.1:15721
    python3 ~/.hermes/skills/interactive-test-cc/scripts/run_all_turns.py

Environment:
    ANTHROPIC_BASE_URL — required, for cc-switch proxy routing
    ANTHROPIC_API_KEY   — optional (auto-set to "dummy" if missing)

TURNS dict should be customized per session. This is a template — copy and
modify the TURNS dictionary for your specific test prompts.
"""

import subprocess
import os
import sys
import time

SEND_ONE = os.path.expanduser("~/.hermes/skills/interactive-test-cc/scripts/send_one.py")

# Example TURNS — replace with your test prompts
TURNS = {
    1: "I'm studying factors that influence college graduation rates in the US. I have data on 777 colleges with variables like admissions stats, selectivity measures, institutional resources, and student spending. I want to understand what drives better graduation outcomes — is it selectivity? resources? teaching quality? Let me know what you think and how you'd approach this.",
    # ... add turns 2-13
}


def main():
    session_dir = os.getcwd()
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:15721"
    if "ANTHROPIC_API_KEY" not in env:
        env["ANTHROPIC_API_KEY"] = "cc-switch-dummy"

    for turn_num in sorted(TURNS.keys()):
        msg = TURNS[turn_num]
        msg_file = os.path.join(session_dir, f"turn-{turn_num}.md")
        out_file = os.path.join(session_dir, f"turn-{turn_num}.json")

        with open(msg_file, "w") as f:
            f.write(msg)

        cmd = [
            sys.executable, SEND_ONE,
            "--msg-file", msg_file,
            "--out-file", out_file,
            "--workdir", session_dir,
        ]
        if turn_num > 1:
            cmd.append("--continue")

        print(f"\n{'='*60}")
        print(f"TURN {turn_num}/{len(TURNS)} — {len(msg)} chars")
        print(f"{'='*60}")

        start = time.time()
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
        elapsed = time.time() - start

        print(result.stderr.strip())
        print(f"Elapsed: {elapsed:.1f}s")
        print(f"Exit: {result.returncode}")

        if result.returncode != 0:
            print(f"STDERR: {result.stderr[:500]}")
            print(f"STDOUT: {result.stdout[:500]}")

    print("\n✅ All turns complete")


if __name__ == "__main__":
    main()
