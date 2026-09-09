"""Check standalone report fixtures and unchanged science, not model reasoning."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_report_cases import BASES, LIMITS, build
from session_driver import validate_case


def read(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8"))


def digest(value):
    return hashlib.sha256(value).hexdigest()


class ReportCases(unittest.TestCase):
    def test_children_validate_and_regenerate_without_changing_base(self):
        for identity, base in BASES.items():
            with self.subTest(case=identity):
                directory = ROOT / "cases" / identity
                parent = ROOT / "cases" / base["id"]
                before = {p.relative_to(parent).as_posix(): digest(p.read_bytes())
                          for p in parent.rglob("*") if p.is_file()}
                manifest = validate_case(directory)
                self.assertEqual(manifest["completion_contract"], "full_report")
                self.assertEqual(manifest["case_version"], "1.0.0")
                self.assertEqual(manifest["suite_version"], "7.0.3")
                self.assertEqual(manifest["run_limits"], LIMITS)
                self.assertEqual(manifest["base_case_id"], base["id"] + "@" + base["version"])
                regenerated = build(identity)
                self.assertEqual(set(regenerated), set(manifest["files"]) | {"case.json"})
                for name, value in regenerated.items():
                    self.assertEqual((directory / name).read_bytes(), value, name)
                after = {p.relative_to(parent).as_posix(): digest(p.read_bytes())
                         for p in parent.rglob("*") if p.is_file()}
                self.assertEqual(before, after)
                self.assertEqual(before["case.json"], base["sha256"])

    def test_original_sources_facts_and_numerical_oracles_are_retained(self):
        for identity, base in BASES.items():
            with self.subTest(case=identity):
                directory = ROOT / "cases" / identity
                parent = ROOT / "cases" / base["id"]
                child, original = read(directory, "case.json"), read(parent, "case.json")
                self.assertEqual(child["sources"], original["sources"])
                for name in original["files"]:
                    if (name.startswith("public/") and name != original["initial_message"]) or name in ("oracle.json", "check_oracle.py"):
                        self.assertEqual((directory / name).read_bytes(), (parent / name).read_bytes(), name)
                original_request = (parent / original["initial_message"]).read_text(encoding="utf-8").rstrip()
                self.assertTrue((directory / child["initial_message"]).read_text(encoding="utf-8").startswith(original_request + "\n\n"))
                old_actor, new_actor = read(parent, original["actor"]), read(directory, child["actor"])
                self.assertEqual(new_actor["facts"][:-1], old_actor["facts"])
                self.assertEqual(new_actor["facts"][-1]["fact_id"], "f-report-deliverable")
                self.assertEqual(old_actor["sources"], new_actor["sources"])
                self.assertEqual(old_actor["fluency"], new_actor["fluency"])
                old_rules = {r["rule_id"]: r for r in old_actor["rules"]}
                new_rules = {r["rule_id"]: r for r in new_actor["rules"]}
                for key in old_rules.keys() - {"r-recap", "r-stop", "r-descriptive"}:
                    self.assertEqual(old_rules[key], new_rules[key])

    def test_scientific_review_is_retained_and_report_completion_is_required(self):
        for identity, base in BASES.items():
            with self.subTest(case=identity):
                directory = ROOT / "cases" / identity
                parent = ROOT / "cases" / base["id"]
                old, new = read(parent, "reviewer.json"), read(directory, "reviewer.json")
                self.assertEqual(old["scientific_truth"], new["scientific_truth"])
                for field in ("numeric_reference", "oracles", "validity", "allowed_alternatives"):
                    if field in old:
                        self.assertEqual(old[field], new[field], field)
                old_criteria = {c["id"]: c for c in old["criteria"]}
                new_criteria = {c["id"]: c for c in new["criteria"]}
                for key in old_criteria.keys() - {"c-recap", "c-stopping"}:
                    self.assertEqual(old_criteria[key], new_criteria[key])
                for key in ("c-report-delivery", "c-report-evidence", "c-report-coverage", "c-report-validation"):
                    self.assertTrue(new_criteria[key]["required"])
                self.assertFalse(new["useful_stop"])
                actor = read(directory, "actor.json")
                rules = {r["rule_id"]: r for r in actor["rules"]}
                self.assertNotIn("r-recap", rules)
                self.assertTrue({"r-report-request", "r-report-repair", "r-stop"} <= rules.keys())
                known = {f["fact_id"] for f in actor["facts"]}
                for value in rules.values():
                    self.assertTrue(set(value.get("fact_ids", [])) <= known)

    def test_report_case_copies_validate_without_bases_or_generator(self):
        for identity in BASES:
            with self.subTest(case=identity), tempfile.TemporaryDirectory(prefix="report-fixture-check-") as temporary:
                directory = ROOT / "cases" / identity
                target = Path(temporary)
                for path in directory.rglob("*"):
                    if path.is_file():
                        output = target / path.relative_to(directory)
                        output.parent.mkdir(parents=True, exist_ok=True)
                        output.write_bytes(path.read_bytes())
                manifest = validate_case(target)
                self.assertEqual(manifest["case_id"], identity)
                result = subprocess.run([sys.executable, "-B", str(target / "check_oracle.py")], cwd=target,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
