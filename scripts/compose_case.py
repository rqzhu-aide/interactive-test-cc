"""Compose one frozen problem/persona case for the existing consultation runner."""
import argparse
import copy
import json
from pathlib import Path
import shutil

from session_driver import digest, inventory, member, read, require
from source_release import validate_source_prerequisite


ROOT = Path(__file__).resolve().parents[1]
PROBLEM_IDS = ("study-design", "observational-did", "cate-policy", "data-quality-edge")
PERSONA_IDS = ("novice", "domain-expert", "statistician", "adversarial")
COMMON_RULES = [
    {"rule_id": "r-initial", "condition": "This is the initial dispatch.",
     "action": "Send exactly the frozen initial request. Do not add private profile, benchmark or expected-answer information.",
     "fact_ids": [], "source_ids": []},
    {"rule_id": "r-known-facts", "condition": "The consultant asks a factual question you can answer from your packet or legitimately learned information.",
     "action": "Answer the current question or closely connected group from what you actually understand, following your persona's disclosure_policy. Keep a short necessary answer together. For a long questionnaire, prioritize the issue blocking the next useful step, acknowledge the remaining topics and retain them in unanswered_questions. Do not recite every known fact or treat a broad request as permission to complete the whole intake at once. Cite visible learning in knowledge_updates; preserve qualifications.",
     "fact_ids": [], "source_ids": []},
    {"rule_id": "r-records", "condition": "The consultant asks for records or information covered by the source inventory.",
     "action": "Source conditions establish eligibility, not an instruction to attach everything eligible. Supply the record or coherent bundle needed for the current issue, with a brief explanation of its relevance. For a broad request covering several topics, start with the current consequential topic and say what other records are available or still requested; do not send the entire dossier in one reply. Follow up on acknowledged requests as the discussion reaches them, without requiring repeated requests. Honor a specific request for a necessary bundle and keep a requested file intact. Do not require private filenames, invent retrieval delays, claim accessible records are unavailable or repeat an attachment. Preserve genuine evaluation-data prerequisites.",
     "fact_ids": [], "source_ids": []},
    {"rule_id": "r-clarify", "condition": "An explanation, request or decision is unclear at your persona's current understanding.",
     "action": "Ask a natural focused question about its practical meaning. Still answer clear parts you know. Retain what you learn and do not repeat a resolved misunderstanding.",
     "fact_ids": [], "source_ids": []},
    {"rule_id": "r-proceed", "condition": "The consultant proposes useful work within the requested study and deliverable.",
     "action": "Respond to the actual offered scope and choices using your documented decision constraints. The initial report request states a goal, not standing permission for analysis or reporting. Ask about unclear implications; otherwise choose supported bounded work in ordinary language. An extension selection authorizes that extension only. Do not prescribe internal routing or a preferred result.",
     "fact_ids": [], "source_ids": []},
    {"rule_id": "r-persona", "condition": "The visible exchange warrants a belief update, method discussion or a permitted presentation-pressure event.",
     "action": "Use only the selected persona's behavior and finite pressure policy. Record the visible basis and retain learning. Persona preferences cannot change study facts or replace the problem's endpoint.",
     "fact_ids": [], "source_ids": []},
    {"rule_id": "r-report", "condition": "The substantive work is settled but the requested saved report has not yet been delivered, or an actual visible omission needs correction.",
     "action": "Use the actual findings and offered directions to choose useful further work or the saved report. If no report option has been offered, you may naturally ask about the deliverable, without treating that request as permission to skip discussion. Ask for a concrete correction when needed. Do not force completion while material questions remain. A recap does not substitute for the saved report.",
     "fact_ids": [], "source_ids": []},
    {"rule_id": "r-stop", "condition": "The requested saved report has been visibly delivered, the stated scope is addressed, and no accepted correction or outstanding user question remains.",
     "action": "Stop without manufacturing another recap or an unused pressure event. Judge completion from information a user can actually see; do not read private helper observations or certify hidden scientific truth. Independent review checks actual artifact integrity and scientific quality.",
     "fact_ids": [], "source_ids": []},
]


def save(file, value):
    Path(file).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def problem_definition(problem_id, bank_root):
    require(problem_id in PROBLEM_IDS, "unknown problem selector")
    directory = member(bank_root, problem_id)
    definition = read(directory / "problem.json")
    require(definition.get("schema_version") == 1 and definition.get("problem_id") == problem_id,
            "problem identity mismatch")
    actual = inventory(directory)
    del actual["problem.json"]
    require(actual == definition["files"], "problem file identity mismatch")
    require(type(definition.get("target_turns")) is int and definition["target_turns"] > 0,
            "problem target must be a positive descriptive count")
    require(set(definition["initial_requests"]) == set(PERSONA_IDS), "missing persona request wording")
    require("public/initial-message.txt" not in actual,
            "initial message must be composed from private wording templates")
    for source in definition["sources"]:
        validate_source_prerequisite(source)
    world = read(member(directory, definition["world"]))
    require(world.get("world_id") and world.get("world_version"), "missing world identity")
    for key in ("world", "reviewer", "oracle_check"):
        require(definition[key] in actual and not definition[key].startswith("public/"),
                "private problem material must remain private")
    return directory, definition, world


def persona_definition(persona_id, personas_root):
    require(persona_id in PERSONA_IDS, "unknown persona selector")
    file = member(personas_root, persona_id + ".json")
    persona = read(file)
    require(persona.get("schema_version") == 1 and persona.get("persona_id") == persona_id,
            "persona identity mismatch")
    require(persona.get("persona_version"), "missing persona version")
    tiers = persona.get("initial_knowledge_tiers")
    require(isinstance(tiers, list) and tiers and set(tiers) <= {"practical", "domain", "statistical"},
            "unsupported knowledge tiers")
    require(not any(key in persona for key in ("goal", "sources", "world", "target_turns", "completion_contract")),
            "persona cannot override the problem, access, endpoint or duration")
    for key in ("behavior", "disclosure_policy", "learning_policy", "pressure_policy", "forbidden"):
        require(isinstance(persona.get(key), list) and all(isinstance(x, str) and x.strip() for x in persona[key]),
                "invalid persona behavior field: " + key)
    require(bool(persona["disclosure_policy"]), "persona disclosure policy must not be empty")
    return file, persona


def compose_case(problem_id, persona_id, output, bank_root=None, personas_root=None, max_consultant_turns=40):
    bank_root = Path(bank_root or ROOT / "problems").resolve()
    personas_root = Path(personas_root or ROOT / "personas").resolve()
    directory, problem, world = problem_definition(problem_id, bank_root)
    persona_file, persona = persona_definition(persona_id, personas_root)
    require(type(max_consultant_turns) is int and max_consultant_turns > 0,
            "operational maximum must be a positive integer")
    output = Path(output).resolve()
    require(not output.exists(), "output already exists; compose into a fresh directory")
    require(not any(output.is_relative_to(source) or source.is_relative_to(output)
                    for source in (bank_root, personas_root)), "output overlaps definition bank")
    facts = []
    for entry in problem["actor_facts"]:
        require(entry.get("knowledge_tier") in ("practical", "domain", "statistical"),
                "actor fact lacks a knowledge tier")
        if entry["knowledge_tier"] in persona["initial_knowledge_tiers"]:
            facts.append({key: copy.deepcopy(value) for key, value in entry.items() if key != "knowledge_tier"})
    fact_ids = {entry["fact_id"] for entry in facts}
    rules = copy.deepcopy(COMMON_RULES) + copy.deepcopy(problem.get("actor_rules", []))
    require(len({entry["rule_id"] for entry in rules}) == len(rules), "duplicate composed actor rule ID")
    for rule in rules:
        rule["fact_ids"] = [ref for ref in rule.get("fact_ids", []) if ref in fact_ids]
    rules[1]["fact_ids"] = sorted(fact_ids)
    sources = [{"source_id": entry["id"], "file": entry["destination"],
                "availability": entry["availability"], "release": entry["release_when"],
                **({"release_prerequisite": copy.deepcopy(entry["release_prerequisite"])}
                   if "release_prerequisite" in entry else {})}
               for entry in problem["sources"]]
    rules[2]["source_ids"] = [entry["source_id"] for entry in sources]
    actor = {
        "role": "Simulated user only. Read this packet and the user-simulator policy, visible conversation and legitimately received material. Do not read the private problem definition, world, numerical oracle, reviewer packet or consultant internal state.",
        "persona_id": persona_id, "persona_version": persona["persona_version"],
        "persona_profile": persona, "goal": problem["goal"], "fluency": persona["fluency"],
        "facts": facts, "sources": sources, "rules": rules, "unknown_policy": problem["unknown_policy"],
        "reply_record": {"required": ["message", "fact_ids", "rule_ids", "attachments", "unanswered_questions", "fixture_gaps", "stop"],
                         "optional": ["knowledge_updates", "belief_updates", "decision_updates", "actor_context",
                                      "action_intents", "source_release_receipts"]},
        "pacing": "Share information progressively around the issue currently being discussed, using your persona's disclosure_policy. Broad relevance does not require exhausting all facts or records in one reply. Retain and revisit unanswered requests; do not hide a known consequential correction, fragment a necessary answer or invent delays. No turn number, target or operational limit determines disclosure or completion. Operational stopping is the operator's responsibility."
    }
    request = problem["initial_requests"][persona_id]
    require("causal-consultant" in request, "initial request must invoke consultant")
    require("report" in request.lower(), "initial request must retain the saved report objective")
    output.mkdir(parents=True)
    # The source bank remains immutable; each run receives a fresh frozen composition.
    for name in ("problem.json", *problem["files"]):
        destination = member(output, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(member(directory, name), destination)
    shutil.copyfile(persona_file, output / "persona.json")
    (output / "public/initial-message.txt").write_text(request.rstrip() + "\n", encoding="utf-8")
    save(output / "actor.json", actor)
    save(output / "composition.json", {
        "schema_version": 1, "problem_id": problem_id, "problem_version": problem["problem_version"],
        "problem_sha256": digest(directory / "problem.json"), "persona_id": persona_id,
        "persona_version": persona["persona_version"], "persona_sha256": digest(persona_file),
        "composer_sha256": digest(Path(__file__)), "target_turns": problem["target_turns"],
        "target_semantics": "Descriptive expectation only. Never exposed as an actor instruction, deadline, quota or success criterion.",
        "science_boundary": "Persona changes initial understanding and interaction, not the problem's world, source access, data, scientific criteria or report endpoint."
    })
    manifest = {
        "schema_version": 1, "case_id": problem_id + "--" + persona_id, "case_version": "1.0.2",
        "suite_version": "7.0.9", "edition": "modular-problem-persona",
        "problem_id": problem_id, "problem_version": problem["problem_version"],
        "persona_id": persona_id, "persona_version": persona["persona_version"],
        "world": problem["world"], "world_id": world["world_id"], "world_version": world["world_version"],
        "author": "Versioned modular test composition", "completion_contract": "full_report",
        "target_turns": problem["target_turns"],
        "run_limits": {"consultant_turns": max_consultant_turns, "active_seconds": 14400, "elapsed_seconds": 43200},
        "requirements": "Shared Python 3.10+ stdlib and Node 18.18+. Freeze independent operational limits and verified host boundaries before a scored run.",
        "initial_message": "public/initial-message.txt", "actor": "actor.json",
        "reviewer": problem["reviewer"], "oracle_check": problem["oracle_check"],
        "sources": [{key: copy.deepcopy(value) for key, value in entry.items() if key != "release_when"}
                    for entry in problem["sources"]], "files": inventory(output)
    }
    save(output / "case.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List the four problems and four independent personas")
    parser.add_argument("--problem", choices=PROBLEM_IDS)
    parser.add_argument("--persona", choices=PERSONA_IDS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-consultant-turns", type=int, default=40,
                        help="Separate operational maximum for the generated manifest, not its target or a stopping instruction")
    args = parser.parse_args()
    if args.list:
        print(json.dumps({"problems": [{"id": key, "label": (item := read(ROOT / "problems" / key / "problem.json"))["label"],
                                        "target_turns": item["target_turns"]} for key in PROBLEM_IDS],
                          "personas": [{"id": key, "label": read(ROOT / "personas" / (key + ".json"))["label"]}
                                       for key in PERSONA_IDS], "combinations": 16}, indent=2))
        return
    parser.error("--problem, --persona and --output are required") if not all((args.problem, args.persona, args.output)) else None
    manifest = compose_case(args.problem, args.persona, args.output, max_consultant_turns=args.max_consultant_turns)
    print(json.dumps({"case_id": manifest["case_id"], "output": str(args.output.resolve()),
                      "target_turns": manifest["target_turns"], "completion_contract": manifest["completion_contract"]}, indent=2))


if __name__ == "__main__":
    main()
