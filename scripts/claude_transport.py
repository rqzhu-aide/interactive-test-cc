"""One Claude Code invocation. No retries, ambient continuation or permission bypass."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def capture(argv, cwd, stdin, timeout, output):
    """Retain full bytes even on timeout/cancellation; stop only this process tree."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    report = {"argv": argv, "cwd": str(cwd), "started_at": started,
              "exit_code": None, "error": None}
    (output / "request.txt").write_text(stdin, encoding="utf-8")
    (output / "command.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    process = None
    with (output / "stdout.txt").open("wb") as stdout, (output / "stderr.txt").open("wb") as stderr:
        try:
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE,
                                       stdout=stdout, stderr=stderr, **options)
            process.communicate(stdin.encode("utf-8"), timeout=timeout)
            report["exit_code"] = process.returncode
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            report["error"] = "timeout" if isinstance(exc, subprocess.TimeoutExpired) else "cancelled"
            if process is not None:
                if os.name == "nt":
                    cleanup = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                             capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    (output / "cleanup.stdout.txt").write_bytes(cleanup.stdout)
                    (output / "cleanup.stderr.txt").write_bytes(cleanup.stderr)
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.kill() if process.poll() is None else None
                process.communicate()
                report["exit_code"] = process.returncode
        except OSError as exc:
            report["error"] = "launch_error: " + str(exc)
    report["finished_at"] = time.time()
    report["active_seconds"] = report["finished_at"] - started
    (output / "process.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def invoke(config, work, session_id, fresh, message, timeout, output):
    command = list(config["claude_command"])
    command += ["--print", "--output-format", "stream-json", "--verbose",
                "--max-turns", str(config["max_agent_turns_per_call"]),
                "--session-id" if fresh else "--resume", session_id]
    if config.get("model"):
        command += ["--model", config["model"]]
    # Configuration is explicit and frozen. No arbitrary flags can override identity.
    if config.get("allowed_tools"):
        command += ["--allowedTools", ",".join(config["allowed_tools"])]
    if config.get("forward_subagent_text", False):
        command += ["--forward-subagent-text"]
    report = capture(command, work, message, timeout, output)
    report.update({"session_id": None, "message": None, "usage": None,
                   "total_cost_usd": None, "provider_duration_ms": None})
    try:
        lines = (Path(output) / "stdout.txt").read_text(encoding="utf-8").splitlines()
        events = [json.loads(line) for line in lines if line.strip()]
        results = [item for item in events if isinstance(item, dict) and item.get("type") == "result"]
        if len(results) != 1:
            raise ValueError("expected exactly one final result")
        result = results[0]
        report["session_id"] = result.get("session_id")
        report["usage"] = result.get("usage")
        report["total_cost_usd"] = result.get("total_cost_usd")
        report["provider_duration_ms"] = result.get("duration_ms")
        if result.get("session_id") != session_id:
            raise ValueError("session identity missing or changed")
        if report["exit_code"] != 0 or result.get("is_error") or result.get("subtype") != "success":
            raise ValueError("provider execution failed")
        if not isinstance(result.get("result"), str) or not result["result"].strip():
            raise ValueError("empty public reply")
        if not report["error"]:
            report["message"] = result["result"]
    except (ValueError, UnicodeError) as exc:
        report["error"] = report["error"] or "invalid_response: " + str(exc)
    (Path(output) / "transport.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
