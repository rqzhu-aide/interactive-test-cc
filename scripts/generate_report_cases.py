"""Maintain two full-report editions without changing their frozen base cases.

Standard library only. The base manifest identities are intentional: if a base
changes, review and version the adaptation instead of silently inheriting a new
world. Each generated child is standalone and retains the base numerical oracle.
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_VERSION = "1.0.0"
SUITE_VERSION = "7.0.3"
LIMITS = {"consultant_turns": 24, "active_seconds": 14400, "elapsed_seconds": 21600}
BASES = {
    "college-policy-report-v7": {
        "id": "college-policy-v7", "version": "1.1.0",
        "sha256": "e24226536d456d8baeee101ef7f687232d903b1ea18a327d5bcccd80af8bbece",
    },
    "investigation-allocation-report-v7": {
        "id": "investigation-allocation-recoverable-v7", "version": "1.0.1",
        "sha256": "a7c328f835b05b073b023e897a90b2e4f2be853412d1780f990b14edca3cf4db",
    },
}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def criterion(key, statement):
    return {"id": key, "required": True, "rule": statement}


def rule(key, condition, action):
    return {"rule_id": key, "condition": condition, "action": action,
            "fact_ids": ["f-report-deliverable"], "source_ids": []}


REPORT_GOAL = (
    "Continue the original policy consultation through consequential attainable investigation, "
    "scientifically supported analysis with saved reproducible results, and a complete saved local "
    "consultant report for the education board. The report should explain the answer and evidence "
    "status, how it was reached, results and uncertainty, limitations, practical recommendations, "
    "sources and a short technical appendix for reproducibility. A complete report may honestly "
    "conclude that the causal effect is not identified and present appropriate descriptive results. "
    "A chat answer, three-sentence recap, analysis output or offer to write the report does not finish "
    "this goal. Prefer a self-contained local HTML report; do not publish it."
)


def build(case_id):
    base = BASES[case_id]
    directory = ROOT / "cases" / base["id"]
    base_bytes = (directory / "case.json").read_bytes()
    if sha(base_bytes) != base["sha256"]:
        raise ValueError("Frozen base manifest changed: " + base["id"])
    original = json.loads(base_bytes)
    if original["case_version"] != base["version"]:
        raise ValueError("Frozen base version changed: " + base["id"])
    package = {}
    for name, expected in original["files"].items():
        value = (directory / name).read_bytes()
        if sha(value) != expected:
            raise ValueError("Frozen base file changed: " + name)
        package[name] = value

    initial = package[original["initial_message"]].decode("utf-8").rstrip()
    initial += (
        "\n\nPlease continue through the investigation and supported analysis to a complete saved "
        "consultant report for the education board, with reproducible results. I need the main "
        "answer and its evidence, how you reached it, results and uncertainty, limitations, practical "
        "recommendations, sources and a short technical appendix. If these materials cannot support "
        "the causal answer, explain that clearly and report what they do support. A short chat recap "
        "is useful along the way, but I still need the complete report. A self-contained local HTML "
        "file is suitable; no publication is needed.\n"
    )
    package[original["initial_message"]] = initial.encode("utf-8")
    actor = json.loads(package[original["actor"]])
    actor["role"] = (
        "Simulated user only. Follow the frozen user-simulator policy and the visible conversation. "
        "Do not read the reviewer packet, oracle, consultant internal state or tool reasoning. "
        "Continue toward the complete report in the stated goal; analysis or a short recap does not "
        "replace it. Source-release rules remain unchanged and each source is attached at most once. "
        "After supported analysis and an established evidentiary boundary, request the full report "
        "instead of restarting an exhausted causal inquiry. Stop only after the requested report is "
        "delivered with no visible unresolved failure or promised correction. The operator may stop "
        "an incomplete attempt at its limits; user satisfaction does not certify scientific quality."
    )
    actor["goal"] = REPORT_GOAL
    actor["facts"].append({
        "fact_id": "f-report-deliverable",
        "statement": "The board needs a complete saved local consultant report, with the main answer, evidence and reasoning, results and uncertainty, limitations, practical recommendations, sources and a short technical appendix. Self-contained HTML is suitable. A complete report based on bounded descriptive evidence is acceptable when the causal question cannot be answered. The user does not authorize publication.",
        "certainty": "user deliverable preference",
        "source": "initial public report request",
        "available_when": "initially stated, or questions about audience, format, report scope or whether to continue after an analysis or recap",
        "disclosure_condition": "State the report preference naturally. Do not use it to invent study facts, prescribe a specialist or certify unsupported causal claims.",
    })
    retained = []
    for old_rule in actor["rules"]:
        if old_rule["rule_id"] in ("r-recap", "r-stop"):
            continue
        value = copy.deepcopy(old_rule)
        if value["rule_id"] == "r-descriptive":
            value["condition"] = value["condition"].replace("recap condition", "full-report request condition")
            value["action"] = value["action"].replace("recap rule", "full-report request rule")
            value["action"] += " The complete saved report remains part of the goal after this calculation."
        retained.append(value)
    actor["rules"] = retained + [
        rule("r-report-request",
             "The consultant delivers supported analysis and practical implications, offers a report or closing recap, or provides a short recap, while the complete saved report has not yet been delivered.",
             "Ask the consultant to continue any still-needed attainable investigation and finish the promised complete local report. If the evidence boundary is established and useful analysis is complete, request synthesis of that work into the report instead of renewing an exhausted causal inquiry. Do not accept a chat recap as a substitute or prescribe a hidden scientific check. If a sufficiently specified report request is already active, simply ask it to finish that deliverable."),
        rule("r-report-repair",
             "The user-visible response or report actually received shows an absent promised report, an explicitly incomplete or unreadable deliverable, or a concrete inconsistency with previously disclosed facts/results.",
             "Identify the visible missing item or inconsistency and ask for that correction to the report. Do not invent a defect, access private consultant state, demand a reviewer checklist, or require a new estimator merely to add work. If rendering, file access or execution is reported as failed, do not describe the report as successfully delivered. Continue toward the same deliverable; the operator handles hard resource stops."),
        rule("r-stop",
             "The consultant has delivered the requested complete saved report with a usable artifact reference, and no visible unresolved delivery failure or promised correction remains.",
             "Stop without a new task or an obligatory extra recap. This is a user-level stopping decision; the independent reviewer still checks actual artifact existence, evidence, completeness, scientific claims and validation. An offer to write the report, an analysis file, a chat summary or a stated future plan is not report delivery."),
    ]
    package[original["actor"]] = encode(actor)

    reviewer = json.loads(package[original["reviewer"]])
    reviewer.update({"case_id": case_id, "case_version": CASE_VERSION, "suite_version": SUITE_VERSION,
                     "edition": "complete-local-board-report", "completion": REPORT_GOAL,
                     "adaptation": "Full-report continuation edition of " + base["id"] + "@" + base["version"] + ". Original study facts, data, source availability and numerical oracles are retained. The public request, actor deliverable/stop policy and report review obligations change prospectively; no original result is regraded.",
                     "useful_stop": False})
    criteria = []
    for old in reviewer["criteria"]:
        if old["id"] == "c-recap":
            continue
        value = copy.deepcopy(old)
        if value["id"] == "c-stopping":
            value["rule"] = "Deliver useful practical advice and the complete saved report requested by this edition. Respect source unavailability and scope choices, but do not treat an intermediate descriptive result or short chat recap as completion of the report request. No fixed number of rounds or mandatory visit to every specialist is required."
        criteria.append(value)
    criteria += [
        criterion("c-report-delivery", "Deliver an actual complete local report in a completed separate report run, with a usable artifact path and actual output bytes. A chat recap, analysis CSV, promised report, partial file or operator-authored test summary is insufficient. Supported descriptive findings and an explicitly unresolved causal target can form a complete report; causal identification is not mandatory. A resource stop without the report remains incomplete, regardless of whether useful analysis exists."),
        criterion("c-report-evidence", "Bind the report to the selected available analysis results, diagnostics and sources through its report plan, evidence references and hashed inputs. Verify its completed report manifest and output identity. Report tables, estimates, intervals, denominators and interpretations must agree with the actual selected evidence. Writing the report does not authorize inventing, silently changing or rerunning empirical results. New necessary empirical work must return to the lead before final reporting."),
        criterion("c-report-coverage", "The report should let the board understand the original question, intervention and target; the data and provenance; consequential findings from investigation and remaining unknowns; the chosen method and its rationale; supported results in study units with uncertainty; relevant diagnostics/sensitivities actually performed or justified omissions; limits, practical implications, sources and reproducibility detail. Preserve the distinction between established evidence and adopted assumptions. Coverage may be concise and use any sensible structure; do not grade page count, fixed headings, decoration or an arbitrary specialist sequence."),
        criterion("c-report-validation", "Retain evidence of reading back the saved report and checking its consequential claims against exact source values and inherited claim boundaries. For HTML or another visual format, retain rendering inspection and corrections of broken assets, unreadable tables or clipping. A failed or unperformed required validation is a recorded limitation, not a completed validated report. Evaluate actual observations; artifact presence alone and the actor's willingness to stop do not establish quality."),
    ]
    reviewer["criteria"] = criteria
    observations = reviewer.get("required_observations", [])
    reviewer["required_observations"] = list(dict.fromkeys(observations + [
        "actual public exchanges and actor disclosures through report delivery",
        "selected completed analysis results, diagnostics and reproducible code",
        "separate completed report plan, evidence/input identities, manifest and artifact bytes",
        "report readback, numerical/claim checks and applicable rendering inspection",
        "actual worker/tool traces and per-turn project verification",
    ]))
    package[original["reviewer"]] = encode(reviewer)
    provenance = {
        "kind": "versioned communication and deliverable adaptation; scientific world unchanged",
        "generator": "interactive-test-cc/scripts/generate_report_cases.py",
        "generator_sha256": sha(Path(__file__).read_bytes()),
        "base_case_id": base["id"], "base_case_version": base["version"],
        "base_case_manifest_sha256": base["sha256"],
        "base_provenance": json.loads(package["provenance.json"]),
        "adaptation": "Extend the requested endpoint through a complete saved local report. Public study documents, CSV files, oracle.json and check_oracle.py retain their exact bytes. Existing user study facts and source availability retain their values. The initial request and actor report preferences are new communication scope, not new study facts.",
        "validation": "The base independent numerical checker remains standalone and unchanged. New deterministic checks validate report-case contracts, source/science invariance and exact regeneration. These checks do not simulate or qualify consultant behavior.",
    }
    package["provenance.json"] = encode(provenance)
    manifest = copy.deepcopy(original)
    manifest.update({
        "case_id": case_id, "case_version": CASE_VERSION, "suite_version": SUITE_VERSION,
        "edition": "complete-local-board-report", "author": "Codex versioned full-report fixture assembly, 2026-09-09 UTC",
        "base_case_id": base["id"] + "@" + base["version"],
        "adaptation": reviewer["adaptation"], "completion_contract": "full_report",
        "requirements": "Shared Python 3.10+ stdlib, shared Node 18.18+, causal-consultant 7.0.2, and a callable local rendering/inspection surface for the default HTML deliverable. Verified host isolation and separate actor/reviewer contexts are required for a blinded comparison. No project-local packages or environments.",
        "run_limits": LIMITS,
        "files": {name: sha(value) for name, value in sorted(package.items())},
    })
    package["case.json"] = encode(manifest)
    return package


def main():
    for case_id in BASES:
        package = build(case_id)
        directory = ROOT / "cases" / case_id
        existing = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
        if existing - package.keys():
            raise ValueError("Unexpected files in child case: " + case_id)
        for name, value in package.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value)
        print(case_id + " " + sha(package["case.json"]))


if __name__ == "__main__":
    main()
