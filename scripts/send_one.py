#!/usr/bin/env python3
"""send_one.py — Send a message to Claude Code, write raw JSON output to file.

Usage:
    python3 send_one.py --msg-file turn-1.md --out-file turn-1.json
    python3 send_one.py --msg-file turn-2.md --out-file turn-2.json --continue

Environment:
    CC_ALLOWED_TOOLS  — tool allowlist (default: Bash,Read,Write)
    ANTHROPIC_BASE_URL — optional, for routing through a proxy
"""

import argparse
import json
import os
import subprocess
import sys

CLAUDE_BIN = "claude"
DEFAULT_MAX_TURNS = 30
DEFAULT_TIMEOUT = 900
ALLOWED_TOOLS = os.environ.get("CC_ALLOWED_TOOLS", "Bash,Read,Write")


def send(workdir, message, continue_session, max_turns, timeout):
    env = os.environ.copy()

    cmd = [CLAUDE_BIN]
    if continue_session:
        cmd.extend(["-c", "-p", message])
    else:
        cmd.extend(["-p", message])

    cmd.extend([
        "--max-turns", str(max_turns),
        "--output-format", "json",
        "--allowedTools", ALLOWED_TOOLS,
        "--dangerously-skip-permissions",
    ])

    result = subprocess.run(
        cmd, env=env, capture_output=True, text=True,
        timeout=timeout, cwd=workdir
    )

    stdout = result.stdout.strip()
    if not stdout:
        return {"is_error": True, "error": "Empty stdout",
                "stderr": result.stderr.strip()[:500]}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        return {"is_error": True, "error": f"JSON parse: {e}",
                "raw": stdout[:2000]}


def main():
    parser = argparse.ArgumentParser(description="Send a message to Claude Code")
    parser.add_argument("--msg-file", required=True,
                        help="File containing the message to send")
    parser.add_argument("--out-file", required=True,
                        help="File to write the JSON response to")
    parser.add_argument("--workdir", required=True,
                        help="Working directory for Claude Code")
    parser.add_argument("--continue", dest="continue_session",
                        action="store_true",
                        help="Continue previous session (-c)")
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    workdir = os.path.expanduser(args.workdir)
    if not os.path.isdir(workdir):
        print(f"ERROR: workdir not found: {workdir}", file=sys.stderr)
        sys.exit(1)

    msg_file = os.path.expanduser(args.msg_file)
    if not os.path.isfile(msg_file):
        print(f"ERROR: msg-file not found: {msg_file}", file=sys.stderr)
        sys.exit(1)

    with open(msg_file) as f:
        message = f.read().strip()

    if not message:
        print("ERROR: empty message", file=sys.stderr)
        sys.exit(1)

    mode = "continue" if args.continue_session else "fresh"
    print(f"[send_one] {mode} session, {len(message)} chars", file=sys.stderr)

    result = send(workdir, message, args.continue_session,
                  args.max_turns, args.timeout)

    out_file = os.path.expanduser(args.out_file)
    os.makedirs(os.path.dirname(out_file) or ".", exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)

    if result.get("is_error"):
        print(f"[send_one] ❌ {result.get('error')}", file=sys.stderr)
        sys.exit(1)
    else:
        turns = result.get("num_turns", "?")
        dur = result.get("duration_ms", 0) / 1000
        reply_len = len(result.get("result", ""))
        print(f"[send_one] ✓ {turns} turns, {dur:.1f}s, {reply_len} chars",
              file=sys.stderr)


if __name__ == "__main__":
    main()
