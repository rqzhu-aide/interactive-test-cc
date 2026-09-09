"""Validate standalone persona fixtures and science preservation, not model behavior."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_persona_core_cases as generator
from session_driver import validate_case

NOVICE = "persona-novice-grant-v7"
ADVERSARIAL = "persona-adversarial-college-v7"


def read(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8"))


def inventory(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob("*") if p.is_file()}


class PersonaCoreCases(unittest.TestCase):
    def test_validate_regeneration_and_pinned_parent_preservation(self):
        for identity, base in generator.BASES.items():
            with self.subTest(case=identity):
                directory = ROOT / "cases" / identity
                parent = ROOT / "cases" / base["id"]
                before = inventory(parent)
                manifest = validate_case(directory)
                self.assertEqual(manifest["case_version"], "1.0.0")
                self.assertEqual(manifest["suite_version"], "7.0.4")
                self.assertEqual(manifest["completion_contract"], "full_report")
                self.assertEqual(manifest["run_limits"], generator.LIMITS)
                self.assertEqual(manifest["base_case_id"], base["id"] + "@" + base["version"])
                regenerated = generator.build(identity)
                self.assertEqual(set(regenerated), set(manifest["files"]) | {"case.json"})
                for name, value in regenerated.items():
                    self.assertEqual((directory / name).read_bytes(), value, name)
                self.assertEqual(inventory(parent), before)
                self.assertEqual(before["case.json"], base["sha256"])
                expected_parent = read(parent, "case.json")["files"]
                self.assertEqual({k: v for k, v in before.items() if k != "case.json"}, expected_parent)

    def test_scientific_source_and_oracle_bytes_are_retained(self):
        for identity, base in generator.BASES.items():
            with self.subTest(case=identity):
                directory, parent = ROOT / "cases" / identity, ROOT / "cases" / base["id"]
                original = read(parent, "case.json")
                for name in original["files"]:
                    if name in ("oracle.json", "check_oracle.py") or (name.startswith("public/") and name != original["initial_message"]):
                        expected = (parent / name).read_bytes()
                        if identity == NOVICE and name == generator.INVENTORY_ADAPTATION["file"]:
                            adaptation = generator.INVENTORY_ADAPTATION
                            self.assertEqual(expected.count(adaptation["before"].encode()), 1)
                            expected = expected.replace(adaptation["before"].encode(), adaptation["after"].encode())
                        self.assertEqual((directory / name).read_bytes(), expected, name)
                old, new = read(parent, "reviewer.json"), read(directory, "reviewer.json")
                for key in ("scientific_truth", "numeric_reference", "oracles", "allowed_alternatives", "validity"):
                    if key in old:
                        self.assertEqual(new[key], old[key], key)
                criteria = {entry["id"]: entry for entry in new["criteria"]}
                for entry in old["criteria"]:
                    self.assertEqual(criteria[entry["id"]], entry)

    def test_world_identity_private_binding_and_complete_source_inventory(self):
        for identity, base in generator.BASES.items():
            with self.subTest(case=identity):
                directory = ROOT / "cases" / identity
                manifest, actor = read(directory, "case.json"), read(directory, "actor.json")
                world = read(directory, manifest["world"])
                self.assertEqual(manifest["world"], "world.json")
                self.assertFalse(manifest["world"].startswith("public/"))
                self.assertEqual(manifest["files"][manifest["world"]], inventory(directory)["world.json"])
                self.assertEqual(manifest["world_id"], base["world_id"])
                self.assertEqual(world["world_id"], manifest["world_id"])
                self.assertEqual(world["world_version"], manifest["world_version"])
                self.assertEqual(actor["persona_id"], manifest["persona_id"])
                self.assertEqual(world["scientific_truth"], read(directory, "reviewer.json")["scientific_truth"])
                self.assertIs(world["known_causal_truth"], identity == NOVICE)
                sources = {s["id"]: s for s in manifest["sources"]}
                self.assertEqual({s["source_id"] for s in world["source_inventory"]}, set(sources))
                for entry in world["source_inventory"]:
                    source = sources[entry["source_id"]]
                    self.assertEqual(entry["file"], source["file"])
                    self.assertEqual(entry["availability"], source["availability"])
                    self.assertEqual(entry["sha256"], manifest["files"][source["file"]])
                    self.assertNotEqual(entry["file"], manifest["world"])
                for kind in ("oracle", "checker"):
                    refs = world["reference_outputs"]
                    self.assertEqual(refs[kind + "_sha256"], manifest["files"][refs[kind + "_file"]])
                adaptations = [generator.INVENTORY_ADAPTATION] if identity == NOVICE else []
                self.assertEqual(world["communication_adaptations"], adaptations)
                self.assertEqual(read(directory, "provenance.json")["communication_adaptations"], adaptations)

    def test_novice_initial_information_and_release_rule_references(self):
        directory = ROOT / "cases" / NOVICE
        manifest, actor = read(directory, "case.json"), read(directory, "actor.json")
        sources = {s["id"]: s for s in manifest["sources"]}
        self.assertEqual({key for key, s in sources.items() if s["availability"] == "initial"}, {"s-data"})
        on_request = {key for key, s in sources.items() if s["availability"] == "on_request"}
        self.assertEqual(on_request, {"s-dictionary", "s-allocation", "s-inventory"})
        for item in actor["sources"]:
            source = sources[item["source_id"]]
            self.assertEqual(item["availability"], source["availability"])
            self.assertEqual(item["file"], source["destination"])
        rules = {r["rule_id"]: r for r in actor["rules"]}
        self.assertTrue(on_request <= set(rules["r-definitions-release"]["source_ids"]))
        self.assertTrue(on_request <= set(rules["r-access-release"]["source_ids"]))
        self.assertIn("s-allocation", rules["r-allocation-release"]["source_ids"])
        self.assertNotIn("f-allocation-source", {f["fact_id"] for f in actor["facts"]})
        self.assertEqual({b["subject"] for b in actor["persona_profile"]["beliefs"]},
                         {"b-baseline-cohort", "b-average-guarantee"})

    def test_adversarial_world_facts_and_finite_pressure_declarations(self):
        directory = ROOT / "cases" / ADVERSARIAL
        parent = ROOT / "cases" / generator.BASES[ADVERSARIAL]["id"]
        actor, original = read(directory, "actor.json"), read(parent, "actor.json")
        self.assertEqual(actor["facts"], original["facts"])
        self.assertEqual(read(directory, "case.json")["sources"], read(parent, "case.json")["sources"])
        events = actor["persona_profile"]["pressure_events"]
        self.assertEqual({e["subject"] for e in events},
                         {"d-causal-pressure", "d-selection-pressure", "d-uncertainty-pressure"})
        self.assertTrue(all(type(e["maximum_occurrences"]) is int and e["maximum_occurrences"] == 1 for e in events))
        self.assertEqual(sum(e["maximum_occurrences"] for e in events), 3)
        self.assertTrue(all(e["trigger"] and e["retirement"] for e in events))
        # Semantic pressure and retirement still need independent actor rehearsal.

    def test_learning_subjects_references_and_report_endpoint_are_coherent(self):
        for identity in generator.BASES:
            with self.subTest(case=identity):
                directory = ROOT / "cases" / identity
                actor, reviewer = read(directory, "actor.json"), read(directory, "reviewer.json")
                profile = actor["persona_profile"]
                subjects = [entry["subject"] for key in ("knowledge", "beliefs", "decisions", "pressure_events")
                            for entry in profile.get(key, [])]
                self.assertTrue(subjects)
                self.assertEqual(len(subjects), len(set(subjects)))
                self.assertTrue(all(entry.get("learning") for entry in profile["beliefs"]))
                for name in generator.UPDATE_FIELDS:
                    self.assertEqual(actor["reply_record"][name], [])
                fact_ids = {f["fact_id"] for f in actor["facts"]}
                source_ids = {s["source_id"] for s in actor["sources"]}
                for item in actor["rules"]:
                    self.assertTrue(set(item.get("fact_ids", [])) <= fact_ids, item["rule_id"])
                    self.assertTrue(set(item.get("source_ids", [])) <= source_ids, item["rule_id"])
                rules = {r["rule_id"] for r in actor["rules"]}
                self.assertTrue({"r-report-request", "r-report-repair", "r-stop"} <= rules)
                self.assertNotIn("r-recap", rules)
                criteria = {c["id"]: c for c in reviewer["criteria"]}
                for key in ("c-persona-fidelity", "c-persona-learning", "c-report-delivery", "c-report-evidence", "c-report-validation"):
                    self.assertTrue(criteria[key]["required"])
                self.assertFalse(reviewer["useful_stop"])

    def test_standalone_copy_oracles_without_repository_or_audit_dependencies(self):
        for identity in generator.BASES:
            with self.subTest(case=identity), tempfile.TemporaryDirectory(prefix="persona-fixture-") as temporary:
                target = Path(temporary) / "case"
                shutil.copytree(ROOT / "cases" / identity, target)
                manifest = validate_case(target)
                self.assertEqual(manifest["case_id"], identity)
                result = subprocess.run([sys.executable, "-B", str(target / manifest["oracle_check"])], cwd=target,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)["ok"])
                self.assertFalse(list(target.rglob("__pycache__")))

    def test_generator_rejects_changed_pinned_science_without_writing(self):
        for identity, base in generator.BASES.items():
            with self.subTest(case=identity), tempfile.TemporaryDirectory(prefix="persona-pin-") as temporary:
                sandbox = Path(temporary)
                parent = sandbox / "cases" / base["id"]
                shutil.copytree(ROOT / "cases" / base["id"], parent)
                data = parent / "public/data.csv"
                data.write_bytes(data.read_bytes() + b"\n")
                with patch.object(generator, "ROOT", sandbox), self.assertRaisesRegex(ValueError, "Pinned base payload changed"):
                    generator.build(identity)
                self.assertFalse((sandbox / "cases" / identity).exists())


if __name__ == "__main__":
    unittest.main()
