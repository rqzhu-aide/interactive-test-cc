"""Exercise composed fixtures and their isolation, not consultant model quality."""
import csv
from collections import Counter
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import compose_case as composer
from session_driver import validate_case

PROBLEMS = {"study-design": 5, "observational-did": 10,
            "cate-policy": 15, "data-quality-edge": 8}
PERSONAS = ("novice", "domain-expert", "statistician", "adversarial")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def inventory(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file()}


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class ModularCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="modular-matrix-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.cases = {}
        cls.original_bank = inventory(ROOT / "problems")
        cls.original_personas = inventory(ROOT / "personas")
        for problem in PROBLEMS:
            for persona in PERSONAS:
                directory = cls.root / (problem + "--" + persona)
                manifest = composer.compose_case(problem, persona, directory)
                cls.cases[problem, persona] = (directory, manifest)

    def test_all_sixteen_combinations_pass_existing_standalone_validation(self):
        self.assertEqual(len(self.cases), 16)
        for (problem, persona), (directory, returned) in self.cases.items():
            with self.subTest(problem=problem, persona=persona):
                manifest = validate_case(directory)
                self.assertEqual(returned, manifest)
                self.assertEqual(manifest["schema_version"], 1)
                self.assertEqual(manifest["suite_version"], "7.0.6")
                self.assertEqual(manifest["completion_contract"], "full_report")
                self.assertEqual(manifest["problem_id"], problem)
                self.assertEqual(manifest["persona_id"], persona)
                self.assertTrue(manifest["problem_version"])
                self.assertTrue(manifest["persona_version"])
                actual = inventory(directory)
                self.assertEqual(manifest["files"], {k: v for k, v in actual.items() if k != "case.json"})
                self.assertFalse(list(directory.rglob("__pycache__")))

    def test_composition_is_reproducible_and_does_not_modify_its_inputs(self):
        for (problem, persona), (directory, _) in self.cases.items():
            with self.subTest(problem=problem, persona=persona):
                replica = self.root / ("replica-" + problem + "--" + persona)
                composer.compose_case(problem, persona, replica)
                self.assertEqual(inventory(replica), inventory(directory))
        self.assertEqual(self.original_bank, inventory(ROOT / "problems"))
        self.assertEqual(self.original_personas, inventory(ROOT / "personas"))

    def test_persona_changes_cannot_change_scientific_world_or_source_access(self):
        for problem in PROBLEMS:
            baseline, expected = self.cases[problem, "novice"]
            reference = {name: sha for name, sha in expected["files"].items()
                         if (name.startswith("public/") and name != expected["initial_message"])
                         or name in ("world.json", "oracle.json", "check_oracle.py", "problem.json")}
            self.assertIn("world.json", reference)
            self.assertIn("oracle.json", reference)
            self.assertTrue(any(name.startswith("public/") for name in reference))
            for persona in PERSONAS:
                directory, manifest = self.cases[problem, persona]
                with self.subTest(problem=problem, persona=persona):
                    actual = {name: sha for name, sha in manifest["files"].items()
                              if (name.startswith("public/") and name != manifest["initial_message"])
                              or name in ("world.json", "oracle.json", "check_oracle.py", "problem.json")}
                    self.assertEqual(actual, reference)
                    self.assertEqual(manifest["sources"], expected["sources"])
                    self.assertEqual(manifest["completion_contract"], expected["completion_contract"])
                    self.assertEqual(manifest["world_id"], expected["world_id"])
                    self.assertEqual(manifest["world_version"], expected["world_version"])
                    world = read(directory / manifest["world"])
                    self.assertEqual(world, read(baseline / expected["world"]))

    def test_all_initial_requests_invoke_skill_and_retain_report_goal(self):
        for (problem, persona), (directory, manifest) in self.cases.items():
            with self.subTest(problem=problem, persona=persona):
                text = (directory / manifest["initial_message"]).read_text(encoding="utf-8")
                self.assertIn("causal-consultant", text)
                self.assertIn("report", text.lower())
                self.assertNotIn("target_turns", text)
                self.assertNotIn("oracle.json", text)
                self.assertNotIn("reviewer.json", text)

    def test_target_lengths_are_metadata_and_cap_does_not_change_actor(self):
        for problem, target in PROBLEMS.items():
            for persona in PERSONAS:
                directory, manifest = self.cases[problem, persona]
                with self.subTest(problem=problem, persona=persona):
                    self.assertEqual(manifest["target_turns"], target)
                    self.assertEqual(manifest["run_limits"]["consultant_turns"], 40)
                    actor = read(directory / manifest["actor"])
                    serialized = json.dumps(actor)
                    self.assertNotIn("target_turns", serialized)
                    self.assertNotIn("planned_turns", serialized)
                    expanded = self.root / ("cap50-" + problem + "--" + persona)
                    larger = composer.compose_case(problem, persona, expanded, max_consultant_turns=50)
                    self.assertEqual(larger["target_turns"], target)
                    self.assertEqual(larger["run_limits"]["consultant_turns"], 50)
                    self.assertEqual((directory / manifest["actor"]).read_bytes(),
                                     (expanded / larger["actor"]).read_bytes())
                    self.assertEqual((directory / manifest["initial_message"]).read_bytes(),
                                     (expanded / larger["initial_message"]).read_bytes())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="modular-existing-") as temporary:
            output = Path(temporary) / "occupied"
            output.mkdir()
            marker = output / "precious.txt"
            marker.write_text("Existing work must remain intact.", encoding="utf-8")
            before = inventory(output)
            with self.assertRaises((ValueError, FileExistsError)):
                composer.compose_case("study-design", "novice", output)
            self.assertEqual(before, inventory(output))
            empty = Path(temporary) / "empty"
            empty.mkdir()
            with self.assertRaises((ValueError, FileExistsError)):
                composer.compose_case("study-design", "novice", empty)
            self.assertEqual(list(empty.iterdir()), [])

    def test_invalid_selectors_do_not_create_an_output(self):
        invalid = [("unknown", "novice"), ("study-design", "unknown"),
                   ("../study-design", "novice"), ("study-design", "../novice")]
        with tempfile.TemporaryDirectory(prefix="modular-invalid-") as temporary:
            for index, (problem, persona) in enumerate(invalid):
                with self.subTest(problem=problem, persona=persona):
                    output = Path(temporary) / str(index)
                    with self.assertRaises((ValueError, KeyError, FileNotFoundError)):
                        composer.compose_case(problem, persona, output)
                    self.assertFalse(output.exists())

    def test_compiled_fixture_tampering_is_rejected_by_existing_driver(self):
        original, manifest = self.cases["data-quality-edge", "novice"]
        with tempfile.TemporaryDirectory(prefix="modular-tamper-") as temporary:
            output = Path(temporary) / "copied"
            shutil.copytree(original, output)
            source = output / manifest["sources"][0]["file"]
            source.write_bytes(source.read_bytes() + b"\nChanged after compilation.\n")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                validate_case(output)

    def test_actor_gets_only_its_knowledge_tier_and_legitimate_source_inventory(self):
        for (problem, persona), (directory, manifest) in self.cases.items():
            with self.subTest(problem=problem, persona=persona):
                definition = read(directory / "problem.json")
                profile = read(ROOT / "personas" / (persona + ".json"))
                actor = read(directory / manifest["actor"])
                self.assertEqual(actor["persona_profile"], profile)
                self.assertEqual(actor["goal"], definition["goal"])
                expected_facts = [{key: value for key, value in entry.items() if key != "knowledge_tier"}
                                  for entry in definition["actor_facts"]
                                  if entry["knowledge_tier"] in profile["initial_knowledge_tiers"]]
                self.assertEqual(actor["facts"], expected_facts)
                self.assertFalse({"scientific_truth", "oracle", "world", "reviewer", "initial_requests"} & actor.keys())
                source_map = {source["id"]: source for source in manifest["sources"]}
                self.assertEqual({item["source_id"] for item in actor["sources"]}, set(source_map))
                for source in actor["sources"]:
                    original = source_map[source["source_id"]]
                    self.assertEqual(source["file"], original["destination"])
                    self.assertEqual(source["availability"], original["availability"])
                    self.assertTrue(source["release"])
                fact_ids = {fact["fact_id"] for fact in actor["facts"]}
                for rule in actor["rules"]:
                    self.assertTrue(set(rule["fact_ids"]) <= fact_ids, rule["rule_id"])
                    self.assertTrue(set(rule["source_ids"]) <= set(source_map), rule["rule_id"])

    def test_private_definitions_and_answers_cannot_be_public_source_destinations(self):
        private = {"world.json", "oracle.json", "check_oracle.py", "problem.json", "persona.json",
                   "reviewer.json", "actor.json", "composition.json", "case.json"}
        for (problem, persona), (directory, manifest) in self.cases.items():
            with self.subTest(problem=problem, persona=persona):
                self.assertTrue(private <= set(inventory(directory)))
                self.assertFalse(any((directory / "public" / name).exists() for name in private))
                for source in manifest["sources"]:
                    self.assertTrue(source["file"].startswith("public/"))
                    self.assertNotIn(source["destination"], private)
                composition = read(directory / "composition.json")
                self.assertEqual(composition["problem_sha256"], inventory(directory)["problem.json"])
                self.assertEqual(composition["persona_sha256"], inventory(directory)["persona.json"])
                self.assertEqual(composition["composer_sha256"], hashlib.sha256(
                    (ROOT / "scripts/compose_case.py").read_bytes()).hexdigest())

    def test_changed_or_unexpected_input_files_fail_before_creating_output(self):
        with tempfile.TemporaryDirectory(prefix="modular-input-") as temporary:
            sandbox = Path(temporary)
            bank = sandbox / "problems"
            shutil.copytree(ROOT / "problems", bank)
            definition = read(bank / "study-design/problem.json")
            changed = bank / "study-design" / definition["sources"][0]["file"]
            original = changed.read_bytes()
            changed.write_bytes(original + b"\nThis is an unrecorded change.\n")
            with self.assertRaisesRegex(ValueError, "problem file identity mismatch"):
                composer.compose_case("study-design", "novice", sandbox / "changed", bank_root=bank)
            self.assertFalse((sandbox / "changed").exists())
            changed.write_bytes(original)
            (bank / "study-design/unexpected.txt").write_text("Not declared.", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "problem file identity mismatch"):
                composer.compose_case("study-design", "novice", sandbox / "unexpected", bank_root=bank)
            self.assertFalse((sandbox / "unexpected").exists())

    def test_persona_identity_mismatch_and_endpoint_overrides_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="modular-persona-") as temporary:
            sandbox = Path(temporary)
            personas = sandbox / "personas"
            shutil.copytree(ROOT / "personas", personas)
            profile = read(personas / "novice.json")
            for field, value in (("persona_id", "statistician"), ("goal", "Produce a favorable estimate"),
                                 ("sources", []), ("world", {}), ("target_turns", 1),
                                 ("completion_contract", "focused")):
                with self.subTest(field=field):
                    modified = {**profile, field: value}
                    (personas / "novice.json").write_text(json.dumps(modified), encoding="utf-8")
                    output = sandbox / ("output-" + field)
                    with self.assertRaisesRegex(ValueError, "identity mismatch|cannot override"):
                        composer.compose_case("study-design", "novice", output, personas_root=personas)
                    self.assertFalse(output.exists())

    def test_operational_limit_is_validated_independently_of_problem_target(self):
        with tempfile.TemporaryDirectory(prefix="modular-limit-") as temporary:
            for index, value in enumerate((0, -1, 1.5, True, "40")):
                with self.subTest(value=value):
                    output = Path(temporary) / ("invalid-" + str(index))
                    with self.assertRaisesRegex(ValueError, "positive integer"):
                        composer.compose_case("cate-policy", "novice", output, max_consultant_turns=value)
                    self.assertFalse(output.exists())
            # Operators may intentionally stop an incomplete run; a cap is not a completion rule.
            low = composer.compose_case("cate-policy", "novice", Path(temporary) / "low",
                                        max_consultant_turns=2)
            self.assertEqual(low["target_turns"], 15)
            self.assertEqual(low["run_limits"]["consultant_turns"], 2)
            self.assertEqual(low["completion_contract"], "full_report")

    def test_cli_lists_only_the_four_by_four_catalog_and_composes_a_valid_case(self):
        script = ROOT / "scripts/compose_case.py"
        listed = subprocess.run([sys.executable, "-B", str(script), "--list"],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        catalog = json.loads(listed.stdout)
        self.assertEqual(catalog["combinations"], 16)
        self.assertEqual({item["id"]: item["target_turns"] for item in catalog["problems"]}, PROBLEMS)
        self.assertEqual({item["id"] for item in catalog["personas"]}, set(PERSONAS))
        with tempfile.TemporaryDirectory(prefix="modular-cli-") as temporary:
            output = Path(temporary) / "case"
            result = subprocess.run([sys.executable, "-B", str(script), "--problem", "observational-did",
                                     "--persona", "statistician", "--output", str(output),
                                     "--max-consultant-turns", "50"],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = validate_case(output)
            self.assertEqual(json.loads(result.stdout)["case_id"], manifest["case_id"])
            self.assertEqual(manifest["run_limits"]["consultant_turns"], 50)

    def test_design_problem_contains_planning_units_and_no_trial_outcomes(self):
        directory, _ = self.cases["study-design", "novice"]
        centers = rows(directory / "public/centers.csv")
        planning = read(directory / "public/planning-inputs.json")
        oracle = read(directory / "oracle.json")
        self.assertEqual(len(centers), len({row["center_id"] for row in centers}))
        self.assertEqual(len(centers), 24)
        self.assertEqual(Counter(row["region"] for row in centers), {"North": 12, "South": 12})
        self.assertEqual(sum(int(row["planned_eligible_learners"]) for row in centers), 960)
        self.assertEqual(set(centers[0]), {"center_id", "region", "planned_eligible_learners", "historical_mean_score"})
        self.assertIs(oracle["specification"]["future_outcomes_exist"], False)
        retained = planning["learners_per_center"] * (1 - planning["anticipated_attrition_fraction"])
        expected = oracle["expected"]
        self.assertAlmostEqual(retained, expected["retained_per_center_assumption"])
        for icc in planning["icc_assumptions"]:
            self.assertAlmostEqual(1 + (retained - 1) * icc,
                                   expected["design_effects_at_retained_size"][str(icc)])
        # Planning MDE, not observed effect or exact finite-cluster power.
        normal_multiplier = 1.959963984540054 + 0.8416212335729143
        variance = 4 * planning["outcome_sd_assumption"] ** 2 * (1 + (retained - 1) * 0.05)
        variance /= retained * len(centers)
        self.assertAlmostEqual(normal_multiplier * math.sqrt(variance), expected["normal_approx_mde_at_icc_005"])

    def test_did_reference_keeps_all_site_ate_distinct_from_adopter_att(self):
        directory, _ = self.cases["observational-did", "statistician"]
        panel = rows(directory / "public/panel.csv")
        roster = rows(directory / "public/site-roster.csv")
        self.assertEqual(len(panel), 600)
        self.assertEqual(len(roster), 120)
        self.assertEqual(len({(r["site_id"], r["year"]) for r in panel}), 600)
        lookup = {(r["site_id"], int(r["year"])): Fraction(r["mean_skill_score"]) for r in panel}
        changes = {r["site_id"]: (lookup[r["site_id"], 2025] + lookup[r["site_id"], 2026]) / 2
                   - lookup[r["site_id"], 2024] for r in roster}
        effects = {}
        for readiness in ("0", "1"):
            groups = [[changes[r["site_id"]] for r in roster
                       if r["readiness_high"] == readiness and r["adopted_2025"] == arm]
                      for arm in ("0", "1")]
            self.assertEqual([len(g) for g in groups], [45, 15] if readiness == "0" else [15, 45])
            effects[readiness] = sum(groups[1]) / len(groups[1]) - sum(groups[0]) / len(groups[0])
        ate = sum(effects.values()) / 2
        att = effects["0"] / 4 + effects["1"] * 3 / 4
        oracle = read(directory / "oracle.json")
        self.assertAlmostEqual(float(ate), oracle["expected"]["standardized_ate_reference"])
        self.assertAlmostEqual(float(att), oracle["expected"]["att_reference"])
        self.assertGreater(abs(float(ate - att)), 0.5)
        self.assertEqual(oracle["specification"]["generating_ate"], 4)
        self.assertEqual(oracle["specification"]["generating_att"], 5)
        # Realized estimates have noise; fixture grading must not demand private truth recovery.
        self.assertNotEqual(float(ate), 4)
        self.assertNotEqual(float(att), 5)

    def test_cate_data_splits_and_capacity_constrained_benchmark_are_coherent(self):
        directory, _ = self.cases["cate-policy", "domain-expert"]
        datasets = {split: rows(directory / ("public/" + split + ".csv"))
                    for split in ("development", "evaluation")}
        ids = {split: {r["learner_id"] for r in data} for split, data in datasets.items()}
        self.assertFalse(ids["development"] & ids["evaluation"])
        oracle = read(directory / "oracle.json")
        for split, data in datasets.items():
            self.assertEqual(len(data), 1800 if split == "development" else 600)
            self.assertEqual(len(data), len(ids[split]))
            counts = Counter((r["readiness_high"], r["barrier_flag"], r["baseline_band"]) for r in data)
            self.assertEqual(len(counts), 8)
            self.assertEqual(set(counts.values()), {225 if split == "development" else 75})
            self.assertTrue(all(r["offer"] in ("0", "1") and r["skill_gain"] for r in data))
            selected = [r for r in data if r["readiness_high"] == "1"
                        and (r["barrier_flag"] == "1" or r["baseline_band"] == "0.5")]
            self.assertEqual(Fraction(len(selected), len(data)), Fraction(3, 8))
            offer_total = sum(Fraction(r["skill_gain"]) for r in selected if r["offer"] == "1")
            no_offer_total = sum(Fraction(r["skill_gain"]) for r in selected if r["offer"] == "0")
            gain = (2 * (offer_total - no_offer_total) - 2 * len(selected)) / len(data)
            self.assertAlmostEqual(float(gain), oracle["expected"]["partitions"][split]["fixed_benchmark_ipw_net_gain"])
            scores = {cell: [] for cell in counts}
            for row in data:
                cell = (row["readiness_high"], row["barrier_flag"], row["baseline_band"])
                policy = int(row["readiness_high"] == "1" and
                             (row["barrier_flag"] == "1" or row["baseline_band"] == "0.5"))
                scores[cell].append(policy * (2 * (2 * int(row["offer"]) - 1)
                                              * Fraction(row["skill_gain"]) - 2))
            # Fixed cell sizes call for cell-specific sampling variance, not between-cell variation.
            stratified_variance = sum((sum(value * value for value in group)
                                       - sum(group) ** 2 / len(group))
                                      / (len(group) - 1) / len(group) / 64
                                      for group in scores.values())
            self.assertAlmostEqual(math.sqrt(float(stratified_variance)),
                                   oracle["expected"]["partitions"][split]["fixed_benchmark_stratified_score_se"])
        cells = list(itertools.product((0, 1), (0, 1), (-0.5, 0.5)))
        effects = [-1 + 4 * h + 2 * b + s for h, b, s in cells]
        self.assertEqual(sum(effects) / len(cells), 2)
        best_three = sorted((effect - 2 for effect in effects), reverse=True)[:3]
        self.assertEqual(sum(best_three) / len(cells), 0.9375)
        self.assertEqual(oracle["expected"]["benchmark_policy_generating_net_gain"], 0.9375)

    def test_cate_evaluation_access_is_a_scientific_prerequisite_for_every_persona(self):
        for persona in PERSONAS:
            directory, manifest = self.cases["cate-policy", persona]
            actor = read(directory / "actor.json")
            evaluation = next(source for source in manifest["sources"] if source["id"] == "s-evaluation")
            self.assertEqual(evaluation["availability"], "on_request")
            actor_source = next(source for source in actor["sources"] if source["source_id"] == "s-evaluation")
            self.assertIn("saved fixed candidate rule", actor_source["release"])
            rules = {rule["rule_id"]: rule for rule in actor["rules"]}
            self.assertIn("s-evaluation", rules["r-evaluation-release"]["source_ids"])
            self.assertIn("s-evaluation-access", rules["r-evaluation-release"]["source_ids"])
            # A broad records request must preserve the particular evaluation release condition.
            problem_rules = read(directory / "problem.json")["actor_rules"]
            for rule in problem_rules:
                if rule["rule_id"] != "r-evaluation-release":
                    self.assertNotIn("s-evaluation", rule["source_ids"])

    def test_edge_person_level_denominators_and_completion_bounds_are_independent(self):
        directory, _ = self.cases["data-quality-edge", "adversarial"]
        extract = rows(directory / "public/extract.csv")
        roster = rows(directory / "public/participant-roster.csv")
        by_id = {}
        duplicates = []
        for row in extract:
            if row["participant_id"] in by_id:
                self.assertEqual(row, by_id[row["participant_id"]])
                duplicates.append(row["participant_id"])
            by_id[row["participant_id"]] = row
        self.assertEqual((len(extract), len(by_id), len(duplicates)), (132, 120, 12))
        self.assertEqual(set(by_id), {r["participant_id"] for r in roster})
        people = list(by_id.values())
        self.assertEqual(sum(r["baseline_score"] == "" for r in people), 18)
        missing = sum(r["completed_12weeks"] == "" for r in people)
        successes = sum(r["completed_12weeks"] == "1" for r in people)
        self.assertEqual((missing, successes), (30, 60))
        self.assertEqual({r["program_received"] for r in people}, {"1"})
        self.assertEqual(Fraction(successes, len(people) - missing), Fraction(2, 3))
        bounds = [successes / len(people), (successes + missing) / len(people)]
        self.assertEqual(bounds, [0.5, 0.75])
        oracle = read(directory / "oracle.json")
        self.assertEqual(bounds, oracle["expected"]["cohort_success_bounds"])
        self.assertIs(oracle["specification"]["known_causal_truth"], False)

    def test_problem_bank_reproduces_from_shared_stdlib_generator_without_writes(self):
        import generate_problem_bank as generator
        before = inventory(ROOT / "problems")
        for problem in PROBLEMS:
            regenerated = generator.build(problem)
            directory = ROOT / "problems" / problem
            self.assertEqual(set(regenerated), set(inventory(directory)))
            for filename, expected in regenerated.items():
                self.assertEqual((directory / filename).read_bytes(), expected, problem + "/" + filename)
        self.assertEqual(inventory(ROOT / "problems"), before)


if __name__ == "__main__":
    unittest.main()
