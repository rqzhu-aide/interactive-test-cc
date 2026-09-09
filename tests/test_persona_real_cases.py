"""Real-data integrity and numerical references, not simulated consulting quality."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_persona_real_cases import CASES, LIMITS, build
from session_driver import validate_case


def read(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


class PersonaRealCases(unittest.TestCase):
    def test_standalone_identity_and_exact_regeneration(self):
        for case_id, (_, persona, source, sha) in CASES.items():
            with self.subTest(case=case_id):
                root = ROOT / "cases" / case_id
                original = (ROOT.parent / "test-data" / source / "data.csv").read_bytes()
                manifest = validate_case(root)
                self.assertEqual(manifest["suite_version"], "7.0.4")
                self.assertEqual(manifest["case_version"], "1.0.0")
                self.assertEqual(manifest["target_consultant"], "7.0.2")
                self.assertEqual(manifest["completion_contract"], "full_report")
                self.assertEqual(manifest["run_limits"], LIMITS)
                self.assertEqual(manifest["persona_id"], persona)
                self.assertEqual((root / "public/data.csv").read_bytes(), original)
                self.assertEqual(digest(original), sha)
                expected = build(case_id)
                actual = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                self.assertEqual(actual, expected)

    def test_world_actor_source_references_and_private_boundary(self):
        for case_id in CASES:
            with self.subTest(case=case_id):
                root = ROOT / "cases" / case_id
                manifest, actor, world = read(root, "case.json"), read(root, "actor.json"), read(root, "world.json")
                self.assertEqual(world["world_id"], manifest["world_id"])
                self.assertEqual(world["world_version"], manifest["world_version"])
                self.assertEqual(actor["persona_id"], manifest["persona_id"])
                source_ids = {s["id"] for s in manifest["sources"]}
                fact_ids = {f["fact_id"] for f in actor["facts"]}
                self.assertEqual(set(world["attainable"]), source_ids)
                for rule in actor["rules"]:
                    self.assertLessEqual(set(rule["fact_ids"]), fact_ids)
                    self.assertLessEqual(set(rule["source_ids"]), source_ids)
                staged = {s["file"] for s in manifest["sources"]}
                self.assertTrue({"world.json", "actor.json", "reviewer.json", "oracle.json", "provenance.json"}.isdisjoint(staged))
                self.assertTrue(all(p.startswith("public/") for p in staged))

    def test_numeric_check_runs_without_repository_or_generator(self):
        for case_id in CASES:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "standalone"
                shutil.copytree(ROOT / "cases" / case_id, root)
                result = subprocess.run([sys.executable, "-B", str(root / "check_oracle.py")], cwd=root,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(json.loads(result.stdout)["ok"])

    def test_rehashed_changed_data_still_fails_numeric_reference(self):
        for case_id in CASES:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                shutil.copytree(ROOT / "cases" / case_id, root)
                path = root / "public/data.csv"
                data = path.read_bytes()
                if "star" in case_id:
                    data = data.replace(b"473,447,", b"573,447,", 1)
                else:
                    data = data.replace(b"6.306275", b"7.306275", 1)
                self.assertNotEqual(data, path.read_bytes())
                path.write_bytes(data)
                oracle = read(root, "oracle.json")
                oracle["data_sha256"] = digest(data)
                (root / "oracle.json").write_text(json.dumps(oracle), encoding="utf-8")
                manifest = read(root, "case.json")
                manifest["files"] = {name: digest((root / name).read_bytes()) for name in manifest["files"]}
                (root / "case.json").write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "self-check"):
                    validate_case(root)

    def test_references_match_observed_structure_and_no_known_causal_truth(self):
        star = read(ROOT / "cases/persona-domain-star-v7", "oracle.json")
        school = read(ROOT / "cases/persona-statistician-schooling-v7", "oracle.json")
        self.assertEqual(star["reference"]["n"], 5748)
        self.assertEqual(star["reference"]["schools"], 79)
        self.assertEqual(star["reference"]["arm_counts"], {"regular": 2000, "small.class": 1733, "regular.with.aide": 2015})
        self.assertTrue(all(value == 0 for value in star["missing_cells"].values()))
        self.assertEqual({k: v for k, v in school["missing_cells"].items() if v},
                         {"kww": 47, "iqscore": 949, "mar76": 7, "libcrd14": 13})
        self.assertTrue(school["reference"]["exp76_equals_age76_minus_ed76_minus_6"])
        self.assertEqual(school["reference"]["nomomed_equals_nodaded_rows"], 3010)
        self.assertIsNone(star["causal_truth"])
        self.assertIsNone(school["causal_truth"])
        coefficient = school["reference"]["Wald_unadjusted"]["slope"]
        interval = school["reference"]["AR_HC1_asymptotic_95"]["bounds"]
        self.assertLess(interval[0], coefficient)
        self.assertGreater(interval[1], coefficient)


if __name__ == "__main__":
    unittest.main()
