"""Source gates bind prior public commitments to saved bytes, not scientific truth."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from source_release import (POLICY_EVALUATION_COMPONENTS, policy_evaluation_prerequisite,
                            source_release_observations, validate_release_receipts, validate_source_prerequisite)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class SourceReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="source-release-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.attempt, self.work = self.root / "attempt", self.root / "work"
        self.sources = {
            "s-evaluation": {"id": "s-evaluation", "file": "public/evaluation.csv",
                "destination": "evaluation.csv", "availability": "on_request",
                "release_prerequisite": policy_evaluation_prerequisite()},
            "s-dictionary": {"id": "s-dictionary", "file": "public/dictionary.md",
                "destination": "dictionary.md", "availability": "on_request"}}
        self.state = {"turns": 2, "work": str(self.work)}
        self.artifact = "analysis/commitment.md"
        self.quotes = {
            "candidate_rule": "Use the development-selected rule saved here: offer when baseline readiness is high.",
            "utility": "Evaluate gain minus the documented offer cost.",
            "comparators": "Compare with no offers and the capacity-constrained lottery.",
            "evaluation_procedure": "Use the fixed randomized-offer IPW score and a design-appropriate standard error; no nuisance fitting."}
        self.content = "\n".join(self.quotes.values()) + "\n"
        self.sha = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        self.current = self.work / self.artifact
        self.snapshot = self.attempt / "events/001/work-snapshot" / self.artifact
        for path in (self.current, self.snapshot):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.content, encoding="utf-8", newline="")
        self.public = "I have fixed the candidate and evaluation choices and saved analysis/commitment.md. Please send the evaluation data."
        write(self.attempt / "events/001/public.json", {"user": "Please proceed.", "assistant": self.public})
        write(self.attempt / "events/001/work-files.json", {self.artifact: self.sha})
        self.receipt = {"source_id": "s-evaluation", "public_turn": 1, "public_quote": self.public,
                        "commitments": {component: {"artifact": self.artifact, "sha256": self.sha,
                                                    "quote": quote} for component, quote in self.quotes.items()}}

    def check(self, receipts=None, attachments=None):
        return validate_release_receipts(self.attempt, self.state, self.sources,
                                         ["s-evaluation"] if attachments is None else attachments,
                                         [self.receipt] if receipts is None else receipts)

    def test_saved_public_commitment_allows_release_without_heldout_file_or_hash(self):
        before = {path.relative_to(self.root).as_posix(): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        checked = self.check()
        self.assertEqual(len(checked), 1)
        self.assertEqual(checked[0]["source_id"], "s-evaluation")
        self.assertEqual(checked[0]["receipt"], self.receipt)
        self.assertIn("events/001/work-snapshot/analysis/commitment.md", checked[0]["evidence_refs"])
        self.assertIn("semantic adequacy requires review", checked[0]["scope"])
        self.assertFalse((self.work / "evaluation.csv").exists())
        self.assertEqual(before, {path.relative_to(self.root).as_posix(): path.read_bytes()
                                 for path in self.root.rglob("*") if path.is_file()})

    def test_ordinary_requested_bundle_needs_no_commitment(self):
        self.assertEqual(self.check([], ["s-dictionary"]), [])
        self.assertEqual(self.check([], []), [])
        self.assertEqual(self.check(attachments=["s-dictionary", "s-evaluation"])[0]["source_id"], "s-evaluation")

    def test_no_receipt_or_only_a_public_promise_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing saved commitment receipt"):
            self.check([])
        self.snapshot.unlink()
        with self.assertRaisesRegex(ValueError, "artifact was not saved"):
            self.check()

    def test_reference_must_be_an_actual_earlier_public_assistant_turn(self):
        for turn in (0, -1, True, "1", 3, 99):
            receipt = {**self.receipt, "public_turn": turn}
            with self.subTest(turn=turn), self.assertRaisesRegex(ValueError, "earlier completed public turn"):
                self.check([receipt])
        with self.assertRaisesRegex(ValueError, "must be retained"):
            self.check([{**self.receipt, "public_turn": 2}])
        with self.assertRaisesRegex(ValueError, "absent from the earlier assistant"):
            self.check([{**self.receipt, "public_quote": "I fixed a different rule."}])
        write(self.attempt / "events/001/public.json", {"user": self.public, "assistant": "I will do that later."})
        with self.assertRaisesRegex(ValueError, "absent from the earlier assistant"):
            self.check()

    def test_public_statement_must_identify_the_saved_artifact(self):
        for message in ("I fixed the rule and saved it.",
                        "I saved other-analysis/commitment.md.",
                        "I saved analysis/commitment.md.backup."):
            write(self.attempt / "events/001/public.json", {"assistant": message})
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, "identified in the public"):
                self.check([{**self.receipt, "public_quote": message}])

    def test_public_links_and_windows_path_spelling_can_identify_saved_files(self):
        for message in ("Saved and fixed: [plan](analysis/commitment.md)",
                        "Saved and fixed: C:\\study\\analysis\\commitment.md"):
            write(self.attempt / "events/001/public.json", {"assistant": message})
            self.assertEqual(len(self.check([{**self.receipt, "public_quote": message}])), 1)

    def test_all_four_saved_components_are_required_and_quotes_must_exist(self):
        for component in POLICY_EVALUATION_COMPONENTS:
            missing = copy.deepcopy(self.receipt)
            del missing["commitments"][component]
            with self.subTest(missing=component), self.assertRaisesRegex(ValueError, "all four"):
                self.check([missing])
            fabricated = copy.deepcopy(self.receipt)
            fabricated["commitments"][component]["quote"] = "Text absent from the saved commitment."
            with self.subTest(fabricated=component), self.assertRaisesRegex(ValueError, "commitment quote"):
                self.check([fabricated])

    def test_artifact_hash_must_match_the_prior_inventory_snapshot_and_current_file(self):
        wrong = copy.deepcopy(self.receipt)
        wrong["commitments"]["candidate_rule"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "artifact was not saved"):
            self.check([wrong])
        self.snapshot.write_text(self.content + "Retained evidence changed.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "retained saved artifact hash mismatch"):
            self.check()
        self.snapshot.write_text(self.content, encoding="utf-8", newline="")
        self.current.write_text(self.content + "Candidate changed after its public commitment.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed or disappeared"):
            self.check()

    def test_multiple_saved_component_files_are_supported(self):
        path = "analysis/candidate.txt"
        content = self.quotes["candidate_rule"]
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        for artifact in (self.work / path, self.attempt / "events/001/work-snapshot" / path):
            artifact.write_text(content, encoding="utf-8")
        write(self.attempt / "events/001/work-files.json", {self.artifact: self.sha, path: sha})
        public = self.public + " The fixed rule is also saved in analysis/candidate.txt."
        write(self.attempt / "events/001/public.json", {"assistant": public})
        receipt = copy.deepcopy(self.receipt)
        receipt["public_quote"] = public
        receipt["commitments"]["candidate_rule"] = {"artifact": path, "sha256": sha, "quote": content}
        self.assertEqual(len(self.check([receipt])), 1)

    def test_unrelated_duplicate_or_unsafe_receipts_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check([self.receipt, self.receipt])
        with self.assertRaisesRegex(ValueError, "requested gated source"):
            self.check([{**self.receipt, "source_id": "s-dictionary"}])
        for path in ("../private.md", "/absolute.md", "C:/private.md", "analysis/../private.md"):
            receipt = copy.deepcopy(self.receipt)
            receipt["commitments"]["candidate_rule"]["artifact"] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "invalid artifact path"):
                self.check([receipt])

    def test_metadata_is_specific_and_cannot_make_the_holdout_initial(self):
        validate_source_prerequisite(self.sources["s-dictionary"])
        validate_source_prerequisite(self.sources["s-evaluation"])
        for prerequisite in (None, {}, {"kind": "unknown", "required_components": []},
                             {"kind": "saved-policy-evaluation-commitment-v1", "required_components": ["candidate_rule"]}):
            with self.subTest(prerequisite=prerequisite), self.assertRaisesRegex(ValueError, "prerequisite"):
                validate_source_prerequisite({**self.sources["s-evaluation"], "release_prerequisite": prerequisite})
        with self.assertRaisesRegex(ValueError, "cannot be initial"):
            validate_source_prerequisite({**self.sources["s-evaluation"], "availability": "initial"})

    def trace_index(self):
        return {"files": {"private/" + path.relative_to(self.attempt).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in self.attempt.rglob("*") if path.is_file()}}

    def trace_fixture(self, *, release=True):
        source = self.sources["s-evaluation"]
        content = b"id,outcome\n1,8\n2,11\n"
        sha = hashlib.sha256(content).hexdigest()
        alias = "analysis/inputs/0001.csv"
        for path in (self.attempt / "case" / source["file"],
                     self.attempt / "events/002/work-snapshot" / alias):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        write(self.attempt / "events/001/releases.json", {})
        write(self.attempt / "events/002/work-files.json", {alias: sha})
        write(self.attempt / "events/002/releases.json",
              {source["id"]: {"path": source["destination"], "sha256": sha}} if release else {})
        write(self.attempt / "events/002/source-release-check.json", {"verified_receipts": self.check() if release else []})
        frozen = {"case_manifest": {"sources": [source], "files": {source["file"]: sha}}}
        return frozen, alias

    def test_renamed_source_without_release_is_acquisition_unverified(self):
        frozen, alias = self.trace_fixture(release=False)
        index = self.trace_index()
        observed = source_release_observations(self.attempt, frozen, index)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]["status"], "acquisition_unverified")
        self.assertEqual(observed[0]["source_id"], "s-evaluation")
        self.assertEqual(observed[0]["first_observed_event"], 2)
        self.assertEqual(observed[0]["first_observed_path"], alias)
        self.assertIn("does not establish when they were accessed or used", observed[0]["meaning"])
        self.assertTrue(all(ref in index["files"] for ref in observed[0]["evidence_refs"]))

    def test_valid_release_trace_adds_no_finding_and_does_not_change_evidence(self):
        frozen, _ = self.trace_fixture()
        before = self.trace_index()
        self.assertEqual(source_release_observations(self.attempt, frozen, before), [])
        self.assertEqual(self.trace_index(), before)

    def test_empty_gated_receipt_is_distinct_from_unreadable_receipt(self):
        frozen, _ = self.trace_fixture()
        target = self.attempt / "events/002/source-release-check.json"
        write(target, {"verified_receipts": []})
        observed = source_release_observations(self.attempt, frozen, self.trace_index())
        self.assertEqual(observed[0]["status"], "receipt_unverified")
        self.assertEqual(observed[0]["missing_receipt_events"], [2])
        target.write_text("{", encoding="utf-8")
        observed = source_release_observations(self.attempt, frozen, self.trace_index())
        self.assertEqual(observed[0]["status"], "evidence_gap")
        self.assertTrue(observed[0]["evidence_gaps"])
        target.unlink()
        observed = source_release_observations(self.attempt, frozen, self.trace_index())
        self.assertEqual(observed[0]["status"], "evidence_gap")
        self.assertNotIn("private/events/002/source-release-check.json", observed[0]["evidence_refs"])

    def test_changed_or_unindexed_snapshot_cannot_establish_source_appearance(self):
        frozen, alias = self.trace_fixture(release=False)
        snapshot = self.attempt / "events/002/work-snapshot" / alias
        index = self.trace_index()
        snapshot.write_bytes(b"changed data")
        observed = source_release_observations(self.attempt, frozen, index)
        self.assertEqual(observed[0]["status"], "evidence_gap")
        self.assertNotIn("first_observed_event", observed[0])
        ref = "private/events/002/work-snapshot/" + alias
        self.assertNotIn(ref, observed[0]["evidence_refs"])
        del index["files"][ref]
        observed = source_release_observations(self.attempt, frozen, index)
        self.assertEqual(observed[0]["status"], "evidence_gap")
        self.assertNotIn("first_observed_event", observed[0])

    def test_missing_prior_release_record_is_an_evidence_gap(self):
        frozen, _ = self.trace_fixture(release=False)
        (self.attempt / "events/001/releases.json").unlink()
        observed = source_release_observations(self.attempt, frozen, self.trace_index())
        self.assertEqual(observed[0]["status"], "evidence_gap")
        self.assertEqual(observed[0]["first_observed_event"], 2)

    def test_later_release_cannot_establish_the_earlier_acquisition(self):
        frozen, _ = self.trace_fixture(release=False)
        source = frozen["case_manifest"]["sources"][0]
        write(self.attempt / "events/003/releases.json", {source["id"]: {
            "path": source["destination"], "sha256": frozen["case_manifest"]["files"][source["file"]]}})
        write(self.attempt / "events/003/source-release-check.json", {"verified_receipts": self.check()})
        observed = source_release_observations(self.attempt, frozen, self.trace_index())
        self.assertEqual(observed[0]["status"], "acquisition_unverified")
        self.assertEqual(observed[0]["first_observed_event"], 2)

    def test_unseen_unreleased_source_adds_no_finding(self):
        frozen, _ = self.trace_fixture(release=False)
        write(self.attempt / "events/002/work-files.json", {})
        self.assertEqual(source_release_observations(self.attempt, frozen, self.trace_index()), [])


if __name__ == "__main__":
    unittest.main()
