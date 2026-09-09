"""Frozen fixture integrity and scientific contrast checks, not model grading."""
import csv
from fractions import Fraction
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from session_driver import validate_case
from generate_investigation_cases import KINDS, build


def case(kind):
    return ROOT / "cases" / ("investigation-" + kind + "-v7")


def read(kind, name):
    return json.loads((case(kind) / name).read_text(encoding="utf-8"))


def rows(kind):
    with (case(kind) / "public/data.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class InvestigationCases(unittest.TestCase):
    def test_all_standalone_cases_validate_and_reproduce_frozen_bytes(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                manifest = validate_case(case(kind))
                self.assertEqual(manifest["case_version"], "1.0.1")
                self.assertEqual(manifest["suite_version"], "7.0.2")
                identity, recreated = build(kind)
                self.assertEqual(identity, manifest["case_id"])
                self.assertEqual(set(recreated), set(manifest["files"]) | {"case.json"})
                for name, content in recreated.items():
                    self.assertEqual((case(kind) / name).read_bytes(), content.encode("utf-8"), name)

    def test_release_rules_refer_to_real_available_sources_and_facts(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                manifest = read(kind, "case.json")
                actor = read(kind, "actor.json")
                known_facts = {f["fact_id"] for f in actor["facts"]}
                sources = {s["id"]: s for s in manifest["sources"]}
                released = set()
                for rule in actor["rules"]:
                    self.assertTrue(set(rule["fact_ids"]) <= known_facts)
                    for source in rule["source_ids"]:
                        self.assertIn(source, sources)
                        self.assertEqual(sources[source]["availability"], "on_request")
                        released.add(source)
                self.assertEqual(released, {key for key, value in sources.items() if value["availability"] == "on_request"})
                for fact in actor["facts"]:
                    for field in ("statement", "certainty", "source", "available_when", "disclosure_condition"):
                        self.assertTrue(fact[field])

    def test_allocation_pair_changes_access_not_observed_science(self):
        left, right = "allocation-recoverable", "allocation-lost"
        for filename in ("public/data.csv", "public/dictionary.md", "public/initial-message.txt", "oracle.json"):
            self.assertEqual((case(left) / filename).read_bytes(), (case(right) / filename).read_bytes())
        recoverable_sources = {s["id"]: s for s in read(left, "case.json")["sources"]}
        lost_sources = {s["id"]: s for s in read(right, "case.json")["sources"]}
        self.assertEqual(set(recoverable_sources) - set(lost_sources), {"s-allocation"})
        self.assertEqual(recoverable_sources["s-allocation"]["availability"], "on_request")
        self.assertFalse((case(right) / "public/records/allocation-record.md").exists())
        self.assertNotEqual((case(left) / "public/available-records.md").read_bytes(),
                            (case(right) / "public/available-records.md").read_bytes())

    def test_anomaly_is_only_in_separate_prior_cohort(self):
        for kind in ("allocation-recoverable", "allocation-lost", "scope-intermediate", "scope-closed"):
            values = rows(kind)
            bad_baselines = [row["site_id"] for row in values if not 0 <= float(row["baseline_completion_pct"]) <= 100]
            self.assertEqual(bad_baselines, ["S07"])
            self.assertTrue(all(0 <= int(row["completion_2024_pct"]) <= 100 for row in values))
            self.assertEqual({int(row["entrants"]) for row in values}, {100})
            self.assertEqual(len(values), len({row["site_id"] for row in values}))

    def test_timing_pair_has_coherent_changed_world_and_unchanged_initial_explanation(self):
        aligned, late = "timing-aligned", "timing-late"
        for name in ("public/initial-message.txt", "public/dictionary.md", "public/study-notes.md", "public/available-records.md"):
            self.assertEqual((case(aligned) / name).read_bytes(), (case(late) / name).read_bytes())
        before = read(aligned, "oracle.json")["world"]
        after = read(late, "oracle.json")["world"]
        self.assertLess(before["assignment_date"], before["outcome_date"])
        self.assertGreater(after["assignment_date"], after["outcome_date"])
        self.assertEqual(before["outcome_date"], after["outcome_date"])
        self.assertEqual(before["assignment_effect"], 6)
        self.assertEqual(after["assignment_effect"], 0)
        for first, second in zip(rows(aligned), rows(late)):
            for field in set(first) - {"completion_2024_pct"}:
                self.assertEqual(first[field], second[field])
            self.assertEqual(int(first["completion_2024_pct"]) - int(second["completion_2024_pct"]),
                             6 * int(first["grant_offer"]))
        for kind in (aligned, late):
            source = next(s for s in read(kind, "case.json")["sources"] if s["id"] == "s-calendar")
            self.assertEqual(source["availability"], "on_request")

    def test_scope_pair_changes_user_choice_not_initial_material_or_science(self):
        intermediate, closed = "scope-intermediate", "scope-closed"
        first = read(intermediate, "case.json")
        second = read(closed, "case.json")
        self.assertEqual(first["sources"], second["sources"])
        for filename in first["files"]:
            if filename.startswith("public/") or filename == "oracle.json":
                self.assertEqual((case(intermediate) / filename).read_bytes(), (case(closed) / filename).read_bytes())
        first_actor = read(intermediate, "actor.json")
        second_actor = read(closed, "actor.json")
        first_facts = {f["fact_id"]: f for f in first_actor["facts"]}
        second_facts = {f["fact_id"]: f for f in second_actor["facts"]}
        self.assertEqual(first_facts.keys(), second_facts.keys())
        self.assertEqual([key for key in first_facts if first_facts[key] != second_facts[key]], ["f-scope-preference"])
        self.assertEqual(second_actor["rules"][0]["rule_id"], "r-close-scope")

    def test_ready_pair_has_same_data_and_only_selection_document_withheld(self):
        complete, missing = "design-complete", "design-missing"
        for filename in ("public/data.csv", "public/dictionary.md", "public/initial-message.txt", "oracle.json"):
            self.assertEqual((case(complete) / filename).read_bytes(), (case(missing) / filename).read_bytes())
        source = next(s for s in read(missing, "case.json")["sources"] if s["id"] == "s-allocation")
        self.assertEqual(source["availability"], "on_request")
        self.assertFalse(any(s["availability"] == "on_request" for s in read(complete, "case.json")["sources"]))
        # Full protocol/log bytes are identical when available; only presentation differs.
        complete_text = (case(complete) / "public/study-notes.md").read_text().split("\n\n", 1)[1]
        missing_text = (case(missing) / source["file"]).read_text().split("\n\n", 1)[1]
        self.assertEqual(complete_text, missing_text)

    def test_ready_reference_uses_realized_estimator_not_generating_truth(self):
        values = rows("design-complete")
        observed = read("design-complete", "oracle.json")["expected"]["statistics"]
        treated = [int(r["score"]) for r in values if r["grant_offer"] == "1"]
        control = [int(r["score"]) for r in values if r["grant_offer"] == "0"]
        estimate = Fraction(sum(treated) - sum(control), 6)
        # Raw second moments provide another route independent of centered moments.
        variance = sum((Fraction(sum(y * y for y in group)) - Fraction(sum(group) ** 2, 6)) / 30
                       for group in (treated, control))
        self.assertAlmostEqual(float(estimate), observed["difference_offered_minus_control"])
        self.assertNotEqual(float(estimate), 3)
        self.assertAlmostEqual(float(variance), observed["neyman_variance"])
        all_scores = [int(r["score"]) for r in values]
        comparisons = [abs(Fraction(2 * sum(group) - sum(all_scores), 6))
                       for group in itertools.combinations(all_scores, 6)]
        self.assertEqual(len(comparisons), 924)
        extreme = sum(value >= abs(estimate) for value in comparisons)
        self.assertEqual(extreme, observed["sharp_null_two_sided"]["extreme"])
        self.assertAlmostEqual(extreme / 924, observed["sharp_null_two_sided"]["p_value"])

    def test_self_check_runs_without_maintenance_generator_or_other_cases(self):
        fixture = case("design-complete")
        with tempfile.TemporaryDirectory(prefix="causal-fixture-check-") as directory:
            target = Path(directory)
            for filename in ("check_oracle.py", "oracle.json", "public/data.csv"):
                destination = target / filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((fixture / filename).read_bytes())
            result = subprocess.run([sys.executable, "-B", str(target / "check_oracle.py")],
                                    capture_output=True, text=True, timeout=30, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
