"""Subprocess test double, never a consultant or a live-host qualification."""
import json
from pathlib import Path
import sys
import time

args = sys.argv[1:]
if "--version" in args or "--help" in args:
    print("fake-claude-test-only 1.0")
    raise SystemExit(0)
scenario = args[0]
flag = "--session-id" if "--session-id" in args else "--resume"
session_id = args[args.index(flag) + 1]
marker = Path("fake-session.txt")
if flag == "--session-id":
    if marker.exists():
        raise SystemExit(17)
    marker.write_text(session_id)
elif not marker.exists() or marker.read_text() != session_id:
    raise SystemExit(18)
message = sys.stdin.read()
Path("fake-message.txt").write_text(message, encoding="utf-8")
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Fake"}]}}), flush=True)
print("full stderr retained " + "x" * 6000, file=sys.stderr, flush=True)
if scenario == "timeout":
    time.sleep(20)
elif scenario == "invalid":
    print("{truncated", flush=True)
    raise SystemExit(0)
elif scenario == "empty":
    raise SystemExit(0)
result = {"type": "result", "subtype": "success", "is_error": False,
          "session_id": session_id, "result": "What records describe how the policy was introduced?" if flag == "--session-id" else "Recorded your reply."}
if scenario == "fixture_response":
    result["result"] = Path("fake-response.txt").read_text(encoding="utf-8")
if scenario == "changed":
    result["session_id"] = "wrong-session"
if scenario == "missing_id":
    del result["session_id"]
if scenario == "empty_message":
    result["result"] = ""
if scenario == "provider_error":
    result.update({"is_error": True, "subtype": "error_max_turns"})
if scenario == "usage":
    result.update({"usage": {"input_tokens": 9, "cache_read_input_tokens": 12, "output_tokens": 7}, "total_cost_usd": 0.1})
print(json.dumps(result), flush=True)
if scenario == "duplicate":
    print(json.dumps(result), flush=True)
if scenario == "nonzero":
    raise SystemExit(4)
