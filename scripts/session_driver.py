"""Small adaptive v7 adapter. Hermes supplies actor replies; a separate reviewer grades."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
import uuid

from claude_transport import capture, invoke


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def member(root, relative):
    """Portable fixture paths, without traversal, alternate streams or link escapes."""
    rel = PurePosixPath(relative)
    require(isinstance(relative, str) and relative and "\\" not in relative and ":" not in relative
            and not rel.is_absolute() and all(p not in ("..", ".") for p in relative.split("/")),
            "invalid relative path: " + str(relative))
    root = Path(root).resolve()
    target = root.joinpath(*rel.parts)
    require(target.resolve().is_relative_to(root), "path escapes root")
    current = target
    while current != root:
        require(not current.is_symlink() and not (hasattr(current, "is_junction") and current.is_junction()),
                "links are not fixture/evidence files: " + str(current))
        current = current.parent
    return target


def inventory(root):
    root = Path(root)
    require(root.is_dir(), "missing directory: " + str(root))
    result = {}
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        member(root, name)
        if path.is_file():
            result[name] = digest(path)
    return result


def validate_case(case):
    manifest = read(case / "case.json")
    require(manifest["schema_version"] == 1, "unsupported case schema")
    actual = inventory(case)
    del actual["case.json"]
    require(actual == manifest["files"], "case file identity mismatch (including unexpected files)")
    actor = read(member(case, manifest["actor"]))
    reviewer = read(member(case, manifest["reviewer"]))
    source_ids, destinations = set(), set()
    for source in manifest["sources"]:
        require(source["id"] not in source_ids, "duplicate source ID")
        require(source["destination"].casefold() not in destinations, "duplicate public destination")
        source_ids.add(source["id"])
        destinations.add(source["destination"].casefold())
        require(source["file"].startswith("public/"), "source must be explicitly public")
        require(source["file"] in actual, "source not bound to manifest")
        member(case, source["destination"])
        require(source["destination"].split("/")[0] not in (".claude", "consultation"), "reserved destination")
        require(source["availability"] in ("initial", "on_request"), "invalid availability")
    require({s["source_id"] for s in actor["sources"]} == source_ids, "actor/source mismatch")
    for field, key in (("facts", "fact_id"), ("rules", "rule_id")):
        ids = [item[key] for item in actor[field]]
        require(len(ids) == len(set(ids)), "duplicate actor IDs")
    criteria = [item["id"] for item in reviewer["criteria"]]
    require(criteria and len(criteria) == len(set(criteria)), "missing or duplicate criteria")
    request = member(case, manifest["initial_message"]).read_text(encoding="utf-8")
    require("causal-consultant" in request, "initial request must invoke consultant")
    oracle = subprocess.run([sys.executable, str(member(case, manifest["oracle_check"]))],
                            cwd=case, capture_output=True, timeout=30)
    require(oracle.returncode == 0, "independent fixture self-check failed: " + oracle.stderr.decode(errors="replace"))
    return manifest


def candidate_inventory(candidate):
    package = read(candidate / "package.json")  # Required even though absent from npm's explicit files list.
    require(package["version"] in ("7.0.0", "7.0.1"), "this observation profile requires consultant 7.0.0 or 7.0.1")
    result = {"package.json": digest(candidate / "package.json")}
    for entry in package["files"]:
        path = member(candidate, entry)
        if path.is_dir():
            result.update({entry + "/" + name: sha for name, sha in inventory(path).items()})
        else:
            result[entry] = digest(path)
    return dict(sorted(result.items()))


def validate_config(config):
    allowed = {"claude_command", "node_command", "model", "allowed_tools", "forward_subagent_text",
               "max_agent_turns_per_call", "call_timeout_seconds", "limits", "mode", "host_evidence"}
    require(not set(config) - allowed, "unknown configuration keys")
    for key in ("claude_command", "node_command"):
        require(isinstance(config[key], list) and config[key] and
                all(isinstance(x, str) and x for x in config[key]), key + " must be an argv prefix")
    # An isolation wrapper is permitted, but it cannot smuggle in Claude identity/permission flags.
    forbidden = ("--continue", "--resume", "--session-id", "--fork-session", "--no-session-persistence",
                 "--dangerously-skip-permissions", "--allow-dangerously-skip-permissions", "--permission-mode")
    require(not any(x.split("=")[0] in forbidden for x in config["claude_command"]), "unsafe transport override")
    require(config["mode"] in ("diagnostic", "verified_host"), "unknown mode")
    for value in (config["call_timeout_seconds"], config["max_agent_turns_per_call"], *config["limits"].values()):
        require(type(value) in (int, float) and math.isfinite(value) and value > 0, "limits must be positive finite numbers")
    require(set(config["limits"]) == {"consultant_turns", "active_seconds", "elapsed_seconds"}, "wrong whole-run limits")
    require(type(config["limits"]["consultant_turns"]) is int and type(config["max_agent_turns_per_call"]) is int,
            "turn limits must be integers")
    if config["mode"] == "verified_host":
        require(config.get("host_evidence"), "verified_host requires existing host smoke/isolation evidence directory")


def preflight(case, candidate, config):
    require(sys.version_info >= (3, 10), "shared Python 3.10+ required")
    validate_config(config)
    node_probe = subprocess.run(config["node_command"] + ["-p", "process.versions.node"],
                                capture_output=True, timeout=15)
    require(node_probe.returncode == 0, "shared Node cannot run")
    node_version = node_probe.stdout.decode().strip()
    require(tuple(int(part) for part in node_version.split(".")[:3]) >= (18, 18, 0), "shared Node 18.18+ required")
    manifest = validate_case(case)
    files = candidate_inventory(candidate)
    checked = subprocess.run(config["node_command"] + [str(candidate / "scripts/validate.cjs")],
                             cwd=candidate, capture_output=True, timeout=60)
    require(checked.returncode == 0, "consultant package validation failed: " + checked.stdout.decode(errors="replace"))
    validation = json.loads(checked.stdout)
    package_sha = hashlib.sha256("".join(name + "\t" + sha + "\n" for name, sha in files.items()).encode()).hexdigest()
    require(validation["ok"] and validation["package_sha256"] == package_sha, "candidate inventory mismatch")
    help_result = subprocess.run(config["node_command"] + [str(candidate / "scripts/project.cjs"), "help"],
                                 cwd=candidate, capture_output=True, timeout=30)
    require(help_result.returncode == 0, "consultant project helper cannot load")
    return {"case_manifest": manifest, "case_sha256": digest(case / "case.json"),
            "candidate_files": files, "candidate_validation": validation,
            "configuration": config, "python": sys.version, "node": node_version}


@contextmanager
def locked(attempt):
    lock = attempt / "operator.lock"
    try:
        stream = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise ValueError("another operation or interrupted operator holds the lock; inspect before recovery")
    try:
        stream.write(str(time.time()))
        stream.close()
        yield
    finally:
        lock.unlink()


def start(case, candidate, config, attempt, work):
    require(not attempt.exists() and not work.exists(), "attempt and work must both be fresh paths")
    roots = [attempt, work, case, candidate]
    require(all(not a.is_relative_to(b) and not b.is_relative_to(a)
                for i, a in enumerate(roots) for b in roots[i + 1:]), "case, candidate, attempt and work must not overlap")
    attempt.mkdir(parents=True)
    try:
        frozen = preflight(case, candidate, config)
        if config.get("host_evidence"):
            host = Path(config["host_evidence"]).resolve()
            require(not any(host.is_relative_to(p) or p.is_relative_to(host) for p in (work, attempt)), "host evidence overlaps run")
            frozen["host_files"] = inventory(host)
            require(frozen["host_files"], "empty host evidence")
            shutil.copytree(host, attempt / "host")
        shutil.copytree(case, attempt / "case")
        work.mkdir(parents=True)
        skill = work / ".claude/skills/causal-consultant"
        for name in frozen["candidate_files"]:
            destination = member(skill, name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate / name, destination)
        public = {}
        for source in frozen["case_manifest"]["sources"]:
            if source["availability"] == "initial":
                destination = member(work, source["destination"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(case / source["file"], destination)
                public[source["destination"]] = digest(destination)
        frozen["adapter_files"] = {
            name: digest(Path(__file__).parent / name) for name in ("session_driver.py", "claude_transport.py")}
        testing_root = Path(__file__).resolve().parents[1]
        testing_files = [testing_root / "SKILL.md", testing_root / "README.md"]
        testing_files += list((testing_root / "references").glob("*"))
        testing_files += [testing_root / "scripts" / name for name in frozen["adapter_files"]]
        frozen["testing_files"] = {}
        for source in testing_files:
            name = source.relative_to(testing_root).as_posix()
            destination = member(attempt / "testing", name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            frozen["testing_files"][name] = digest(destination)
        frozen["initial_public_files"] = public
        frozen["created_at"] = time.time()
        frozen["no_token_or_cost_cap_reason"] = "Exploratory utility test; preserve raw provider usage without assumed aggregation."
        write(attempt / "freeze.json", frozen)
        (attempt / "events").mkdir()
        write(attempt / "state.json", {"status": "ready", "session_id": str(uuid.uuid4()), "work": str(work),
                                       "turns": 0, "active_seconds": 0, "started_at": None,
                                       "public_files": public, "released_sources": [], "breaches": []})
        # Cheap capability evidence only; does not establish loading, isolation or resume.
        probe = capture(config["claude_command"] + ["--version"], work, "", 15, attempt / "claude-version")
        require(not probe["error"] and probe["exit_code"] == 0, "Claude command version probe failed; inspect retained startup evidence")
        capture(config["claude_command"] + ["--help"], work, "", 15, attempt / "claude-help")
        return {"attempt": str(attempt), "work": str(work), "status": "ready", "initial_message_sent": False}
    except Exception as exc:
        write(attempt / "startup-error.json", {"error": str(exc), "time": time.time()})
        if (attempt / "state.json").exists():
            state = read(attempt / "state.json")
            state["status"] = "execution_error"
            write(attempt / "state.json", state)
        raise


def integrity(attempt, state, frozen):
    require(digest(attempt / "case/case.json") == frozen["case_sha256"], "frozen case changed")
    require(inventory(attempt / "case") == {"case.json": frozen["case_sha256"], **frozen["case_manifest"]["files"]}, "frozen inputs changed")
    skill = Path(state["work"]) / ".claude/skills/causal-consultant"
    require(inventory(skill) == frozen["candidate_files"], "staged consultant changed")
    for name, sha in state["public_files"].items():
        require(digest(member(Path(state["work"]), name)) == sha, "released public input changed: " + name)
    require(all(digest(Path(__file__).parent / name) == sha for name, sha in frozen["adapter_files"].items()), "adapter changed during attempt")


def observe_project(event, state, config):
    """Retain each turn's files and read-only v7 observations, including failed turns."""
    work = Path(state["work"])
    before = inventory(work)
    shutil.copytree(work, event / "work-snapshot")
    require(inventory(event / "work-snapshot") == before == inventory(work), "work changed while capturing evidence")
    write(event / "work-files.json", before)
    helper = work / ".claude/skills/causal-consultant/scripts/project.cjs"
    for command in ("status", "history", "verify"):
        remaining = config["limits"]["elapsed_seconds"] - (time.time() - state["started_at"])
        if remaining <= 0:
            write(event / "observation-skipped.json", {"reason": "elapsed limit reached", "next_command": command})
            break
        capture(config["node_command"] + [str(helper), command, "--project-root", str(work / "consultation")],
                work, "", min(30, remaining), event / ("project-" + command))


def record_time_limits(state, config, now):
    limits = config["limits"]
    exceeded = state["active_seconds"] > limits["active_seconds"] or (
        state["started_at"] is not None and now - state["started_at"] > limits["elapsed_seconds"])
    if exceeded and "whole_run_time_limit" not in state["breaches"]:
        state["breaches"].append("whole_run_time_limit")


def step(attempt, reply):
    with locked(attempt):
        state, frozen = read(attempt / "state.json"), read(attempt / "freeze.json")
        require(state["status"] == "ready", "attempt cannot send: " + state["status"])
        integrity(attempt, state, frozen)
        config, case = frozen["configuration"], frozen["case_manifest"]
        actor = read(attempt / "case" / case["actor"])
        required = {"message", "fact_ids", "rule_ids", "attachments", "unanswered_questions", "fixture_gaps", "stop"}
        require(set(reply) == required, "reply record fields do not match actor contract")
        for field in required - {"message", "stop"}:
            require(isinstance(reply[field], list), field + " must be a list")
        require(type(reply["stop"]) is bool, "stop must be boolean")
        for field, key, packet in (("fact_ids", "fact_id", "facts"), ("rule_ids", "rule_id", "rules")):
            require(set(reply[field]) <= {item[key] for item in actor[packet]}, "unknown " + field)
        if reply["stop"]:
            require(reply["message"] is None and not reply["attachments"], "stop sends no message or attachments")
            write(attempt / "events" / (f"{state['turns'] + 1:03d}-stop.json"), reply)
            state["status"] = "awaiting_review"
            state["ended_at"] = time.time()
            record_time_limits(state, config, state["ended_at"])
            write(attempt / "state.json", state)
            return {"status": state["status"]}
        message = reply["message"]
        require(isinstance(message, str) and message.strip(), "empty actor message")
        initial = (attempt / "case" / case["initial_message"]).read_text(encoding="utf-8")
        if not state["turns"]:
            require(message == initial and not reply["fact_ids"] and not reply["attachments"], "first step must use exact frozen public request")
        private_markers = [str(attempt), str(attempt).replace("\\", "/"), case["actor"], case["reviewer"], "oracle.json"]
        require(not any(marker.casefold() in message.casefold() for marker in private_markers), "private path leaked into public text")
        limits = config["limits"]
        remaining_elapsed = limits["elapsed_seconds"] - (time.time() - state["started_at"] if state["started_at"] else 0)
        remaining_active = limits["active_seconds"] - state["active_seconds"]
        if state["turns"] >= limits["consultant_turns"] or min(remaining_elapsed, remaining_active) <= 0:
            state["status"] = "limit_reached"
            state["ended_at"] = time.time()
            state["breaches"].append("whole_run_limit")
            write(attempt / "state.json", state)
            return {"status": state["status"]}
        sources = {item["id"]: item for item in case["sources"]}
        require(len(reply["attachments"]) == len(set(reply["attachments"])), "duplicate release")
        for source_id in reply["attachments"]:
            require(source_id in sources and sources[source_id]["availability"] == "on_request", "unauthorized source release")
            require(source_id not in state["released_sources"], "source already released")
            require(not member(Path(state["work"]), sources[source_id]["destination"]).exists(), "release would overwrite a file")
        event = attempt / "events" / f"{state['turns'] + 1:03d}"
        event.mkdir()  # Refuse an existing/uncertain attempt, never overwrite it.
        write(event / "actor.json", reply)
        state["status"] = "pending"  # Persist before staging or dispatch; interrupted delivery cannot be retried.
        state["started_at"] = state["started_at"] or time.time()
        state["turns"] += 1
        write(attempt / "state.json", state)
        try:
            released = {}
            for source_id in reply["attachments"]:
                source = sources[source_id]
                destination = member(Path(state["work"]), source["destination"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(attempt / "case" / source["file"], destination)
                state["public_files"][source["destination"]] = digest(destination)
                state["released_sources"].append(source_id)
                released[source_id] = {"path": source["destination"], "sha256": digest(destination)}
            write(event / "releases.json", released)
            result = invoke(config, state["work"], state["session_id"], state["turns"] == 1, message,
                            min(config["call_timeout_seconds"], remaining_active, remaining_elapsed), event / "transport")
            state["active_seconds"] += result["active_seconds"]
            state["status"] = "execution_error" if result["error"] else "ready"
            if result["error"] == "timeout":
                state["breaches"].append("call_or_remaining_time_limit")
            write(event / "public.json", {"user": message, "assistant": result["message"],
                                          "attachments": [v["path"] for v in released.values()]})
            write(attempt / "state.json", state)
            observe_project(event, state, config)
            state["last_activity_at"] = time.time()
            record_time_limits(state, config, state["last_activity_at"])
            if state["status"] == "ready" and state["breaches"]:
                state["status"] = "limit_reached"
            if state["status"] == "execution_error" or state["breaches"]:
                state["ended_at"] = state["last_activity_at"]
            write(attempt / "state.json", state)
            return {"status": state["status"], "message": result["message"], "error": result["error"]}
        except Exception as exc:
            write(event / "operator-error.json", {"error": str(exc), "time": time.time()})
            state["status"] = "execution_error"
            state["ended_at"] = time.time()
            record_time_limits(state, config, state["ended_at"])
            write(attempt / "state.json", state)
            # Delivery may be uncertain. Preserve the attempt and do not permit another dispatch.
            raise


def evidence(attempt, state):
    files = {"private/" + name: sha for name, sha in inventory(attempt).items()
             if name not in ("operator.lock", "review-index.json", "assessment.json", "state.json")}
    files.update({"work/" + name: sha for name, sha in inventory(Path(state["work"])).items()})
    files["state_at_review"] = identity(state)
    return {"sha256": identity(files), "files": files}


def inspect(attempt, view):
    with locked(attempt):
        state = read(attempt / "state.json")
        conversation = [read(path) for path in sorted((attempt / "events").glob("*/public.json"))]
        if view == "actor":
            return {"conversation": conversation, "public_files": list(state["public_files"])}
        require(state["status"] != "finished", "review already finalized")
        index = evidence(attempt, state)
        write(attempt / "review-index.json", index)
        return {"state": state, "evidence_sha256": index["sha256"], "index": str(attempt / "review-index.json")}


def assess(review, state, frozen, index):
    require(review["evidence_sha256"] == index["sha256"], "review evidence changed; inspect and review again")
    require(review["test_validity"] in ("valid", "invalid", "unverified"), "invalid test validity")
    require(review["outcome"] in ("objective_met", "useful_stop", "incomplete", "execution_error"), "invalid outcome")
    require(isinstance(review.get("stop_reason"), str) and review["stop_reason"].strip(), "stop reason required")
    require(isinstance(review.get("reviewer"), str) and review["reviewer"].strip(), "identify independent reviewer")

    def references(item):
        require(item.get("evidence_refs") and all(ref in index["files"] for ref in item["evidence_refs"]), "missing or unbound evidence references")

    packet = frozen["reviewer_packet"]
    criteria = {item["id"]: item for item in packet["criteria"]}
    require(set(review["coverage"]) == set(criteria), "coverage must address every frozen criterion")
    missing = False
    for key, item in review["coverage"].items():
        require(item["status"] in ("observed", "unobserved", "not_applicable"), "invalid coverage status")
        require(item.get("reason"), "coverage reason required")
        if item["status"] == "observed":
            references(item)
        if item["status"] == "not_applicable":
            require(criteria[key].get("conditional"), "unconditional criterion cannot be waived")
        missing |= criteria[key].get("required", True) and item["status"] == "unobserved"
    for finding in review["findings"]:
        require(finding["owner"] in ("consultant", "simulator", "harness", "fixture", "environment"), "invalid finding owner")
        require(finding["severity"] in ("minor", "material", "fundamental"), "invalid severity")
        require(finding["criterion"] in criteria and finding.get("description") and finding.get("consequence"), "incomplete finding")
        references(finding)
    validity = review["test_validity"]
    if frozen["configuration"]["mode"] == "diagnostic":
        validity = "invalid"
    elif validity == "valid":
        for key in ("candidate_loading", "exact_resume", "private_isolation", "role_separation"):
            check = review.get("host_checks", {}).get(key, {})
            require(check.get("verified") is True and check.get("reason"), "missing reviewed host check: " + key)
            references(check)
            require(any(ref.startswith("private/host/") for ref in check["evidence_refs"]), "host checks require captured host evidence")
    outcome = review["outcome"]
    if state["status"] in ("pending", "execution_error"):
        outcome = "execution_error"
    elif state["status"] == "limit_reached":
        outcome = "incomplete"
    if outcome == "useful_stop":
        require(packet.get("useful_stop") and review.get("useful_stop_basis"), "case does not permit this useful stop")
    defects = [f for f in review["findings"] if f["owner"] == "consultant"]
    if any(f["severity"] in ("material", "fundamental") for f in defects):
        rating = "fail"
    elif validity != "valid" or missing or state["breaches"] or outcome not in ("objective_met", "useful_stop"):
        rating = "inconclusive"
    else:
        rating = "weak" if defects else "pass"
    return {**review, "test_validity": validity, "outcome": outcome, "quality_rating": rating,
            "resources": {"consultant_turns": state["turns"],
                          "active_seconds": None if state["status"] == "pending" else state["active_seconds"],
                          "recorded_active_seconds": state["active_seconds"],
                          "elapsed_seconds": None if state["status"] == "pending" else (
                              state.get("ended_at", state.get("last_activity_at", state["started_at"])) - state["started_at"] if state["started_at"] else 0),
                          "limits": frozen["configuration"]["limits"],
                          "active_time_scope": "Consultant subprocess only; harness observations and reviewer effort excluded.",
                          "elapsed_time_scope": "First dispatch through stop/failure/limit, or last captured turn when finalized directly; reviewer effort excluded.",
                          "breaches": state["breaches"], "aggregate_tokens": None, "aggregate_cost_usd": None,
                          "usage_scope": "Raw per-call result usage in transport.json; aggregation not established."}}


def finish(attempt, review):
    with locked(attempt):
        state, frozen = read(attempt / "state.json"), read(attempt / "freeze.json")
        require(state["status"] != "finished", "already finalized")
        index = evidence(attempt, state)
        frozen["reviewer_packet"] = read(attempt / "case" / frozen["case_manifest"]["reviewer"])
        result = assess(review, state, frozen, index)
        write(attempt / "assessment.json", result)
        state["status"] = "finished"
        write(attempt / "state.json", state)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "start"):
        p = commands.add_parser(name)
        for argument in ("case", "candidate", "config"):
            p.add_argument("--" + argument, required=True, type=Path)
        if name == "start":
            p.add_argument("--attempt", required=True, type=Path)
            p.add_argument("--work", required=True, type=Path)
    for name in ("step", "inspect", "finish"):
        p = commands.add_parser(name)
        p.add_argument("--attempt", required=True, type=Path)
        if name == "step":
            p.add_argument("--reply", required=True, type=Path)
        if name == "inspect":
            p.add_argument("--view", required=True, choices=("actor", "reviewer"))
        if name == "finish":
            p.add_argument("--assessment", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command in ("preflight", "start"):
            common = (args.case.resolve(), args.candidate.resolve(), read(args.config))
            result = preflight(*common) if args.command == "preflight" else start(*common, args.attempt.resolve(), args.work.resolve())
        elif args.command == "step":
            result = step(args.attempt.resolve(), read(args.reply))
        elif args.command == "inspect":
            result = inspect(args.attempt.resolve(), args.view)
        else:
            result = finish(args.attempt.resolve(), read(args.assessment))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
