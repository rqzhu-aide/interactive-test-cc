#!/usr/bin/env python3
"""Run one registered multi-turn causal-consultant test."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "references" / "test-cases.json"
SEND_ONE = Path(__file__).resolve().with_name("send_one.py")
TEST_IDS = ("smoke", "standard", "mechanical-edge", "causal-edge")
ARTIFACT_ROUTES = {
    "data_audit",
    "causal_discovery",
    "analysis_execution",
    "report_writer",
}
ARTIFACT_EXPECTATION_KEYS = {"new", "total", *ARTIFACT_ROUTES}
MANIFEST_KEYS = {
    "schema_version",
    "operation_id",
    "route",
    "scope_ref",
    "files",
    "completed_at",
    "summary",
}
ARTIFACT_RECORD_KEYS = {
    "artifact_id",
    "operation_id",
    "route",
    "location",
    "created_at",
    "summary",
    "design",
    "support",
}
ARTIFACT_RECORD_REQUIRED = {
    "artifact_id",
    "operation_id",
    "route",
    "location",
    "created_at",
    "summary",
}
REQUIRED_HEADINGS = ("[> Framing]", "[! Boundary]", "[? Next Steps]")
OPTIONAL_HEADING = "[+ Consultant Options]"
VERSION_PATTERN = re.compile(r"^Version: `([^`]+)`$", re.MULTILINE)
WINDOWS_ABSOLUTE_REFERENCE = re.compile(r"^[A-Za-z]:[\\/]")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
RFC3339_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$"
)
MANUAL_RATINGS = {
    "mechanical-edge": {"pass", "fail"},
    "standard": {"pass", "fail"},
    "causal-edge": {"safe", "weak", "fail"},
}
SUMMARY_SCHEMA_VERSION = 2
EXIT_PENDING = 3


class RunError(RuntimeError):
    """An error that makes the next prompt unsafe to send."""


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_test_suite_version():
    try:
        match = VERSION_PATTERN.search((ROOT / "SKILL.md").read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise RunError(f"cannot read interactive-test-cc version: {exc}") from exc
    if match is None or not match.group(1).strip():
        raise RunError("interactive-test-cc SKILL.md has no valid Version line")
    return match.group(1).strip()


def skill_runtime_sha256(skill_root):
    required = [
        skill_root / "SKILL.md",
        skill_root / "scripts" / "statectl.cjs",
        skill_root / "package.json",
    ]
    directories = [skill_root / "references", skill_root / "assets"]
    hooks = skill_root / "project-hooks"
    if hooks.exists():
        directories.append(hooks)
    missing = [path for path in required if not path.is_file()]
    missing.extend(path for path in directories if not path.is_dir())
    if missing:
        names = ", ".join(path.relative_to(skill_root).as_posix() for path in missing)
        raise RunError(f"causal-consultant runtime input is missing: {names}")

    paths = required[:]
    for directory in directories:
        paths.extend(path for path in directory.rglob("*") if path.is_file())
    paths = sorted(set(paths), key=lambda path: path.relative_to(skill_root).as_posix())

    digest = hashlib.sha256()
    try:
        for path in paths:
            relative = path.relative_to(skill_root).as_posix().encode("utf-8")
            content = path.read_bytes()
            digest.update(b"path\0")
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(b"content\0")
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
    except (OSError, UnicodeError) as exc:
        raise RunError(f"cannot hash causal-consultant runtime: {exc}") from exc
    return digest.hexdigest()


def suite_runtime_sha256():
    required = [ROOT / "SKILL.md", SEND_ONE, Path(__file__).resolve()]
    missing = [path for path in required if not path.is_file()]
    if not (ROOT / "references").is_dir():
        missing.append(ROOT / "references")
    if missing:
        names = ", ".join(path.relative_to(ROOT).as_posix() for path in missing)
        raise RunError(f"interactive-test-cc runtime input is missing: {names}")

    paths = required + [path for path in (ROOT / "references").rglob("*") if path.is_file()]
    digest = hashlib.sha256()
    try:
        for path in sorted(set(paths), key=lambda item: item.relative_to(ROOT).as_posix()):
            relative = path.relative_to(ROOT).as_posix().encode("utf-8")
            content = path.read_bytes()
            digest.update(b"path\0")
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(b"content\0")
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
    except (OSError, UnicodeError) as exc:
        raise RunError(f"cannot hash interactive-test-cc runtime: {exc}") from exc
    return digest.hexdigest()


def validate_runtime_provenance(target):
    current = skill_runtime_sha256(Path(target["skill_root"]))
    if current != target["skill_runtime_sha256"]:
        raise RunError("installed causal-consultant runtime changed during the test")
    if suite_runtime_sha256() != target["test_suite_runtime_sha256"]:
        raise RunError("interactive-test-cc runtime changed during the test")
    if target.get("input_data") is not None:
        data_path = Path(target["input_path"])
        try:
            current_data_sha256 = sha256_file(data_path)
        except OSError as exc:
            raise RunError(f"cannot verify data.csv during the test: {exc}") from exc
        if current_data_sha256 != target["input_data"]["sha256"]:
            raise RunError("data.csv changed during the test")


def capture_review_evidence(results_dir, excluded=()):
    """Fingerprint the saved run evidence used by qualitative review."""
    root = results_dir.resolve()
    ignored = {"summary.json", "summary.md", *excluded}
    paths = []
    digest = hashlib.sha256()
    try:
        candidates = sorted(
            (path for path in root.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(root).as_posix(),
        )
        for path in candidates:
            relative = path.relative_to(root).as_posix()
            if relative in ignored:
                continue
            if path.is_symlink():
                raise RunError(f"review evidence must not contain a symlink: {relative}")
            content_sha256 = sha256_file(path)
            encoded = relative.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
            digest.update(bytes.fromhex(content_sha256))
            paths.append(relative)
    except (OSError, UnicodeError, ValueError) as exc:
        raise RunError(f"cannot fingerprint review evidence: {exc}") from exc
    required = {"conversation.md", "test-reference.md"}
    if not required.issubset(paths):
        raise RunError("review evidence is missing conversation.md or test-reference.md")
    return {
        "sha256": digest.hexdigest(),
        "file_count": len(paths),
        "paths": paths,
    }


class HtmlLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicate_ids = set()
        self.references = []

    def handle_starttag(self, tag, attrs):
        self._collect(attrs)

    def handle_startendtag(self, tag, attrs):
        self._collect(attrs)

    def _collect(self, attrs):
        for name, value in attrs:
            if not isinstance(value, str):
                continue
            if name.lower() == "id":
                if value in self.ids:
                    self.duplicate_ids.add(value)
                self.ids.add(value)
            elif name.lower() in ("href", "src"):
                self.references.append((name.lower(), value))


def parse_html(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return None, f"cannot read HTML ({exc})"
    parser = HtmlLinks()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        return None, f"cannot parse HTML ({exc})"
    return parser, None


def load_cases():
    try:
        registry = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunError(f"cannot read test registry: {exc}") from exc
    if (
        not isinstance(registry, dict)
        or registry.get("schema_version") != 1
        or not isinstance(registry.get("tests"), dict)
    ):
        raise RunError("test registry must use schema_version 1 and contain a tests map")
    tests = registry["tests"]
    if set(tests) != set(TEST_IDS):
        raise RunError(f"test registry must define exactly: {', '.join(TEST_IDS)}")
    for test_id, case in tests.items():
        if not isinstance(case, dict):
            raise RunError(f"{test_id}: test definition must be an object")
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
            unknown = sorted(set(expected) - ARTIFACT_EXPECTATION_KEYS)
            if unknown:
                raise RunError(
                    f"{test_id} turn {number}: unknown artifact expectation(s): {', '.join(unknown)}"
                )
            if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in expected.values()):
                raise RunError(f"{test_id} turn {number}: artifact counts must be nonnegative integers")
        data = case.get("data")
        if data is not None:
            if not isinstance(data, dict):
                raise RunError(f"{test_id}: data requirement must be an object or null")
            if data.get("filename") != "data.csv" or not isinstance(data.get("rows"), int):
                raise RunError(f"{test_id}: invalid data requirement")
            columns = data.get("required_columns")
            if not isinstance(columns, list) or not columns or not all(isinstance(column, str) for column in columns):
                raise RunError(f"{test_id}: required_columns must be a nonempty string list")
            canonical_sha256 = data.get("canonical_sha256")
            if not isinstance(canonical_sha256, str) or not SHA256_PATTERN.fullmatch(canonical_sha256):
                raise RunError(f"{test_id}: canonical_sha256 must be a lowercase SHA-256 digest")
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
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except (OSError, UnicodeError, csv.Error, StopIteration) as exc:
        raise RunError(f"cannot read data.csv: {exc}") from exc
    if not rows:
        raise RunError("data.csv is empty")
    header = rows[0]
    row_count = len(rows) - 1
    missing = [column for column in requirement["required_columns"] if column not in header]
    if missing:
        raise RunError(f"data.csv is missing required columns: {', '.join(missing)}")
    if row_count != requirement["rows"]:
        raise RunError(f"data.csv has {row_count} rows; expected {requirement['rows']}")
    canonical = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    if canonical_sha256 != requirement["canonical_sha256"]:
        raise RunError("data.csv does not match the registered College dataset")
    return {
        "filename": path.name,
        "bytes": len(raw),
        "rows": row_count,
        "columns": header,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_sha256": canonical_sha256,
    }


def require_controller_capabilities(test_id, template_result):
    if test_id == "smoke":
        return
    capabilities = template_result.get("capabilities")
    if not isinstance(capabilities, dict) or capabilities.get("scope_snapshot") != 1:
        raise RunError(f"{test_id} requires controller capability scope_snapshot 1")


def preflight(test_id, case, workdir, results_dir, statectl, node_bin):
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
    require_controller_capabilities(test_id, payload)
    package_path = active_skill / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        version = package.get("version") if isinstance(package, dict) else None
        if not isinstance(version, str) or not version.strip():
            raise ValueError("version must be a nonempty string")
        statectl_sha256 = hashlib.sha256(statectl.read_bytes()).hexdigest()
        runtime_sha256 = skill_runtime_sha256(active_skill)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise RunError(f"cannot read causal-consultant target provenance: {exc}") from exc
    if not workdir.is_dir():
        raise RunError(f"workdir not found: {workdir}")
    if paths_overlap(workdir, results_dir):
        raise RunError("workdir and results-dir must be separate, non-nested directories")

    entries = list(workdir.iterdir())
    requirement = case.get("data")
    input_data = None
    if requirement is None:
        if entries:
            raise RunError("smoke workdir must be empty")
    else:
        if len(entries) != 1 or entries[0].name != requirement["filename"] or not entries[0].is_file():
            raise RunError("data test workdir must contain only data.csv")
        input_data = validate_data(entries[0], requirement)

    if results_dir.exists() and (not results_dir.is_dir() or any(results_dir.iterdir())):
        raise RunError("results-dir must be missing or empty")
    results_dir.mkdir(parents=True, exist_ok=True)
    return {
        "test_suite_version": load_test_suite_version(),
        "test_suite_runtime_sha256": suite_runtime_sha256(),
        "test_case_sha256": hashlib.sha256(
            json.dumps(case, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "causal_consultant_version": version.strip(),
        "statectl_sha256": statectl_sha256,
        "skill_runtime_sha256": runtime_sha256,
        "skill_root": str(active_skill),
        "input_data": input_data,
        "input_path": str(entries[0].resolve()) if input_data is not None else None,
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
    framing_hits = [index for index, line in enumerate(lines) if line == REQUIRED_HEADINGS[0]]
    if len(framing_hits) == 1:
        prefix = [line for line in lines[: framing_hits[0]] if line]
        welcome = "[Causal-Consultant Loaded] This is a new project. Causal analysis team ready."
        allowed_prefix = (
            not prefix
            or (len(prefix) == 1 and (prefix[0].startswith("[OK Confirmed]") or prefix[0] == welcome))
            or (
                len(prefix) == 2
                and (
                    (prefix[0].startswith("[OK Confirmed]") and prefix[1] == welcome)
                    or (prefix[0] == welcome and prefix[1].startswith("[OK Confirmed]"))
                )
            )
        )
        if not allowed_prefix:
            errors.append("prose appears before the heading shell")
    option_hits = [index for index, line in enumerate(lines) if line == OPTIONAL_HEADING]
    if len(option_hits) > 1:
        errors.append(f"{OPTIONAL_HEADING} appears {len(option_hits)} times")
    if len(positions) == len(REQUIRED_HEADINGS) and positions != sorted(positions):
        errors.append("required headings are out of order")
    if len(option_hits) == 1 and len(positions) == len(REQUIRED_HEADINGS):
        if not positions[0] < option_hits[0] < positions[1]:
            errors.append(f"{OPTIONAL_HEADING} is outside the Framing-to-Boundary position")
    return {"ok": not errors, "errors": errors}


def validate_state(
    statectl,
    node_bin,
    workdir,
    previous_project_id,
    previous_revision,
    previous_manifest_count,
    manifest_count,
):
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
    else:
        baseline = 0 if previous_revision is None else previous_revision
        revision_delta = revision - baseline
        manifest_growth = manifest_count - previous_manifest_count
        if manifest_growth not in (0, 1):
            errors.append(
                f"artifact manifest count changed by {manifest_growth}; expected 0 or 1"
            )
        if revision_delta < 2:
            errors.append(
                f"revision increased by {revision_delta}; one completed operation requires at least 2 mutations"
            )
        elif manifest_growth == 0 and revision_delta > 3:
            errors.append(
                f"revision increased by {revision_delta} without a new artifact; expected at most 3"
            )
        elif manifest_growth == 1 and revision_delta != 4:
            errors.append(
                f"revision increased by {revision_delta} with one new artifact; expected 4"
            )
    return payload, errors


def normalize_scope_snapshot(snapshot):
    """Return the stable scope fields used by deterministic transition checks."""
    if not isinstance(snapshot, dict) or not {"analysis", "report"}.issubset(snapshot):
        return None, ["scope_snapshot is missing or invalid"]
    raw_analysis = snapshot["analysis"]
    raw_report = snapshot["report"]
    if not isinstance(raw_analysis, dict):
        return None, ["scope_snapshot.analysis is invalid"]

    errors = []
    analysis_keys = {"scope_id", "scope_revision", "current_status", "support", "last_updated"}
    analysis = {}
    for route, entry in raw_analysis.items():
        if (
            not isinstance(route, str)
            or not route
            or not isinstance(entry, dict)
            or not analysis_keys.issubset(entry)
            or not isinstance(entry["current_status"], str)
            or not (entry["support"] is None or isinstance(entry["support"], str))
            or not (entry["last_updated"] is None or isinstance(entry["last_updated"], str))
        ):
            errors.append(f"analysis scope snapshot {route!r} has an invalid shape")
        else:
            analysis[route] = {key: entry[key] for key in analysis_keys}
    report_keys = {"scope_id", "scope_revision", "current_status", "last_updated"}
    if raw_report is not None and (
        not isinstance(raw_report, dict)
        or not report_keys.issubset(raw_report)
        or not isinstance(raw_report["current_status"], str)
        or not (raw_report["last_updated"] is None or isinstance(raw_report["last_updated"], str))
    ):
        errors.append("report scope snapshot has an invalid shape")
    if errors:
        return None, errors
    report = None if raw_report is None else {key: raw_report[key] for key in report_keys}
    snapshot = {"analysis": analysis, "report": report}

    if any(scope_ref(entry) is None for entry in analysis.values()):
        errors.append("analysis scope snapshot has an invalid identity")
    if report is not None and scope_ref(report) is None:
        errors.append("report scope snapshot has an invalid identity")
    return (None, errors) if errors else (snapshot, [])


def scope_ref(entry):
    if not isinstance(entry, dict):
        return None
    scope_id = entry.get("scope_id")
    revision = entry.get("scope_revision")
    if (
        not isinstance(scope_id, str)
        or not scope_id
        or not isinstance(revision, int)
        or isinstance(revision, bool)
        or revision < 1
    ):
        return None
    return scope_id, revision


def check_new_manifest_scope_bindings(raw_snapshot, previous_snapshot, artifacts):
    """Bind every new analysis/report manifest to the prior ready scope and current done scope."""
    relevant = [
        manifest
        for manifest in artifacts.get("new_manifests", [])
        if manifest.get("route") in ("analysis_execution", "report_writer")
    ]
    if not relevant:
        return []

    current, errors = normalize_scope_snapshot(raw_snapshot)
    if errors:
        return errors
    previous, previous_errors = normalize_scope_snapshot(previous_snapshot)
    if previous_errors:
        return ["new analysis or report artifact has no valid prior scope snapshot"]

    for manifest in relevant:
        route = manifest["route"]
        reference = manifest.get("scope_ref")
        expected_kind = "analysis" if route == "analysis_execution" else "report"
        if (
            not isinstance(reference, dict)
            or set(reference) != {"kind", "id", "revision"}
            or reference.get("kind") != expected_kind
        ):
            errors.append(f"{manifest['path']}: scope_ref is not a valid {expected_kind} reference")
            continue
        identity = (reference.get("id"), reference.get("revision"))
        if route == "analysis_execution":
            prior_matches = [
                entry
                for entry in previous["analysis"].values()
                if scope_ref(entry) == identity and entry.get("current_status") == "ready"
            ]
            current_matches = [
                entry
                for entry in current["analysis"].values()
                if scope_ref(entry) == identity and entry.get("current_status") == "done"
            ]
        else:
            prior = previous["report"]
            completed = current["report"]
            prior_matches = [prior] if scope_ref(prior) == identity and prior.get("current_status") == "ready" else []
            current_matches = [completed] if scope_ref(completed) == identity and completed.get("current_status") == "done" else []
        if len(prior_matches) != 1:
            errors.append(f"{manifest['path']}: artifact scope was not exactly ready before approval")
        if len(current_matches) != 1:
            errors.append(f"{manifest['path']}: artifact scope is not exactly done after execution")
    return errors


def check_standard_scopes(turn_number, raw_snapshot, history):
    """Check the standard benchmark's fixed scope lifecycle."""
    snapshot, errors = normalize_scope_snapshot(raw_snapshot)
    if errors:
        return errors

    def one_with_status(value, status, label):
        matches = [
            (route, entry)
            for route, entry in value["analysis"].items()
            if entry.get("current_status") == status
        ]
        if len(matches) != 1:
            errors.append(f"{label} must contain exactly one {status} analysis scope")
            return None
        return matches[0]

    if turn_number <= 5:
        if snapshot["analysis"] or snapshot["report"] is not None:
            errors.append(f"turn {turn_number} must not create an analysis or report scope")
    elif turn_number == 6:
        ready = one_with_status(snapshot, "ready", "turn 6")
        if ready and ready[0] != "single_time_observational":
            errors.append("turn 6 ready scope must use the single_time_observational route")
        if len(snapshot["analysis"]) != 1:
            errors.append("turn 6 must contain exactly one analysis scope")
        if snapshot["report"] is not None:
            errors.append("turn 6 must not create a report scope")
    elif turn_number == 7:
        previous = history.get(6)
        if previous is None:
            errors.append("turn 7 cannot verify the ready turn 6 analysis scope")
        ready = one_with_status(previous, "ready", "turn 6") if previous else None
        completed = one_with_status(snapshot, "done", "turn 7")
        if len(snapshot["analysis"]) != 1:
            errors.append("turn 7 must contain exactly one analysis scope")
        if ready and completed:
            if (ready[0], scope_ref(ready[1]), ready[1].get("support")) != (
                completed[0], scope_ref(completed[1]), completed[1].get("support")
            ):
                errors.append("turn 7 must complete the exact turn 6 analysis scope")
        if snapshot["report"] is not None:
            errors.append("turn 7 must not create a report scope")
    elif turn_number == 8:
        previous = history.get(7)
        if previous is None:
            errors.append("turn 8 cannot verify the completed turn 7 analysis scope")
        else:
            completed = [
                entry
                for entry in previous["analysis"].values()
                if entry.get("current_status") == "done"
            ]
            if len(completed) != 1:
                errors.append("turn 7 must contain exactly one completed analysis scope")
            if snapshot["analysis"] != previous["analysis"]:
                errors.append("turn 8 must leave the completed analysis scope unchanged")
        if snapshot["report"] is not None:
            errors.append("turn 8 must not create a report scope")
    elif turn_number == 9:
        previous = history.get(8)
        if previous is None:
            errors.append("turn 9 cannot verify the turn 8 analysis scope")
        else:
            prior_routes = set(previous["analysis"])
            current_routes = set(snapshot["analysis"])
            if any(
                snapshot["analysis"].get(route) != entry
                for route, entry in previous["analysis"].items()
            ):
                errors.append("turn 9 must preserve completed analysis scopes")
            new_routes = current_routes - prior_routes
            if len(new_routes) != 1:
                errors.append("turn 9 must create exactly one new analysis scope")
            ready = [
                (route, entry)
                for route, entry in snapshot["analysis"].items()
                if entry.get("current_status") == "ready"
            ]
            if len(ready) != 1:
                errors.append("turn 9 must contain exactly one ready analysis scope")
            else:
                route, current = ready[0]
                previous_ids = {
                    entry["scope_id"] for entry in previous["analysis"].values()
                }
                if route not in new_routes:
                    errors.append("turn 9 ready scope must be the new analysis scope")
                if route != "descriptive_association":
                    errors.append("turn 9 ready scope must use the descriptive_association route")
                if current["scope_id"] in previous_ids:
                    errors.append("turn 9 must create a new analysis scope identity")
                if current.get("support") != "heterogeneous-effects":
                    errors.append("turn 9 ready scope must use heterogeneous-effects support")
        if snapshot["report"] is not None:
            errors.append("turn 9 must not create a report scope")
    elif turn_number == 10:
        previous = history.get(9)
        if previous is None:
            errors.append("turn 10 cannot verify the ready turn 9 analysis scope")
        ready = one_with_status(previous, "ready", "turn 9") if previous else None
        if ready:
            route, prior_entry = ready
            current_entry = snapshot["analysis"].get(route)
            if (
                not isinstance(current_entry, dict)
                or scope_ref(current_entry) != scope_ref(prior_entry)
                or current_entry.get("support") != prior_entry.get("support")
                or current_entry.get("current_status") != "done"
            ):
                errors.append("turn 10 must complete the exact turn 9 analysis scope")
            prior_other = {key: value for key, value in previous["analysis"].items() if key != route}
            current_other = {key: value for key, value in snapshot["analysis"].items() if key != route}
            if current_other != prior_other:
                errors.append("turn 10 must preserve previously completed analysis scopes")
        if snapshot["report"] is not None:
            errors.append("turn 10 must not create a report scope")
    elif turn_number == 11:
        previous = history.get(10)
        if previous is None or snapshot["analysis"] != previous["analysis"]:
            errors.append("turn 11 must preserve completed analysis scopes")
        report = snapshot["report"]
        if scope_ref(report) is None or report.get("current_status") != "ready":
            errors.append("turn 11 must create one ready report scope")
    elif turn_number == 12:
        previous = history.get(11)
        if previous is None or snapshot["analysis"] != previous["analysis"]:
            errors.append("turn 12 must preserve completed analysis scopes")
        prior_report = previous["report"] if previous else None
        report = snapshot["report"]
        if (
            not isinstance(report, dict)
            or scope_ref(report) != scope_ref(prior_report)
            or report.get("current_status") != "done"
        ):
            errors.append("turn 12 must complete the exact turn 11 report scope")
    elif turn_number == 13:
        previous = history.get(12)
        if previous is None or snapshot["analysis"] != previous["analysis"]:
            errors.append("turn 13 must preserve completed analysis scopes")
        prior_report = previous["report"] if previous else None
        report = snapshot["report"]
        if (
            not isinstance(report, dict)
            or scope_ref(report) is None
            or report.get("current_status") != "ready"
        ):
            errors.append("turn 13 must prepare one ready derivative communication scope")
        elif scope_ref(report) == scope_ref(prior_report):
            errors.append("turn 13 must create or revise the completed report scope")

    if not errors:
        history[turn_number] = snapshot
    return errors


def check_mechanical_edge_scopes(turn_number, raw_snapshot, history):
    """Check the fixed scope transitions exercised by mechanical-edge."""
    snapshot, errors = normalize_scope_snapshot(raw_snapshot)
    if errors:
        return errors
    analysis = snapshot["analysis"]
    report = snapshot["report"]

    def single_analysis(value, label, status):
        entries = value["analysis"]
        if len(entries) != 1:
            errors.append(f"{label} must have exactly one analysis scope")
            return None
        route, entry = next(iter(entries.items()))
        if scope_ref(entry) is None or entry.get("current_status") != status:
            errors.append(f"{label} analysis scope must be valid and {status}")
            return None
        return route, entry

    if turn_number <= 3:
        if analysis or report is not None:
            errors.append(f"turn {turn_number} must not create a scope")
    elif turn_number == 4:
        single_analysis(snapshot, "turn 4", "ready")
    elif turn_number == 5:
        if snapshot != history.get(4):
            errors.append("turn 5 must leave the original analysis scope unchanged")
    elif turn_number == 6:
        current = single_analysis(snapshot, "turn 6", "ready")
        original = single_analysis(history[4], "turn 4", "ready")
        if current:
            if current[0] != "single_time_observational":
                errors.append("turn 6 replacement must use the single_time_observational route")
            if current[1].get("support") != "heterogeneous-effects":
                errors.append("turn 6 replacement must use heterogeneous-effects support")
            if original and scope_ref(current[1]) == scope_ref(original[1]):
                errors.append("turn 6 must replace or revise the original analysis scope")
    elif turn_number == 7:
        if snapshot != history.get(6):
            errors.append("turn 7 stale approval must leave the replacement scope unchanged")
    elif turn_number == 8:
        current = single_analysis(snapshot, "turn 8", "done")
        replacement = single_analysis(history[6], "turn 6", "ready")
        if current and replacement:
            exact_current = current[0], scope_ref(current[1]), current[1].get("support")
            exact_replacement = replacement[0], scope_ref(replacement[1]), replacement[1].get("support")
            if exact_current != exact_replacement:
                errors.append("turn 8 must complete the exact replacement analysis scope")
    elif turn_number == 9:
        if snapshot != history.get(8):
            errors.append("turn 9 duplicate request must leave scope state unchanged")
    else:
        if analysis != history[8]["analysis"]:
            errors.append(f"turn {turn_number} must leave the completed analysis scope unchanged")
        if turn_number == 10:
            if scope_ref(report) is None or report.get("current_status") != "ready":
                errors.append("turn 10 must create one ready report scope")
        elif turn_number == 11:
            original = history[10]["report"]
            if scope_ref(report) is None or report.get("current_status") != "ready":
                errors.append("turn 11 must leave one ready replacement report scope")
            elif scope_ref(report) == scope_ref(original):
                errors.append("turn 11 must replace or revise the original report scope")
        elif turn_number == 12:
            if snapshot != history.get(11):
                errors.append("turn 12 stale approval must leave the replacement report scope unchanged")
        elif turn_number == 13:
            replacement = history[11]["report"]
            if scope_ref(report) != scope_ref(replacement) or report.get("current_status") != "done":
                errors.append("turn 13 must complete the exact replacement report scope")

    if turn_number <= 9 and report is not None:
        errors.append(f"turn {turn_number} must not create a report scope")
    if not errors:
        history[turn_number] = snapshot
    return errors


def is_within(path, root):
    try:
        return os.path.commonpath((str(path.resolve()), str(root.resolve()))) == str(root.resolve())
    except ValueError:
        return False


def is_rfc3339_utc(value):
    if not isinstance(value, str) or not RFC3339_UTC_PATTERN.fullmatch(value):
        return False
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").tzinfo == timezone.utc
    except ValueError:
        return False


def read_artifact_records(state_path):
    """Parse controller-generated artifact_records and fail closed on other layouts."""
    try:
        lines = state_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [], [f"cannot read project state artifact records ({exc})"]

    headers = [
        (index, line.partition(":")[2].strip())
        for index, line in enumerate(lines)
        if line.startswith("artifact_records:") and not line.startswith(" ")
    ]
    if len(headers) != 1:
        return [], ["project state must contain exactly one artifact_records section"]
    start, suffix = headers[0]
    if suffix == "[]":
        return [], []
    if suffix:
        return [], ["project state artifact_records must be a block list or []"]

    records = []
    current = None
    errors = []

    def finish_record():
        if current is None:
            return
        missing = sorted(ARTIFACT_RECORD_REQUIRED - set(current))
        unknown = sorted(set(current) - ARTIFACT_RECORD_KEYS)
        if missing:
            errors.append(f"project state artifact record is missing: {', '.join(missing)}")
        if unknown:
            errors.append(f"project state artifact record has unknown fields: {', '.join(unknown)}")
        if not missing and not unknown:
            records.append(current.copy())

    for line in lines[start + 1 :]:
        if line and not line.startswith(" "):
            break
        if not line.strip():
            continue
        if line.startswith("  - "):
            finish_record()
            current = {}
            field = line[4:]
        elif line.startswith("    ") and current is not None:
            field = line[4:]
        else:
            errors.append("project state artifact_records has unexpected indentation")
            continue
        key, separator, raw = field.partition(":")
        key = key.strip()
        raw = raw.strip()
        if not separator or not key or key in current:
            errors.append("project state artifact record has an invalid or duplicate field")
            continue
        if raw == "null":
            value = None
        else:
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                errors.append(f"project state artifact record field {key} is not a quoted scalar")
                continue
            if not isinstance(value, str):
                errors.append(f"project state artifact record field {key} is not a string or null")
                continue
        current[key] = value
    finish_record()

    operation_ids = set()
    for record in records:
        operation_id = record["operation_id"]
        if operation_id is not None:
            if not isinstance(operation_id, str) or not operation_id:
                errors.append("project state artifact operation_id is invalid")
            elif operation_id in operation_ids:
                errors.append("project state artifact operation_id is duplicated")
            else:
                operation_ids.add(operation_id)
        if record["route"] not in ARTIFACT_ROUTES:
            errors.append(f"project state artifact route is invalid: {record['route']}")
        if not isinstance(record["location"], str) or not record["location"].startswith("output/"):
            errors.append("project state artifact location must be under output/")
        if not isinstance(record["summary"], str) or not record["summary"].strip():
            errors.append("project state artifact summary must be nonempty")
    return records, errors


def inspect_html_links(path, workdir):
    parser, parse_error = parse_html(path)
    if parse_error:
        return [parse_error]

    errors = []
    for value in sorted(parser.duplicate_ids):
        errors.append(f"duplicate HTML id ({value})")
    for attribute, reference in parser.references:
        value = reference.strip()
        if not value:
            continue
        kind = "link" if attribute == "href" else "source"
        if WINDOWS_ABSOLUTE_REFERENCE.match(value):
            errors.append(f"nonportable local HTML {kind} reference ({value})")
            continue
        try:
            parsed = urlsplit(value)
        except ValueError:
            errors.append(f"malformed HTML {kind} reference ({value})")
            continue
        if parsed.scheme.lower() == "file":
            errors.append(f"nonportable local HTML {kind} reference ({value})")
            continue
        if parsed.scheme or parsed.netloc:
            continue
        if not parsed.path:
            fragment = unquote(parsed.fragment)
            if fragment and fragment not in parser.ids:
                errors.append(f"missing HTML fragment target ({value})")
            continue
        try:
            target = (path.parent / Path(unquote(parsed.path))).resolve()
        except (OSError, RuntimeError, ValueError):
            errors.append(f"malformed HTML {kind} reference ({value})")
            continue
        if not is_within(target, workdir):
            errors.append(f"HTML {kind} is outside the project ({value})")
        elif not target.exists():
            errors.append(f"missing project-local HTML {kind} target ({value})")
        elif parsed.fragment and target.suffix.lower() in (".html", ".htm"):
            fragment = unquote(parsed.fragment)
            target_parser = parser
            if target != path.resolve():
                target_parser, parse_error = parse_html(target)
                if parse_error:
                    errors.append(f"cannot inspect HTML fragment target ({value}: {parse_error})")
                    continue
            if fragment not in target_parser.ids:
                errors.append(f"missing HTML fragment target ({value})")
    return errors


def inspect_artifacts(workdir, expected, previous=None):
    root = workdir.resolve()
    output_dir = workdir / "output"
    state_path = workdir / "project_state.yaml"
    errors = []
    manifest_paths = []
    output_files = set()
    if output_dir.is_symlink():
        errors.append("output directory must not be a symlink")
    elif output_dir.is_dir():
        for candidate in output_dir.rglob("*"):
            if candidate.is_symlink():
                relative = candidate.relative_to(workdir).as_posix()
                errors.append(f"symlink output entries are not allowed: {relative}")
                continue
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if not is_within(resolved, root):
                errors.append(f"output file is outside the project: {candidate}")
                continue
            output_files.add(resolved)
            if candidate.name == "artifact-manifest.json" or candidate.name.endswith(".manifest.json"):
                manifest_paths.append(resolved)
    manifest_paths = sorted(set(manifest_paths))
    state_records = []
    if state_path.is_file():
        state_records, state_errors = read_artifact_records(state_path)
        errors.extend(state_errors)
    elif manifest_paths:
        errors.append("artifact manifests exist without project_state.yaml")
    records_by_operation = {
        record["operation_id"]: record
        for record in state_records
        if isinstance(record.get("operation_id"), str) and record["operation_id"]
    }
    manifests = []
    covered_files = set(manifest_paths)
    operation_ids = set()
    hashes = {}
    previous = previous if isinstance(previous, dict) else {}
    previous_manifest_paths = set(previous.get("manifest_paths", []))
    previous_hashes = previous.get("hashes", {})
    if not isinstance(previous_hashes, dict):
        previous_hashes = {}

    for path in manifest_paths:
        relative = path.relative_to(root).as_posix()
        try:
            hashes[relative] = sha256_file(path)
        except OSError as exc:
            errors.append(f"{relative}: cannot hash manifest ({exc})")
        location = (
            path.parent.relative_to(root).as_posix()
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
        missing_keys = sorted(MANIFEST_KEYS - set(manifest))
        unknown_keys = sorted(set(manifest) - MANIFEST_KEYS)
        if missing_keys:
            errors.append(f"{relative}: manifest is missing: {', '.join(missing_keys)}")
        if unknown_keys:
            errors.append(f"{relative}: manifest has unknown fields: {', '.join(unknown_keys)}")
        if manifest.get("schema_version") != 1:
            errors.append(f"{relative}: unsupported manifest schema_version")
        route = manifest.get("route")
        operation_id = manifest.get("operation_id")
        files = manifest.get("files")
        scope_reference = manifest.get("scope_ref")
        summary = manifest.get("summary")
        if route not in ARTIFACT_ROUTES:
            errors.append(f"{relative}: route is invalid")
        if not isinstance(operation_id, str) or not operation_id:
            errors.append(f"{relative}: operation_id is missing")
        elif not UUID_PATTERN.fullmatch(operation_id):
            errors.append(f"{relative}: operation_id is not a UUID")
        elif operation_id in operation_ids:
            errors.append(f"{relative}: operation_id is duplicated across manifests")
        else:
            operation_ids.add(operation_id)
            record = records_by_operation.get(operation_id)
            if record is None:
                errors.append(f"{relative}: operation_id is not exactly registered in project state")
            else:
                if record.get("route") != route:
                    errors.append(f"{relative}: route does not match its project state record")
                if record.get("location") != location:
                    errors.append(f"{relative}: location does not match its project state record")
                record_summary = record.get("summary")
                if (
                    not isinstance(summary, str)
                    or not isinstance(record_summary, str)
                    or record_summary.strip() != summary.strip()
                ):
                    errors.append(f"{relative}: summary does not match its project state record")
        expected_scope_kind = {
            "analysis_execution": "analysis",
            "report_writer": "report",
        }.get(route)
        if expected_scope_kind is None:
            if scope_reference is not None:
                errors.append(f"{relative}: scope_ref must be null for {route}")
        elif (
            not isinstance(scope_reference, dict)
            or set(scope_reference) != {"kind", "id", "revision"}
            or scope_reference.get("kind") != expected_scope_kind
            or not isinstance(scope_reference.get("id"), str)
            or not UUID_PATTERN.fullmatch(scope_reference.get("id", ""))
            or not isinstance(scope_reference.get("revision"), int)
            or isinstance(scope_reference.get("revision"), bool)
            or scope_reference.get("revision") < 1
        ):
            errors.append(f"{relative}: scope_ref is invalid for {route}")
        if not is_rfc3339_utc(manifest.get("completed_at")):
            errors.append(f"{relative}: completed_at must be RFC3339 UTC")
        if not isinstance(summary, str) or not summary.strip():
            errors.append(f"{relative}: summary must be nonempty")
        if not isinstance(files, list) or not files or not all(
            isinstance(item, str) and item.strip() for item in files
        ):
            errors.append(f"{relative}: files must be a nonempty string list")
            files = []
        resolved_files = []
        resolved_targets = []
        nonempty_deliverable = False
        reserved = (root / Path(location)).resolve()
        directory_manifest = path.name == "artifact-manifest.json"
        for item in files:
            try:
                if (
                    Path(item).is_absolute()
                    or WINDOWS_ABSOLUTE_REFERENCE.match(item)
                    or not item.replace("\\", "/").startswith("output/")
                ):
                    errors.append(f"{relative}: listed file is not a relative output path ({item})")
                    continue
                candidate = workdir / Path(item)
                target = candidate.resolve()
                candidate_is_symlink = candidate.is_symlink()
            except (OSError, RuntimeError, ValueError) as exc:
                errors.append(f"{relative}: listed file path is invalid ({item}: {exc})")
                continue
            if candidate_is_symlink:
                errors.append(f"{relative}: listed file must not be a symlink ({item})")
            elif not is_within(target, root):
                errors.append(f"{relative}: listed file is outside the project ({item})")
            elif not target.is_file():
                errors.append(f"{relative}: listed file is missing ({item})")
            else:
                covered_files.add(target)
                if target == path:
                    errors.append(f"{relative}: manifest must not list itself as a deliverable")
                elif directory_manifest and not is_within(target, reserved):
                    errors.append(f"{relative}: listed file is outside the reserved location ({item})")
                elif not directory_manifest and target != reserved:
                    errors.append(f"{relative}: listed file is not the reserved file ({item})")
                else:
                    resolved_files.append(item)
                    resolved_targets.append((item, target))
                    try:
                        nonempty_deliverable = nonempty_deliverable or target.stat().st_size > 0
                    except OSError as exc:
                        errors.append(f"{relative}: cannot inspect listed file {item} ({exc})")
        if not nonempty_deliverable:
            errors.append(f"{relative}: manifest has no nonempty deliverable")
        html_targets = [
            (item, target)
            for item, target in resolved_targets
            if target.suffix.lower() == ".html"
        ]
        if route == "report_writer" and not html_targets:
            errors.append(f"{relative}: report manifest does not contain an HTML file")
        for item, target in resolved_targets:
            relative_target = target.relative_to(root).as_posix()
            try:
                hashes[relative_target] = sha256_file(target)
            except OSError as exc:
                errors.append(f"{relative}: cannot hash listed file {item} ({exc})")
            if target.suffix.lower() == ".html":
                try:
                    if target.stat().st_size == 0:
                        errors.append(f"{relative}: report HTML file is empty ({item})")
                except OSError as exc:
                    errors.append(f"{relative}: cannot inspect report HTML file {item} ({exc})")
                for error in inspect_html_links(target, workdir):
                    errors.append(f"{relative}: {item}: {error}")
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

    for operation_id, record in records_by_operation.items():
        if operation_id not in operation_ids:
            errors.append(
                f"project state artifact {record['location']} has no matching completion manifest"
            )

    orphaned = sorted(path.relative_to(root).as_posix() for path in output_files - covered_files)
    if orphaned:
        errors.append(f"unlisted output files: {', '.join(orphaned)}")

    current_manifest_paths = {
        path.relative_to(root).as_posix() for path in manifest_paths
    }
    new_manifest_paths = sorted(current_manifest_paths - previous_manifest_paths)
    removed_manifest_paths = sorted(previous_manifest_paths - current_manifest_paths)
    if removed_manifest_paths:
        errors.append(f"previous artifact manifests disappeared: {', '.join(removed_manifest_paths)}")
    for relative, digest in sorted(previous_hashes.items()):
        current = hashes.get(relative)
        if current is None:
            errors.append(f"previous artifact file is missing or unlisted: {relative}")
        elif current != digest:
            errors.append(f"previous artifact file changed: {relative}")

    counts = {}
    for manifest in manifests:
        route = manifest.get("route")
        if isinstance(route, str):
            counts[route] = counts.get(route, 0) + 1
    for route, count in expected.items():
        if route == "new":
            continue
        actual = len(manifests) if route == "total" else counts.get(route, 0)
        if actual != count:
            errors.append(f"expected {count} {route} artifact(s), found {actual}")
    if "new" in expected and len(new_manifest_paths) != expected["new"]:
        errors.append(
            f"expected {expected['new']} new artifact(s), found {len(new_manifest_paths)}"
        )
    new_manifest_set = set(new_manifest_paths)
    return {
        "ok": not errors,
        "expected": expected,
        "manifest_count": len(manifest_paths),
        "new_count": len(new_manifest_paths),
        "counts": counts,
        "manifests": manifests,
        "new_manifests": [item for item in manifests if item["path"] in new_manifest_set],
        "manifest_paths": sorted(current_manifest_paths),
        "hashes": hashes,
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


def runtime_metadata(response):
    model_usage = response.get("modelUsage")
    models = (
        sorted(model for model in model_usage if isinstance(model, str))
        if isinstance(model_usage, dict)
        else []
    )
    fast_mode_state = response.get("fast_mode_state")
    return {
        "models": models,
        "fast_mode_state": fast_mode_state if isinstance(fast_mode_state, str) else None,
    }


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
                record.get("response") or "_No completed response._",
                "",
            ]
        )
        if record.get("failure_phase"):
            parts.extend(
                [
                    "### Test failure",
                    "",
                    f"Phase: `{record['failure_phase']}`",
                    *(
                        [f"Reason: {record['failure_reason']}"]
                        if record.get("failure_reason")
                        else []
                    ),
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
    if output_path.is_dir() and not output_path.is_symlink():
        shutil.copytree(output_path, destination / "output", symlinks=True)


def check_status(check):
    if not isinstance(check, dict) or not check.get("applicable", True):
        return "not_applicable"
    return "pass" if check.get("ok") else "fail"


def aggregate_check(turns, key, expected_turns):
    checks = [turn.get(key) for turn in turns if isinstance(turn.get(key), dict)]
    applicable = [check for check in checks if check.get("applicable", True)]
    if not applicable:
        return "not_applicable"
    if any(not check.get("ok") for check in applicable):
        return "fail"
    if len(turns) != expected_turns or len(checks) != expected_turns:
        return "incomplete"
    return "pass"


def initial_workflow_assessment(test_id, automated_status):
    required = test_id in MANUAL_RATINGS
    if not required:
        status = "not_required"
    elif automated_status == "pass":
        status = "pending"
    else:
        status = "blocked"
    return {
        "required": required,
        "status": status,
        "rating": None,
        "method": "manual" if required else None,
        "reference": "test-reference.md" if required else None,
        "notes_file": None,
        "notes_sha256": None,
        "assessed_at": None,
    }


def derive_final_result(automated_status, workflow):
    if automated_status != "pass":
        return "fail"
    if not workflow["required"]:
        return "pass"
    if workflow["status"] != "complete":
        return "pending"
    rating = workflow["rating"]
    if rating in ("pass", "safe"):
        return "pass"
    if rating == "weak":
        return "weak"
    return "fail"


def final_result_exit_code(status):
    if status == "pass":
        return 0
    if status == "pending":
        return EXIT_PENDING
    return 1


def build_summary(test_id, expected_turns, records, abort_reason, target):
    turn_summaries = []
    for record in records:
        shell = record.get("shell")
        state = record.get("state")
        scope = record.get("scope")
        artifacts = record.get("artifacts")
        reached_checks = all(isinstance(value, dict) for value in (shell, state, scope, artifacts))
        passed = reached_checks and all(
            not value.get("applicable", True) or value.get("ok")
            for value in (shell, state, scope, artifacts)
        )
        turn_summaries.append(
            {
                "turn": record["turn"],
                "label": record["label"],
                "outcome": "pass" if passed else record.get("outcome", "not_evaluated"),
                "failure_phase": record.get("failure_phase"),
                "failure_reason": record.get("failure_reason"),
                "session_id": record.get("session_id"),
                "duration_seconds": record.get("duration_seconds"),
                "input_tokens": record.get("input_tokens", 0),
                "output_tokens": record.get("output_tokens", 0),
                "response_shell": shell,
                "state_protocol": state,
                "scope_identity": scope,
                "artifacts": None if artifacts is None else {
                    "ok": artifacts.get("ok", False),
                    "expected": artifacts.get("expected"),
                    "new_count": artifacts.get("new_count"),
                    "counts": artifacts.get("counts"),
                    "errors": artifacts.get("errors", []),
                },
            }
        )

    attempted_turns = len(records)
    response_turns = sum(record.get("response_received", False) for record in records)
    accepted_response_turns = sum(record.get("response_accepted", False) for record in records)
    validated_turns = sum(turn["outcome"] == "pass" for turn in turn_summaries)
    run_integrity = (
        "pass"
        if abort_reason is None and attempted_turns == accepted_response_turns == expected_turns
        else "fail"
    )
    categories = {
        "run_integrity": run_integrity,
        "response_shell": aggregate_check(turn_summaries, "response_shell", expected_turns),
        "state_protocol": aggregate_check(turn_summaries, "state_protocol", expected_turns),
        "scope_identity": aggregate_check(turn_summaries, "scope_identity", expected_turns),
        "artifacts": aggregate_check(turn_summaries, "artifacts", expected_turns),
    }
    automated_pass = run_integrity == "pass" and all(
        status in ("pass", "not_applicable") for status in categories.values()
    ) and validated_turns == expected_turns
    automated_status = "pass" if automated_pass else "fail"
    workflow = initial_workflow_assessment(test_id, automated_status)

    total_input = sum(turn["input_tokens"] for turn in turn_summaries)
    total_output = sum(turn["output_tokens"] for turn in turn_summaries)
    models = sorted({model for record in records for model in record.get("models", [])})
    fast_mode_states = sorted(
        {
            record["fast_mode_state"]
            for record in records
            if isinstance(record.get("fast_mode_state"), str)
        }
    )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "test": test_id,
        "test_suite": {
            "version": target["test_suite_version"],
            "runtime_sha256": target["test_suite_runtime_sha256"],
            "case_sha256": target["test_case_sha256"],
        },
        "target": {
            "causal_consultant_version": target["causal_consultant_version"],
            "statectl_sha256": target["statectl_sha256"],
            "skill_runtime_sha256": target["skill_runtime_sha256"],
        },
        "input_data": target.get("input_data"),
        "runtime": {
            "models": models,
            "fast_mode_states": fast_mode_states,
        },
        "attempted_turns": attempted_turns,
        "response_turns": response_turns,
        "accepted_response_turns": accepted_response_turns,
        "validated_turns": validated_turns,
        "expected_turns": expected_turns,
        "automated_checks": {
            "status": automated_status,
            "categories": categories,
        },
        "workflow_assessment": workflow,
        "final_result": {"status": derive_final_result(automated_status, workflow)},
        "review_evidence": None,
        "scientific_quality": "not_evaluated",
        "abort_reason": abort_reason,
        "generated_at": utc_now(),
        "tokens": {
            "input": total_input,
            "output": total_output,
            "total": total_input + total_output,
        },
        "turns": turn_summaries,
    }


def summary_check_cell(check):
    status = check_status(check)
    return {"pass": "PASS", "fail": "FAIL", "not_applicable": "N/A"}[status]


def render_summary_markdown(summary):
    workflow = summary["workflow_assessment"]
    lines = [
        f"# {summary['test']} test summary",
        "",
        f"Final result: **{summary['final_result']['status'].upper()}**",
        f"Automated checks: **{summary['automated_checks']['status'].upper()}**",
        f"Workflow assessment: **{workflow['status'].upper()}**",
    ]
    if workflow.get("reference"):
        lines.append(f"Assessment rubric: `{workflow['reference']}`")
    if workflow.get("rating"):
        lines.append(f"Workflow rating: **{workflow['rating'].upper()}**")
    if workflow.get("notes_file"):
        lines.append(f"Assessment notes: `{workflow['notes_file']}`")
    if workflow.get("notes_sha256"):
        lines.append(f"Assessment notes SHA-256: `{workflow['notes_sha256']}`")
    evidence = summary.get("review_evidence")
    if isinstance(evidence, dict):
        lines.append(
            f"Review evidence: {evidence['file_count']} files, SHA-256 `{evidence['sha256']}`"
        )
    lines.extend(
        [
            f"Turns: {summary['attempted_turns']} attempted, {summary['response_turns']} with responses, "
            f"{summary['accepted_response_turns']} accepted, {summary['validated_turns']} validated, "
            f"{summary['expected_turns']} expected",
            f"Test suite: interactive-test-cc v{summary['test_suite']['version']} "
            f"(runtime SHA-256: `{summary['test_suite']['runtime_sha256']}`; "
            f"case SHA-256: `{summary['test_suite']['case_sha256']}`)",
            f"Target: causal-consultant v{summary['target']['causal_consultant_version']} "
            f"(`statectl` SHA-256: `{summary['target']['statectl_sha256']}`; "
            f"skill runtime SHA-256: `{summary['target']['skill_runtime_sha256']}`)",
            f"Runtime: models {', '.join(summary['runtime']['models']) if summary['runtime']['models'] else 'unknown'}; "
            f"fast mode {', '.join(summary['runtime']['fast_mode_states']) if summary['runtime']['fast_mode_states'] else 'unknown'}",
        ]
    )
    if summary.get("input_data"):
        data = summary["input_data"]
        lines.append(
            f"Input: `{data['filename']}`, {data['rows']} rows, SHA-256 `{data['sha256']}`, "
            f"canonical SHA-256 `{data['canonical_sha256']}`"
        )
    if summary.get("abort_reason"):
        lines.append(f"Abort reason: {summary['abort_reason']}")

    categories = summary["automated_checks"]["categories"]
    lines.extend(
        [
            "",
            "Automated categories: "
            + ", ".join(f"{name.replace('_', ' ')}={status.upper()}" for name, status in categories.items()),
            "",
            "| Turn | Label | Outcome | Duration | Tokens | Shell | State | Scope | Artifacts |",
            "|---:|---|---|---:|---:|---|---|---|---|",
        ]
    )
    for turn in summary["turns"]:
        duration = f"{turn['duration_seconds']:.1f}s" if isinstance(turn.get("duration_seconds"), (int, float)) else "N/A"
        tokens = turn.get("input_tokens", 0) + turn.get("output_tokens", 0)
        lines.append(
            f"| {turn['turn']} | {turn['label']} | {turn['outcome'].upper()} | {duration} | {tokens} | "
            f"{summary_check_cell(turn.get('response_shell'))} | "
            f"{summary_check_cell(turn.get('state_protocol'))} | "
            f"{summary_check_cell(turn.get('scope_identity'))} | "
            f"{summary_check_cell(turn.get('artifacts'))} |"
        )

    failures = []
    if summary.get("abort_reason"):
        failures.append(f"Run: {summary['abort_reason']}")
    for turn in summary["turns"]:
        for label, key in (
            ("response shell", "response_shell"),
            ("state protocol", "state_protocol"),
            ("scope identity", "scope_identity"),
            ("artifacts", "artifacts"),
        ):
            check = turn.get(key)
            for error in check.get("errors", []) if isinstance(check, dict) else []:
                failures.append(f"Turn {turn['turn']} {label}: {error}")
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in failures[:20])
        if len(failures) > 20:
            lines.append(f"- {len(failures) - 20} additional failure(s) are recorded in `summary.json`.")
    return "\n".join(lines) + "\n"


def stage_text(path, content):
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    return temporary


def write_summary_files(results_dir, summary):
    json_path = results_dir / "summary.json"
    markdown_path = results_dir / "summary.md"
    json_temporary = None
    markdown_temporary = None
    try:
        json_temporary = stage_text(
            json_path,
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        )
        markdown_temporary = stage_text(markdown_path, render_summary_markdown(summary))
        os.replace(markdown_temporary, markdown_path)
        markdown_temporary = None
        os.replace(json_temporary, json_path)
        json_temporary = None
    except OSError as exc:
        raise RunError(f"cannot write summary files: {exc}") from exc
    finally:
        for temporary in (json_temporary, markdown_temporary):
            if temporary is not None:
                try:
                    temporary.unlink()
                except OSError:
                    pass


def write_summary(results_dir, test_id, expected_turns, records, abort_reason, target):
    summary = build_summary(test_id, expected_turns, records, abort_reason, target)
    if summary["workflow_assessment"]["status"] == "pending":
        summary["review_evidence"] = capture_review_evidence(results_dir)
    write_summary_files(results_dir, summary)
    return summary


def assess_results(results_dir, rating, notes_file):
    results_dir = results_dir.expanduser().resolve()
    summary_path = results_dir / "summary.json"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunError(f"cannot read summary.json: {exc}") from exc
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        raise RunError(f"summary.json must use schema_version {SUMMARY_SCHEMA_VERSION}")
    test_id = summary.get("test")
    allowed = MANUAL_RATINGS.get(test_id)
    workflow = summary.get("workflow_assessment")
    if allowed is None or not isinstance(workflow, dict) or not workflow.get("required"):
        raise RunError(f"{test_id} does not require a workflow assessment")
    if summary.get("automated_checks", {}).get("status") != "pass":
        raise RunError("workflow assessment is blocked because automated checks did not pass")
    if workflow.get("status") != "pending":
        raise RunError("workflow assessment is not pending")
    if rating not in allowed:
        raise RunError(f"invalid {test_id} rating: {rating}; expected one of {', '.join(sorted(allowed))}")

    notes = notes_file.expanduser().resolve()
    if not is_within(notes, results_dir) or not notes.is_file():
        raise RunError("assessment notes must be a file inside results-dir")
    if notes in (summary_path, results_dir / "summary.md"):
        raise RunError("assessment notes must not overwrite a generated summary")
    notes_relative = notes.relative_to(results_dir).as_posix()
    evidence = summary.get("review_evidence")
    if not isinstance(evidence, dict) or notes_relative in evidence.get("paths", []):
        raise RunError("assessment notes must be separate from the saved review evidence")
    current_evidence = capture_review_evidence(results_dir, {notes_relative})
    if current_evidence != evidence:
        raise RunError("saved review evidence changed after the automated run")
    try:
        notes_bytes = notes.read_bytes()
        if not notes_bytes.decode("utf-8").strip():
            raise RunError("assessment notes file is empty")
    except (OSError, UnicodeError) as exc:
        raise RunError(f"cannot read assessment notes: {exc}") from exc

    workflow.update(
        {
            "status": "complete",
            "rating": rating,
            "notes_file": notes_relative,
            "notes_sha256": hashlib.sha256(notes_bytes).hexdigest(),
            "assessed_at": utc_now(),
        }
    )
    summary["final_result"] = {
        "status": derive_final_result(summary["automated_checks"]["status"], workflow)
    }
    write_summary_files(results_dir, summary)
    return summary["final_result"]["status"]


def run_test(args, case):
    workdir = args.workdir.expanduser().resolve()
    results_dir = args.results_dir.expanduser().resolve()
    statectl = args.statectl.expanduser().resolve()
    target = preflight(args.test, case, workdir, results_dir, statectl, args.node)
    write_json(results_dir / "test-case.json", {"test": args.test, "case": case})
    shutil.copyfile(ROOT / "references" / f"{args.test}.md", results_dir / "test-reference.md")

    records = []
    session_id = None
    project_id = None
    revision = None
    manifest_count = 0
    scope_history = {}
    previous_scope_snapshot = None
    previous_artifacts = None
    abort_reason = None
    print(f"Running {args.test}: {len(case['turns'])} turns")

    for number, turn in enumerate(case["turns"], 1):
        record = {
            "turn": number,
            "label": turn["label"],
            "prompt": turn["prompt"],
            "response": None,
            "response_received": False,
            "response_accepted": False,
            "session_id": session_id,
            "duration_seconds": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "models": [],
            "fast_mode_state": None,
            "shell": None,
            "state": None,
            "scope": None,
            "artifacts": None,
            "outcome": "not_evaluated",
            "failure_phase": None,
            "failure_reason": None,
        }
        try:
            validate_runtime_provenance(target)
        except RunError as exc:
            abort_reason = f"turn {number} target validation failed before prompt: {exc}"
            break
        records.append(record)
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
            duration = time.monotonic() - started
            record["duration_seconds"] = duration
            record["outcome"] = "fail"
            record["failure_phase"] = "transport_start"
            write_json(
                results_dir / f"turn-{number:02d}.transport.json",
                {"returncode": None, "stdout": "", "stderr": str(exc), "duration_seconds": duration},
            )
            abort_reason = f"turn {number} transport could not start: {exc}"
            record["failure_reason"] = abort_reason
            break
        duration = time.monotonic() - started
        record["duration_seconds"] = duration
        write_json(
            results_dir / f"turn-{number:02d}.transport.json",
            {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "duration_seconds": duration,
            },
        )
        response = None
        try:
            candidate = json.loads(response_path.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                response = candidate
                record["response_received"] = True
                if isinstance(candidate.get("result"), str):
                    record["response"] = candidate["result"]
        except (OSError, json.JSONDecodeError):
            pass
        try:
            validate_runtime_provenance(target)
        except RunError as exc:
            abort_reason = f"turn {number} target validation failed after response: {exc}"
            record["outcome"] = "fail"
            record["failure_phase"] = "post_response_provenance"
            record["failure_reason"] = abort_reason
            break
        if completed.stderr.strip():
            print(completed.stderr.strip())
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else f"exit {completed.returncode}"
            abort_reason = f"turn {number} transport failed: {detail}"
            record["outcome"] = "fail"
            record["failure_phase"] = "transport"
            record["failure_reason"] = abort_reason
            break

        if response is None:
            abort_reason = f"turn {number} response JSON failed"
            record["outcome"] = "fail"
            record["failure_phase"] = "response_json"
            record["failure_reason"] = abort_reason
            break
        if not isinstance(response, dict) or response.get("is_error"):
            abort_reason = f"turn {number} returned an error response"
            record["outcome"] = "fail"
            record["failure_phase"] = "response_error"
            record["failure_reason"] = abort_reason
            break
        response_text = response.get("result")
        returned_session = response.get("session_id")
        if not isinstance(response_text, str) or not response_text.strip():
            abort_reason = f"turn {number} response text is missing"
            record["outcome"] = "fail"
            record["failure_phase"] = "response_text"
            record["failure_reason"] = abort_reason
            break
        if not isinstance(returned_session, str) or not returned_session:
            abort_reason = f"turn {number} session_id is missing"
            record["outcome"] = "fail"
            record["failure_phase"] = "session_identity"
            record["failure_reason"] = abort_reason
            break
        if session_id is not None and returned_session != session_id:
            abort_reason = f"turn {number} resumed a different session"
            record["outcome"] = "fail"
            record["failure_phase"] = "session_identity"
            record["failure_reason"] = abort_reason
            break
        session_id = returned_session
        runtime = runtime_metadata(response)
        input_tokens, output_tokens = token_usage(response)
        record.update(
            {
                "response": response_text,
                "response_accepted": True,
                "session_id": session_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "models": runtime["models"],
                "fast_mode_state": runtime["fast_mode_state"],
            }
        )

        shell = check_headings(response_text)
        artifacts = inspect_artifacts(workdir, turn["artifacts"], previous_artifacts)
        try:
            validator, state_errors = validate_state(
                statectl,
                args.node,
                workdir,
                project_id,
                revision,
                manifest_count,
                artifacts["manifest_count"],
            )
        except RunError as exc:
            abort_reason = f"turn {number} state validation failed: {exc}"
            record.update(
                {
                    "shell": shell,
                    "state": {"ok": False, "errors": [str(exc)]},
                    "artifacts": artifacts,
                    "outcome": "fail",
                    "failure_phase": "state_validation",
                    "failure_reason": abort_reason,
                }
            )
            write_json(results_dir / f"artifacts-turn-{number:02d}.json", artifacts)
            break
        scope_errors = check_new_manifest_scope_bindings(
            validator.get("scope_snapshot"),
            previous_scope_snapshot,
            artifacts,
        )
        scope_applicable = args.test in ("standard", "mechanical-edge") or bool(
            [
                manifest
                for manifest in artifacts.get("new_manifests", [])
                if manifest.get("route") in ("analysis_execution", "report_writer")
            ]
        )
        if args.test == "standard":
            scope_errors.extend(
                check_standard_scopes(
                    number,
                    validator.get("scope_snapshot"),
                    scope_history,
                )
            )
        elif args.test == "mechanical-edge":
            scope_errors.extend(
                check_mechanical_edge_scopes(
                    number,
                    validator.get("scope_snapshot"),
                    scope_history,
                )
            )
        state = {"ok": not state_errors, "errors": state_errors, "validator": validator}
        scope = {"ok": not scope_errors, "applicable": scope_applicable, "errors": scope_errors}
        nonfatal_errors = []
        if not shell["ok"]:
            nonfatal_errors.extend(
                f"response shell: {error}" for error in (shell.get("errors") or ["check failed"])
            )
        if not artifacts["ok"]:
            nonfatal_errors.extend(
                f"artifacts: {error}" for error in (artifacts.get("errors") or ["check failed"])
            )
        record.update(
            {
                "shell": shell,
                "state": state,
                "scope": scope,
                "artifacts": artifacts,
                "outcome": "pass" if shell["ok"] and state["ok"] and scope["ok"] and artifacts["ok"] else "fail",
                "failure_phase": "turn_validation" if nonfatal_errors else None,
                "failure_reason": "; ".join(nonfatal_errors) if nonfatal_errors else None,
            }
        )
        write_json(results_dir / f"artifacts-turn-{number:02d}.json", artifacts)
        snapshot_state(workdir, results_dir, number, validator)
        if not state["ok"]:
            abort_reason = f"turn {number} ended outside a valid idle state: {'; '.join(state_errors)}"
            record["failure_phase"] = "state_protocol"
            record["failure_reason"] = abort_reason
            break
        if not scope["ok"]:
            abort_reason = f"turn {number} violated the scope identity contract: {'; '.join(scope_errors)}"
            record["failure_phase"] = "scope_identity"
            record["failure_reason"] = abort_reason
            break

        project_id = validator["project_id"]
        revision = validator["revision"]
        manifest_count = artifacts["manifest_count"]
        previous_scope_snapshot = validator.get("scope_snapshot")
        previous_artifacts = artifacts
        print(
            f"  shell={'PASS' if shell['ok'] else 'FAIL'} "
            f"state=PASS scope={'PASS' if scope['ok'] else 'FAIL'} "
            f"artifacts={'PASS' if artifacts['ok'] else 'FAIL'} revision={revision}"
        )

    write_conversation(results_dir, records)
    copy_playground(workdir, results_dir)
    summary = write_summary(results_dir, args.test, len(case["turns"]), records, abort_reason, target)
    if abort_reason:
        print(f"ABORTED: {abort_reason}", file=sys.stderr)
    automated_status = summary["automated_checks"]["status"]
    workflow_status = summary["workflow_assessment"]["status"]
    final_status = summary["final_result"]["status"]
    print(f"Automated checks: {automated_status.upper()}")
    print(f"Workflow assessment: {workflow_status.upper()}")
    print(f"Final result: {final_status.upper()}")
    return final_result_exit_code(final_status)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", choices=TEST_IDS)
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--assess-results", type=Path)
    parser.add_argument("--rating")
    parser.add_argument("--notes-file", type=Path)
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
        if args.assess_results is not None:
            if args.rating is None or args.notes_file is None:
                parser.error("--assess-results requires --rating and --notes-file")
            if (
                any(value is not None for value in (args.test, args.workdir, args.results_dir))
                or args.dry_run
                or args.list_tests
            ):
                parser.error("assessment mode cannot be combined with live-run or dry-run options")
            final_status = assess_results(
                args.assess_results.expanduser().resolve(),
                args.rating,
                args.notes_file,
            )
            print(f"Final result: {final_status.upper()}")
            return final_result_exit_code(final_status)
        if args.rating is not None or args.notes_file is not None:
            parser.error("--rating and --notes-file require --assess-results")
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
