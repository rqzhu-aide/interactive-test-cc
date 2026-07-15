#!/usr/bin/env python3
"""Run one registered multi-turn causal-consultant test."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "references" / "test-cases.json"
SEND_ONE = Path(__file__).resolve().with_name("send_one.py")
TEST_IDS = ("smoke", "standard", "mechanical-edge", "causal-edge")
REQUIRED_HEADINGS = ("[> Framing]", "[! Boundary]", "[? Next Steps]")
OPTIONAL_HEADING = "[+ Consultant Options]"


class RunError(RuntimeError):
    """An error that makes the next prompt unsafe to send."""


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_cases():
    try:
        registry = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunError(f"cannot read test registry: {exc}") from exc
    if registry.get("schema_version") != 1 or not isinstance(registry.get("tests"), dict):
        raise RunError("test registry must use schema_version 1 and contain a tests map")
    tests = registry["tests"]
    if set(tests) != set(TEST_IDS):
        raise RunError(f"test registry must define exactly: {', '.join(TEST_IDS)}")
    for test_id, case in tests.items():
        if not isinstance(case.get("description"), str) or not case["description"].strip():
            raise RunError(f"{test_id}: description must be nonempty")
        turns = case.get("turns")
        if not isinstance(turns, list) or not turns:
            raise RunError(f"{test_id}: turns must be a nonempty list")
        for number, turn in enumerate(turns, 1):
            if not isinstance(turn, dict):
                raise RunError(f"{test_id} turn {number}: entry must be an object")
            if not all(isinstance(turn.get(key), str) and turn[key].strip() for key in ("label", "prompt")):
                raise RunError(f"{test_id} turn {number}: label and prompt must be nonempty")
            expected = turn.get("artifacts")
            if not isinstance(expected, dict) or not expected:
                raise RunError(f"{test_id} turn {number}: artifacts must be a nonempty object")
            if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in expected.values()):
                raise RunError(f"{test_id} turn {number}: artifact counts must be nonnegative integers")
        data = case.get("data")
        if data is not None:
            if data.get("filename") != "data.csv" or not isinstance(data.get("rows"), int):
                raise RunError(f"{test_id}: invalid data requirement")
            columns = data.get("required_columns")
            if not isinstance(columns, list) or not columns or not all(isinstance(column, str) for column in columns):
                raise RunError(f"{test_id}: required_columns must be a nonempty string list")
    return tests


def run_json(command, *, cwd=None, timeout=60):
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RunError(f"command failed to start or finish: {exc}") from exc
    stdout = completed.stdout.strip()
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        detail = completed.stderr.strip() or stdout[:500] or "no output"
        raise RunError(f"command returned invalid JSON: {detail}") from exc
    if not isinstance(payload, dict):
        raise RunError("command JSON output is not an object")
    return completed.returncode, payload, completed.stderr.strip()


def paths_overlap(first, second):
    first = first.resolve()
    second = second.resolve()
    try:
        return os.path.commonpath((str(first), str(second))) in (str(first), str(second))
    except ValueError:
        return False


def validate_data(path, requirement):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            row_count = sum(1 for _ in reader)
    except (OSError, UnicodeError, csv.Error, StopIteration) as exc:
        raise RunError(f"cannot read data.csv: {exc}") from exc
    missing = [column for column in requirement["required_columns"] if column not in header]
    if missing:
        raise RunError(f"data.csv is missing required columns: {', '.join(missing)}")
    if row_count != requirement["rows"]:
        raise RunError(f"data.csv has {row_count} rows; expected {requirement['rows']}")


def preflight(case, workdir, results_dir, statectl, node_bin):
    if not statectl.is_file():
        raise RunError(f"state controller not found: {statectl}")
    config_root = Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")).expanduser().resolve()
    active_skill = config_root / "skills" / "causal-consultant"
    active_statectl = active_skill / "scripts" / "statectl.cjs"
    if not (active_skill / "SKILL.md").is_file() or not active_statectl.is_file():
        raise RunError(
            "causal-consultant is not fully installed in Claude's active personal skill directory: "
            f"{active_skill}"
        )
    if not os.path.samefile(statectl, active_statectl):
        raise RunError(
            "--statectl must belong to Claude's active causal-consultant installation; "
            "install or symlink the intended package before live replay"
        )
    code, payload, _ = run_json([node_bin, str(statectl), "validate", "--template"])
    if code != 0 or not payload.get("ok") or payload.get("code") != "VALID_TEMPLATE":
        raise RunError(f"state controller template validation failed: {payload}")
    package_path = active_skill / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        version = package.get("version") if isinstance(package, dict) else None
        if not isinstance(version, str) or not version.strip():
            raise ValueError("version must be a nonempty string")
        statectl_sha256 = hashlib.sha256(statectl.read_bytes()).hexdigest()
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise RunError(f"cannot read causal-consultant target provenance: {exc}") from exc
    if not workdir.is_dir():
        raise RunError(f"workdir not found: {workdir}")
    if paths_overlap(workdir, results_dir):
        raise RunError("workdir and results-dir must be separate, non-nested directories")

    entries = list(workdir.iterdir())
    requirement = case.get("data")
    if requirement is None:
        if entries:
            raise RunError("smoke workdir must be empty")
    else:
        if len(entries) != 1 or entries[0].name != requirement["filename"] or not entries[0].is_file():
            raise RunError("data test workdir must contain only data.csv")
        validate_data(entries[0], requirement)

    if results_dir.exists() and (not results_dir.is_dir() or any(results_dir.iterdir())):
        raise RunError("results-dir must be missing or empty")
    results_dir.mkdir(parents=True, exist_ok=True)
    return {
        "causal_consultant_version": version.strip(),
        "statectl_sha256": statectl_sha256,
    }


def check_headings(text):
    lines = [line.strip() for line in text.splitlines()]
    errors = []
    positions = []
    for heading in REQUIRED_HEADINGS:
        hits = [index for index, line in enumerate(lines) if line == heading]
        if len(hits) != 1:
            errors.append(f"{heading} appears {len(hits)} times")
        elif hits:
            positions.append(hits[0])
    option_hits = [index for index, line in enumerate(lines) if line == OPTIONAL_HEADING]
    if len(option_hits) > 1:
        errors.append(f"{OPTIONAL_HEADING} appears {len(option_hits)} times")
    if len(positions) == len(REQUIRED_HEADINGS) and positions != sorted(positions):
        errors.append("required headings are out of order")
    if len(option_hits) == 1 and len(positions) == len(REQUIRED_HEADINGS):
        if not positions[0] < option_hits[0] < positions[1]:
            errors.append(f"{OPTIONAL_HEADING} is outside the Framing-to-Boundary position")
    return {"ok": not errors, "errors": errors}


def validate_state(statectl, node_bin, workdir, previous_project_id, previous_revision):
    code, payload, stderr = run_json(
        [node_bin, str(statectl), "validate", "--project-root", str(workdir)]
    )
    errors = []
    if code != 0 or not payload.get("ok") or payload.get("code") != "VALID":
        errors.append(payload.get("message") or stderr or f"validator returned {payload.get('code')}")
    if payload.get("active_operation") is not None:
        errors.append("active_operation is not null")
    if payload.get("plan") != []:
        errors.append("next_step_plan is not empty")
    if payload.get("warnings") != []:
        errors.append(f"validator warnings: {payload.get('warnings')}")

    project_id = payload.get("project_id")
    revision = payload.get("revision")
    if not isinstance(project_id, str) or not project_id:
        errors.append("project_id is missing")
    elif previous_project_id is not None and project_id != previous_project_id:
        errors.append("project_id changed during the test")
    if not isinstance(revision, int) or isinstance(revision, bool):
        errors.append("revision is not an integer")
    elif previous_revision is None and revision < 2:
        errors.append(f"first completed turn has revision {revision}; expected at least 2")
    elif previous_revision is not None and revision <= previous_revision:
        errors.append(f"revision did not increase ({previous_revision} -> {revision})")
    return payload, errors


def is_within(path, root):
    try:
        return os.path.commonpath((str(path.resolve()), str(root.resolve()))) == str(root.resolve())
    except ValueError:
        return False


def inspect_artifacts(workdir, expected):
    output_dir = workdir / "output"
    state_path = workdir / "project_state.yaml"
    try:
        state_text = state_path.read_text(encoding="utf-8") if state_path.is_file() else ""
    except (OSError, UnicodeError):
        state_text = ""
    manifest_paths = []
    if output_dir.is_dir():
        manifest_paths.extend(output_dir.rglob("artifact-manifest.json"))
        manifest_paths.extend(output_dir.rglob("*.manifest.json"))
    manifest_paths = sorted(set(path.resolve() for path in manifest_paths))
    manifests = []
    errors = []
    covered_files = set(manifest_paths)
    operation_ids = set()

    for path in manifest_paths:
        relative = path.relative_to(workdir.resolve()).as_posix()
        location = (
            path.parent.relative_to(workdir.resolve()).as_posix()
            if path.name == "artifact-manifest.json"
            else relative[: -len(".manifest.json")]
        )
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{relative}: invalid manifest JSON ({exc})")
            continue
        if not isinstance(manifest, dict):
            errors.append(f"{relative}: manifest is not an object")
            continue
        route = manifest.get("route")
        operation_id = manifest.get("operation_id")
        files = manifest.get("files")
        if not isinstance(route, str) or not route:
            errors.append(f"{relative}: route is missing")
        if not isinstance(operation_id, str) or not operation_id:
            errors.append(f"{relative}: operation_id is missing")
        elif operation_id in operation_ids:
            errors.append(f"{relative}: operation_id is duplicated across manifests")
        elif operation_id not in state_text:
            errors.append(f"{relative}: operation_id is not recorded in project state")
        else:
            operation_ids.add(operation_id)
        if location not in state_text:
            errors.append(f"{relative}: artifact location is not recorded in project state")
        if not isinstance(files, list) or not files or not all(isinstance(item, str) and item for item in files):
            errors.append(f"{relative}: files must be a nonempty string list")
            files = []
        resolved_files = []
        for item in files:
            target = (workdir / Path(item)).resolve()
            if not is_within(target, workdir):
                errors.append(f"{relative}: listed file is outside the project ({item})")
            elif not target.is_file():
                errors.append(f"{relative}: listed file is missing ({item})")
            else:
                covered_files.add(target)
                resolved_files.append(item)
        if route == "report_writer" and not any(Path(item).suffix.lower() == ".html" for item in resolved_files):
            errors.append(f"{relative}: report manifest does not contain an HTML file")
        manifests.append(
            {
                "path": relative,
                "location": location,
                "operation_id": operation_id,
                "route": route,
                "scope_ref": manifest.get("scope_ref"),
                "completed_at": manifest.get("completed_at"),
                "summary": manifest.get("summary"),
                "files": resolved_files,
            }
        )

    output_files = set(path.resolve() for path in output_dir.rglob("*") if path.is_file()) if output_dir.is_dir() else set()
    orphaned = sorted(path.relative_to(workdir.resolve()).as_posix() for path in output_files - covered_files)
    if orphaned:
        errors.append(f"unlisted output files: {', '.join(orphaned)}")

    counts = {}
    for manifest in manifests:
        route = manifest.get("route")
        if isinstance(route, str):
            counts[route] = counts.get(route, 0) + 1
    for route, count in expected.items():
        actual = len(manifests) if route == "total" else counts.get(route, 0)
        if actual != count:
            errors.append(f"expected {count} {route} artifact(s), found {actual}")
    return {
        "ok": not errors,
        "expected": expected,
        "counts": counts,
        "manifests": manifests,
        "orphaned_files": orphaned,
        "errors": errors,
    }


def token_usage(response):
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    return (
        input_tokens if isinstance(input_tokens, int) else 0,
        output_tokens if isinstance(output_tokens, int) else 0,
    )


def snapshot_state(workdir, results_dir, number, validator):
    state_path = workdir / "project_state.yaml"
    if state_path.is_file():
        shutil.copyfile(state_path, results_dir / f"state-turn-{number:02d}.yaml")
    write_json(results_dir / f"state-turn-{number:02d}.validate.json", validator)


def write_conversation(results_dir, records):
    parts = ["# Conversation", ""]
    for record in records:
        parts.extend(
            [
                f"## Turn {record['turn']}: {record['label']}",
                "",
                "### User",
                "",
                record["prompt"],
                "",
                "### Assistant",
                "",
                record.get("response", "_No completed response._"),
                "",
            ]
        )
    (results_dir / "conversation.md").write_text("\n".join(parts), encoding="utf-8")


def copy_playground(workdir, results_dir):
    destination = results_dir / "playground"
    destination.mkdir(exist_ok=True)
    state_path = workdir / "project_state.yaml"
    if state_path.is_file():
        shutil.copyfile(state_path, destination / state_path.name)
    output_path = workdir / "output"
    if output_path.is_dir():
        shutil.copytree(output_path, destination / "output")


def write_summary(results_dir, test_id, expected_turns, records, abort_reason, target):
    completed = len(records)
    all_checks = all(
        record.get("shell", {}).get("ok")
        and record.get("state", {}).get("ok")
        and record.get("artifacts", {}).get("ok")
        for record in records
    )
    mechanics_pass = abort_reason is None and completed == expected_turns and all_checks
    turn_summaries = []
    for record in records:
        turn_summaries.append(
            {
                "turn": record["turn"],
                "label": record["label"],
                "session_id": record.get("session_id"),
                "duration_seconds": record["duration_seconds"],
                "input_tokens": record.get("input_tokens", 0),
                "output_tokens": record.get("output_tokens", 0),
                "shell": record.get("shell"),
                "state": {
                    "ok": record.get("state", {}).get("ok", False),
                    "errors": record.get("state", {}).get("errors", []),
                },
                "artifacts": {
                    "ok": record.get("artifacts", {}).get("ok", False),
                    "expected": record.get("artifacts", {}).get("expected"),
                    "counts": record.get("artifacts", {}).get("counts"),
                    "errors": record.get("artifacts", {}).get("errors", []),
                },
            }
        )
    total_input = sum(record["input_tokens"] for record in turn_summaries)
    total_output = sum(record["output_tokens"] for record in turn_summaries)
    summary = {
        "schema_version": 1,
        "test": test_id,
        "target": target,
        "completed_turns": completed,
        "expected_turns": expected_turns,
        "mechanics": "pass" if mechanics_pass else "fail",
        "causal_assessment": "not_scored" if test_id == "causal-edge" else "not_applicable",
        "abort_reason": abort_reason,
        "generated_at": utc_now(),
        "tokens": {
            "input": total_input,
            "output": total_output,
            "total": total_input + total_output,
        },
        "turns": turn_summaries,
    }
    write_json(results_dir / "summary.json", summary)

    lines = [
        f"# {test_id} test summary",
        "",
        f"Mechanical result: **{'PASS' if mechanics_pass else 'FAIL'}**",
        f"Completed turns: {completed}/{expected_turns}",
        f"Target: causal-consultant v{target['causal_consultant_version']} "
        f"(`statectl` SHA-256: `{target['statectl_sha256']}`)",
    ]
    if test_id == "causal-edge":
        lines.append("Causal assessment: **not scored** (apply the reference rubric manually)")
    if abort_reason:
        lines.append(f"Abort reason: {abort_reason}")
    lines.extend(
        [
            "",
            "| Turn | Label | Duration | Tokens | Shell | State | Artifacts |",
            "|---:|---|---:|---:|---|---|---|",
        ]
    )
    for record in records:
        tokens = record.get("input_tokens", 0) + record.get("output_tokens", 0)
        status = lambda key: "PASS" if record.get(key, {}).get("ok") else "FAIL"
        lines.append(
            f"| {record['turn']} | {record['label']} | {record['duration_seconds']:.1f}s | "
            f"{tokens} | {status('shell')} | {status('state')} | {status('artifacts')} |"
        )
    (results_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return mechanics_pass


def run_test(args, case):
    workdir = args.workdir.expanduser().resolve()
    results_dir = args.results_dir.expanduser().resolve()
    statectl = args.statectl.expanduser().resolve()
    target = preflight(case, workdir, results_dir, statectl, args.node)

    records = []
    session_id = None
    project_id = None
    revision = None
    abort_reason = None
    print(f"Running {args.test}: {len(case['turns'])} turns")

    for number, turn in enumerate(case["turns"], 1):
        print(f"[{number:02d}/{len(case['turns']):02d}] {turn['label']}", flush=True)
        prompt_path = results_dir / f"turn-{number:02d}.md"
        response_path = results_dir / f"turn-{number:02d}.json"
        prompt_path.write_text(turn["prompt"] + "\n", encoding="utf-8")
        command = [
            sys.executable,
            str(SEND_ONE),
            "--msg-file",
            str(prompt_path),
            "--out-file",
            str(response_path),
            "--workdir",
            str(workdir),
            "--claude-bin",
            args.claude_bin,
            "--max-turns",
            str(args.max_turns),
            "--timeout",
            str(args.timeout),
        ]
        if session_id:
            command.extend(["--session-id", session_id])

        started = time.monotonic()
        try:
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        except OSError as exc:
            abort_reason = f"turn {number} transport could not start: {exc}"
            break
        duration = time.monotonic() - started
        if completed.stderr.strip():
            print(completed.stderr.strip())
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else f"exit {completed.returncode}"
            abort_reason = f"turn {number} transport failed: {detail}"
            break

        try:
            response = json.loads(response_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            abort_reason = f"turn {number} response JSON failed: {exc}"
            break
        if not isinstance(response, dict) or response.get("is_error"):
            abort_reason = f"turn {number} returned an error response"
            break
        response_text = response.get("result")
        returned_session = response.get("session_id")
        if not isinstance(response_text, str) or not response_text.strip():
            abort_reason = f"turn {number} response text is missing"
            break
        if not isinstance(returned_session, str) or not returned_session:
            abort_reason = f"turn {number} session_id is missing"
            break
        if session_id is not None and returned_session != session_id:
            abort_reason = f"turn {number} resumed a different session"
            break
        session_id = returned_session

        shell = check_headings(response_text)
        try:
            validator, state_errors = validate_state(statectl, args.node, workdir, project_id, revision)
        except RunError as exc:
            abort_reason = f"turn {number} state validation failed: {exc}"
            break
        state = {"ok": not state_errors, "errors": state_errors, "validator": validator}
        snapshot_state(workdir, results_dir, number, validator)
        if not state["ok"]:
            abort_reason = f"turn {number} ended outside a valid idle state: {'; '.join(state_errors)}"
            input_tokens, output_tokens = token_usage(response)
            artifacts = inspect_artifacts(workdir, turn["artifacts"])
            write_json(results_dir / f"artifacts-turn-{number:02d}.json", artifacts)
            records.append(
                {
                    "turn": number,
                    "label": turn["label"],
                    "prompt": turn["prompt"],
                    "response": response_text,
                    "session_id": session_id,
                    "duration_seconds": duration,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "shell": shell,
                    "state": state,
                    "artifacts": artifacts,
                }
            )
            break

        project_id = validator["project_id"]
        revision = validator["revision"]
        artifacts = inspect_artifacts(workdir, turn["artifacts"])
        write_json(results_dir / f"artifacts-turn-{number:02d}.json", artifacts)
        input_tokens, output_tokens = token_usage(response)
        records.append(
            {
                "turn": number,
                "label": turn["label"],
                "prompt": turn["prompt"],
                "response": response_text,
                "session_id": session_id,
                "duration_seconds": duration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "shell": shell,
                "state": state,
                "artifacts": artifacts,
            }
        )
        print(
            f"  shell={'PASS' if shell['ok'] else 'FAIL'} "
            f"state=PASS artifacts={'PASS' if artifacts['ok'] else 'FAIL'} revision={revision}"
        )

    write_conversation(results_dir, records)
    copy_playground(workdir, results_dir)
    passed = write_summary(results_dir, args.test, len(case["turns"]), records, abort_reason, target)
    if abort_reason:
        print(f"ABORTED: {abort_reason}", file=sys.stderr)
    print(f"Mechanical result: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", choices=TEST_IDS)
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--statectl", type=Path, default=os.environ.get("CAUSAL_STATECTL"))
    parser.add_argument("--node", default=os.environ.get("NODE_BIN", "node"))
    parser.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--list-tests", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        cases = load_cases()
        if args.list_tests:
            for test_id in TEST_IDS:
                print(f"{test_id}: {len(cases[test_id]['turns'])} turns - {cases[test_id]['description']}")
            return 0
        if not args.test:
            parser.error("--test is required unless --list-tests is used")
        case = cases[args.test]
        if args.dry_run:
            print(f"{args.test}: {len(case['turns'])} turns")
            for number, turn in enumerate(case["turns"], 1):
                print(f"{number:02d}. {turn['label']} | artifacts={turn['artifacts']}")
            return 0
        if args.workdir is None or args.results_dir is None or args.statectl is None:
            parser.error("live runs require --workdir, --results-dir, and --statectl (or CAUSAL_STATECTL)")
        if args.timeout < 1 or args.max_turns < 1:
            parser.error("timeout and max-turns must be positive")
        return run_test(args, case)
    except RunError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
