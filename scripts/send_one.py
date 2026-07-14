#!/usr/bin/env python3
"""Send one prompt to Claude Code and persist its JSON response."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


DEFAULT_MAX_TURNS = 30
DEFAULT_TIMEOUT = 900


def error_result(message, **details):
    result = {"is_error": True, "error": message}
    result.update(details)
    return result


def captured_text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def send(workdir, message, session_id, max_turns, timeout, claude_bin):
    executable = shutil.which(claude_bin)
    if executable is None:
        return error_result(f"Claude Code executable not found: {claude_bin}")
    command = [
        executable,
        "-p",
        "--max-turns",
        str(max_turns),
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
    ]
    if session_id:
        command.extend(["--resume", session_id])
    command.append(message)

    try:
        completed = subprocess.run(
            command,
            cwd=workdir,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return error_result(
            f"Claude Code timed out after {timeout} seconds",
            stdout=captured_text(exc.stdout)[-2000:],
            stderr=captured_text(exc.stderr)[-2000:],
        )
    except OSError as exc:
        return error_result(f"Could not start Claude Code: {exc}")

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        return error_result(
            f"Claude Code exited with status {completed.returncode}",
            stdout=stdout[-2000:],
            stderr=stderr[-2000:],
        )
    if not stdout:
        return error_result("Claude Code returned empty stdout", stderr=stderr[-2000:])

    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return error_result(f"Claude Code returned invalid JSON: {exc}", raw=stdout[:2000])
    if not isinstance(response, dict):
        return error_result("Claude Code JSON response is not an object", raw=stdout[:2000])
    return response


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msg-file", required=True, type=Path)
    parser.add_argument("--out-file", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--session-id", help="Exact Claude Code session ID to resume")
    parser.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    workdir = args.workdir.expanduser().resolve()
    message_path = args.msg_file.expanduser().resolve()
    output_path = args.out_file.expanduser().resolve()
    if not workdir.is_dir():
        parser.error(f"workdir not found: {workdir}")
    if not message_path.is_file():
        parser.error(f"msg-file not found: {message_path}")
    if args.max_turns < 1 or args.timeout < 1:
        parser.error("max-turns and timeout must be positive")

    message = message_path.read_text(encoding="utf-8").strip()
    if not message:
        parser.error("msg-file is empty")

    mode = f"resume {args.session_id}" if args.session_id else "new session"
    print(f"[send_one] {mode}; {len(message)} characters", file=sys.stderr)
    response = send(
        str(workdir),
        message,
        args.session_id,
        args.max_turns,
        args.timeout,
        args.claude_bin,
    )
    write_json(output_path, response)

    if response.get("is_error"):
        print(f"[send_one] ERROR: {response.get('error', 'unknown error')}", file=sys.stderr)
        return 1

    turns = response.get("num_turns", "?")
    duration = response.get("duration_ms", 0) / 1000
    print(f"[send_one] completed: {turns} agent turns, {duration:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
