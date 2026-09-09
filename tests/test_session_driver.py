import copy
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import session_driver as driver


class SessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = ROOT.parent / "causal-consultant"
        cls.node = shutil.which("node")
        if not cls.node or not cls.candidate.is_dir():
            raise RuntimeError("Integration tests require a shared Node and the sibling consultant 7.0.0, 7.0.1 or 7.0.2 package")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = self.root / "case"
        shutil.copytree(ROOT / "cases/college-policy-v7", self.case)
        self.attempt, self.work = self.root / "private", self.root / "work"
        self.config = {"claude_command": [sys.executable, str(ROOT / "tests/fake_claude.py"), "ok"],
                       "node_command": [self.node], "max_agent_turns_per_call": 10,
                       "call_timeout_seconds": 10, "mode": "diagnostic",
                       "limits": {"consultant_turns": 10, "active_seconds": 60, "elapsed_seconds": 120}}

    def begin(self):
        return driver.start(self.case, self.candidate, self.config, self.attempt, self.work)

    def reply(self, initial=False, **updates):
        record = {"message": (self.case / "public/initial-message.txt").read_text() if initial else "No spending plan has been agreed.",
                  "fact_ids": [] if initial else ["f-policy"], "rule_ids": [] if initial else ["r-answer"],
                  "attachments": [], "unanswered_questions": [], "fixture_gaps": [], "stop": False}
        return {**record, **updates}

    def manifest(self):
        manifest = driver.read(self.case / "case.json")
        manifest["files"] = {name: sha for name, sha in driver.inventory(self.case).items() if name != "case.json"}
        driver.write(self.case / "case.json", manifest)

    def assessment(self):
        view = driver.inspect(self.attempt, "reviewer")
        return {"evidence_sha256": view["evidence_sha256"], "test_validity": "valid", "outcome": "objective_met",
                "stop_reason": "Test-only reviewer assertion", "reviewer": "test-double",
                "coverage": {c["id"]: {"status": "observed", "reason": "Test-only coverage", "evidence_refs": ["private/events/001/public.json"]}
                             for c in driver.read(self.case / "reviewer.json")["criteria"]}, "findings": []}

    def test_stages_complete_candidate_and_public_only_then_resumes(self):
        result = self.begin()
        self.assertFalse(result["initial_message_sent"])
        self.assertFalse((self.work / "fake-session.txt").exists())
        self.assertTrue((self.work / ".claude/skills/causal-consultant/package.json").is_file())
        self.assertEqual(driver.digest(self.work / "data.csv"), driver.digest(self.case / "public/data.csv"))
        self.assertFalse((self.work / "actor.json").exists())
        driver.step(self.attempt, self.reply(initial=True))
        driver.step(self.attempt, self.reply())
        actor = driver.inspect(self.attempt, "actor")
        self.assertEqual(len(actor["conversation"]), 2)
        self.assertEqual(set(actor), {"conversation", "public_files"})
        self.assertNotIn("fact_ids", str(actor))
        self.assertEqual(driver.read(self.attempt / "state.json")["turns"], 2)

    def test_missing_package_json_fails_before_consultation(self):
        broken = self.root / "broken"
        shutil.copytree(self.candidate, broken, ignore=shutil.ignore_patterns(".git", "node_modules"))
        (broken / "package.json").unlink()
        with self.assertRaises(FileNotFoundError):
            driver.start(self.case, broken, self.config, self.attempt, self.work)
        self.assertTrue((self.attempt / "startup-error.json").exists())
        self.assertFalse(self.work.exists())

    def test_candidate_inventory_accepts_only_explicit_compatible_versions(self):
        candidate = self.root / "version-probe"
        candidate.mkdir()
        (candidate / "SKILL.md").write_text("Test-only runtime file.", encoding="utf-8")
        for version in ("7.0.0", "7.0.1", "7.0.2"):
            with self.subTest(version=version):
                driver.write(candidate / "package.json", {"version": version, "files": ["SKILL.md"]})
                self.assertEqual(driver.candidate_inventory(candidate), {
                    "SKILL.md": driver.digest(candidate / "SKILL.md"),
                    "package.json": driver.digest(candidate / "package.json")})
        for version in ("6.9.9", "7.0.3", "7.1.0", "7.0.2-preview"):
            with self.subTest(version=version):
                driver.write(candidate / "package.json", {"version": version, "files": ["SKILL.md"]})
                with self.assertRaisesRegex(ValueError, "observation profile"):
                    driver.candidate_inventory(candidate)

    def test_corrupt_or_unexpected_fixture_inputs_fail(self):
        for name in ("public/data.csv", "actor.json"):
            original = (self.case / name).read_bytes()
            (self.case / name).write_bytes(original + b" ")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                driver.validate_case(self.case)
            (self.case / name).write_bytes(original)
        (self.case / "unexpected.txt").write_text("extra")
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            driver.validate_case(self.case)

    def test_numeric_oracle_catches_coherently_rehashed_changed_data(self):
        data = self.case / "public/data.csv"
        data.write_bytes(data.read_bytes().replace(b",118\r\n", b",18\r\n"))
        self.manifest()
        with self.assertRaisesRegex(ValueError, "self-check failed"):
            driver.validate_case(self.case)

    def test_authorized_source_release_is_separate_from_actor_text(self):
        (self.case / "public/note.txt").write_text("A public note.")
        manifest = driver.read(self.case / "case.json")
        manifest["sources"].append({"id": "s-note", "file": "public/note.txt", "destination": "note.txt", "availability": "on_request"})
        driver.write(self.case / "case.json", manifest)
        actor = driver.read(self.case / "actor.json")
        actor["sources"].append({"source_id": "s-note", "file": "note.txt", "availability": "when requested"})
        driver.write(self.case / "actor.json", actor)
        self.manifest()
        self.begin()
        self.assertFalse((self.work / "note.txt").exists())
        driver.step(self.attempt, self.reply(initial=True))
        with self.assertRaisesRegex(ValueError, "unauthorized"):
            driver.step(self.attempt, self.reply(attachments=["s-secret"]))
        driver.step(self.attempt, self.reply(message="Here is the note.txt you asked for.", attachments=["s-note"]))
        self.assertEqual((self.work / "note.txt").read_text(), "A public note.")
        self.assertEqual(driver.read(self.attempt / "events/002/releases.json")["s-note"]["sha256"], driver.digest(self.work / "note.txt"))
        self.assertNotIn("s-note", (self.work / "fake-message.txt").read_text())

    def test_uncertain_or_failed_delivery_cannot_be_silently_resent(self):
        self.config["claude_command"][-1] = "changed"
        self.begin()
        result = driver.step(self.attempt, self.reply(initial=True))
        self.assertEqual(result["status"], "execution_error")
        with self.assertRaisesRegex(ValueError, "cannot send"):
            driver.step(self.attempt, self.reply())
        self.assertEqual(driver.read(self.attempt / "state.json")["turns"], 1)
        review = self.assessment()
        self.assertEqual(driver.finish(self.attempt, review)["outcome"], "execution_error")

    def test_pending_crash_and_operator_lock_refuse_new_dispatch(self):
        self.begin()
        state = driver.read(self.attempt / "state.json")
        state["status"] = "pending"
        driver.write(self.attempt / "state.json", state)
        with self.assertRaisesRegex(ValueError, "pending"):
            driver.step(self.attempt, self.reply(initial=True))
        (self.attempt / "operator.lock").write_text("interrupted")
        with self.assertRaisesRegex(ValueError, "lock"):
            driver.step(self.attempt, self.reply(initial=True))

    def test_whole_consultation_turn_cap_includes_attempts(self):
        self.config["limits"]["consultant_turns"] = 1
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        self.assertEqual(driver.step(self.attempt, self.reply())["status"], "limit_reached")
        result = driver.finish(self.attempt, self.assessment())
        self.assertEqual(result["outcome"], "incomplete")
        self.assertEqual(result["quality_rating"], "inconclusive")

    def test_changed_public_input_blocks_further_dispatch(self):
        self.begin()
        (self.work / "data.csv").write_text("changed")
        with self.assertRaisesRegex(ValueError, "public input changed"):
            driver.step(self.attempt, self.reply(initial=True))

    def test_private_path_unknown_fact_and_changed_initial_message_rejected(self):
        self.begin()
        with self.assertRaisesRegex(ValueError, "exact frozen"):
            driver.step(self.attempt, self.reply())
        driver.step(self.attempt, self.reply(initial=True))
        with self.assertRaisesRegex(ValueError, "private path"):
            driver.step(self.attempt, self.reply(message=str(self.attempt / "actor.json")))
        with self.assertRaisesRegex(ValueError, "unknown fact_ids"):
            driver.step(self.attempt, self.reply(fact_ids=["invented-fact"]))

    def test_review_evidence_changes_are_detected(self):
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        review = self.assessment()
        (self.work / "late-output.txt").write_text("late mutation")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            driver.finish(self.attempt, review)

    def test_diagnostic_cannot_pass_and_finalized_attempt_cannot_continue(self):
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        result = driver.finish(self.attempt, self.assessment())
        self.assertEqual(result["test_validity"], "invalid")
        self.assertEqual(result["quality_rating"], "inconclusive")
        self.assertIsNone(result["resources"]["aggregate_tokens"])
        with self.assertRaisesRegex(ValueError, "cannot send"):
            driver.step(self.attempt, self.reply())

    def test_material_consultant_finding_survives_invalid_test(self):
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        review = self.assessment()
        review["findings"] = [{"owner": "consultant", "severity": "material", "criterion": "c-target",
                               "description": "Test-only defect", "consequence": "Unsupported policy claim",
                               "evidence_refs": ["private/events/001/public.json"]}]
        self.assertEqual(driver.finish(self.attempt, review)["quality_rating"], "fail")

    def test_required_coverage_cannot_be_waived(self):
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        review = self.assessment()
        review["coverage"]["c-compute"]["status"] = "not_applicable"
        with self.assertRaisesRegex(ValueError, "cannot be waived"):
            driver.finish(self.attempt, review)

    def test_configuration_rejects_implicit_bypass_and_invalid_limits(self):
        for update in ({"claude_command": ["claude", "--dangerously-skip-permissions"]},
                       {"max_agent_turns_per_call": 0}, {"mode": "verified_host"}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                driver.validate_config({**self.config, **update})

    def test_last_turn_observation_overrun_is_a_terminal_limit(self):
        self.config["limits"]["elapsed_seconds"] = 0.3
        self.begin()
        with patch.object(driver, "observe_project", side_effect=lambda *args: time.sleep(0.4)):
            result = driver.step(self.attempt, self.reply(initial=True))
        self.assertEqual(result["status"], "limit_reached")
        state = driver.read(self.attempt / "state.json")
        self.assertIn("whole_run_time_limit", state["breaches"])
        self.assertIn("ended_at", state)
        review = self.assessment()
        self.assertEqual(driver.finish(self.attempt, review)["quality_rating"], "inconclusive")

    def test_failed_consultation_clock_excludes_review_delay(self):
        self.config["claude_command"][-1] = "provider_error"
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        state = driver.read(self.attempt / "state.json")
        expected = state["ended_at"] - state["started_at"]
        time.sleep(0.05)
        result = driver.finish(self.attempt, self.assessment())
        self.assertEqual(result["resources"]["elapsed_seconds"], expected)

    def test_rating_rules_with_reviewed_host_and_missing_evidence(self):
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        base = self.assessment()
        state = driver.read(self.attempt / "state.json")
        frozen = driver.read(self.attempt / "freeze.json")
        frozen["configuration"]["mode"] = "verified_host"
        frozen["reviewer_packet"] = driver.read(self.case / "reviewer.json")
        index = driver.read(self.attempt / "review-index.json")
        index["files"]["private/host/smoke.txt"] = "test-only"
        base["host_checks"] = {key: {"verified": True, "reason": "Test-only reviewed probe", "evidence_refs": ["private/host/smoke.txt"]}
                               for key in ("candidate_loading", "exact_resume", "private_isolation", "role_separation")}
        self.assertEqual(driver.assess(base, state, frozen, index)["quality_rating"], "pass")
        missing = copy.deepcopy(base)
        missing["coverage"]["c-cadence"]["status"] = "unobserved"
        self.assertEqual(driver.assess(missing, state, frozen, index)["quality_rating"], "inconclusive")
        minor = copy.deepcopy(base)
        minor["findings"] = [{"owner": "consultant", "severity": "minor", "criterion": "c-target",
                              "description": "Test defect", "consequence": "Test consequence", "evidence_refs": ["private/events/001/public.json"]}]
        self.assertEqual(driver.assess(minor, state, frozen, index)["quality_rating"], "weak")
        no_host = copy.deepcopy(base)
        del no_host["host_checks"]
        with self.assertRaisesRegex(ValueError, "host check"):
            driver.assess(no_host, state, frozen, index)
        wrong_stop = copy.deepcopy(base)
        wrong_stop["outcome"] = "useful_stop"
        with self.assertRaisesRegex(ValueError, "does not permit"):
            driver.assess(wrong_stop, state, frozen, index)


if __name__ == "__main__":
    unittest.main()
