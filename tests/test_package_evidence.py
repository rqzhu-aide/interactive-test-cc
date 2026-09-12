import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import package_evidence as package


class PackageEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.attempt, self.work = self.root / "attempt", self.root / "work"
        self.attempt.mkdir()
        self.work.mkdir()
        self.output = self.root / "review.zip"
        self.event = self.attempt / "events/001"
        self.write(self.work / "project/report.html", "<html>Retained report</html>")
        self.write(self.work / "unexpected-noise.txt", "Preserve this exact noisy output.\n")
        self.write(self.work / ".claude/skills/causal-consultant/package.json", {"version": "test"})
        self.write(self.attempt / "case/case.json", {"schema_version": 1})
        self.write(self.attempt / "case/oracle.json", {"private": True})
        for name in ("SKILL.md", "README.md", "scripts/session_driver.py", "scripts/claude_transport.py"):
            self.write(self.attempt / "testing" / name, "retained testing source\n")
        for command in ("claude-version", "claude-help"):
            self.capture(self.attempt / command, "probe bytes\n")
        self.capture(self.event / "transport", json.dumps({"type": "result", "result": "Exact public reply."}) + "\n")
        self.write(self.event / "transport/transport.json", {"message": "Exact public reply.", "error": None})
        self.write(self.event / "public.json", {"user": "Exact request.", "assistant": "Exact public reply."})
        self.write(self.event / "actor.json", {"message": "Exact request."})
        self.write(self.event / "releases.json", {})
        self.write(self.event / "project-binding.json", {"status": "bound"})
        self.write(self.event / "exchange-observation.json", {"status": "matched"})
        for command in ("status", "context", "history", "verify"):
            self.capture(self.event / ("project-" + command), json.dumps({"ok": True}))
        self.write(self.event / "work-files.json", self.inventory(self.work))
        shutil.copytree(self.work, self.event / "work-snapshot")
        self.write(self.attempt / "freeze.json", {
            "case_sha256": package._sha_file(self.attempt / "case/case.json"),
            "case_manifest": {"files": {"oracle.json": package._sha_file(self.attempt / "case/oracle.json")}},
            "candidate_files": self.inventory(self.work / ".claude/skills/causal-consultant"),
            "testing_files": self.inventory(self.attempt / "testing"),
        })
        self.state = {"work": str(self.work), "status": "awaiting_review", "turns": 1, "public_files": {}}
        self.write(self.attempt / "state.json", self.state)
        self.index()

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if not isinstance(value, str) else value, encoding="utf-8")

    @staticmethod
    def inventory(root):
        return {path.relative_to(root).as_posix(): package._sha_file(path) for path in sorted(root.rglob("*")) if path.is_file()}

    def capture(self, path, stdout):
        for name in package.CAPTURE_FILES:
            self.write(path / name, {"error": None, "exit_code": 0} if name.endswith(".json") else "")
        self.write(path / "stdout.txt", stdout)

    def index(self):
        files = {"private/" + name: sha for name, sha in self.inventory(self.attempt).items()
                 if name not in ("review-index.json", "state.json", "assessment.json", "review-observations.json")}
        files.update({"work/" + name: sha for name, sha in self.inventory(self.work).items()})
        files["state_at_review"] = package._identity(self.state)
        self.review_index = {"files": files, "sha256": package._identity(files)}
        self.write(self.attempt / "review-index.json", self.review_index)

    def rewrite_zip(self, change):
        with zipfile.ZipFile(self.output) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        change(entries)
        target = self.root / "altered.zip"
        with zipfile.ZipFile(target, "x") as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        return target

    def test_complete_round_trip_preserves_every_file_and_raw_bytes(self):
        before = self.inventory(self.attempt)
        result = package.export_package(self.attempt, self.output)
        self.assertEqual(result["completeness"], "complete")
        self.assertEqual(result, package.check_package(self.output))
        self.assertEqual(before, self.inventory(self.attempt))
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.read("work/unexpected-noise.txt"), (self.work / "unexpected-noise.txt").read_bytes())
            self.assertEqual(archive.read("private/events/001/transport/stdout.txt"), (self.event / "transport/stdout.txt").read_bytes())
            self.assertIn("private/events/001/project-verify/stdout.txt", archive.namelist())
            self.assertIn("private/events/001/work-snapshot/project/report.html", archive.namelist())

    def test_indexed_file_missing_refuses_before_output_and_partial_names_omission(self):
        (self.event / "work-snapshot/project/report.html").unlink()
        with self.assertRaisesRegex(ValueError, "complete package refused"):
            package.export_package(self.attempt, self.output)
        self.assertFalse(self.output.exists())
        result = package.export_package(self.attempt, self.output, allow_partial=True)
        self.assertEqual(result["completeness"], "partial")
        self.assertIn("private/events/001/work-snapshot/project/report.html", [item["path"] for item in result["omissions"]])
        with self.assertRaisesRegex(ValueError, "explicitly partial"):
            package.check_package(self.output)
        self.assertEqual(package.check_package(self.output, require_complete=False), result)
        with zipfile.ZipFile(self.output) as archive:
            self.assertTrue(archive.read(package.NOTICE).startswith(b"PARTIAL REVIEW PACKAGE"))

    def test_raw_and_public_capture_deletion_cannot_be_hidden_by_reindexing(self):
        for relative in ("transport/stdout.txt", "public.json"):
            with self.subTest(relative=relative):
                target = self.event / relative
                content = target.read_bytes()
                target.unlink()
                self.index()
                with self.assertRaisesRegex(ValueError, "complete package refused"):
                    package.export_package(self.attempt, self.output)
                target.write_bytes(content)
                self.index()
        self.assertFalse(self.output.exists())

    def test_raw_and_public_tampering_detected_by_index(self):
        for relative in ("transport/stdout.txt", "public.json"):
            with self.subTest(relative=relative):
                target = self.event / relative
                original = target.read_bytes()
                target.write_bytes(original + b" \n")
                with self.assertRaisesRegex(ValueError, "hash_mismatch"):
                    package.export_package(self.attempt, self.output)
                target.write_bytes(original)

    def test_raw_public_disagreement_detected_even_after_reindexing(self):
        self.write(self.event / "transport/stdout.txt", json.dumps({"type": "result", "result": "Different raw text"}))
        self.index()
        with self.assertRaisesRegex(ValueError, "raw_public_mismatch"):
            package.export_package(self.attempt, self.output)

    def test_missing_capture_is_partial_without_claiming_different_messages(self):
        for number, relative in enumerate(("transport/transport.json", "public.json", "transport/stdout.txt")):
            with self.subTest(relative=relative):
                target = self.event / relative
                original = target.read_bytes()
                target.unlink()
                self.index()
                output = self.root / f"missing-{number}.zip"
                result = package.export_package(self.attempt, output, allow_partial=True)
                self.assertEqual(result["completeness"], "partial")
                self.assertTrue(any(item["path"] == "private/events/001/" + relative
                                    and item["reason"] == "missing" for item in result["omissions"]))
                self.assertFalse(any(item["reason"] in ("public_transport_mismatch", "raw_public_mismatch")
                                     for item in result["omissions"]))
                self.assertEqual(package.check_package(output, require_complete=False), result)
                target.write_bytes(original)
                self.index()

    def test_invalid_capture_does_not_establish_a_message_mismatch(self):
        cases = (("transport/transport.json", "{", "invalid_json"),
                 ("transport/transport.json", {}, "invalid_transport_capture"),
                 ("transport/transport.json", {"message": ["Exact public reply."]}, "invalid_transport_capture"),
                 ("transport/transport.json", {"message": None}, "invalid_transport_capture"),
                 ("public.json", {}, "invalid_public_capture"),
                 ("public.json", {"assistant": 7}, "invalid_public_capture"),
                 ("public.json", {"assistant": None}, "invalid_public_capture"),
                 ("transport/stdout.txt", "unparseable response", "invalid_raw_capture"),
                 ("transport/stdout.txt", json.dumps({"type": "result"}), "invalid_raw_capture"),
                 ("transport/stdout.txt", "\n".join([json.dumps({"type": "result", "result": "Exact public reply."})] * 2),
                  "invalid_raw_capture"))
        for number, (relative, replacement, reason) in enumerate(cases):
            with self.subTest(relative=relative, replacement=replacement):
                target = self.event / relative
                original = target.read_bytes()
                self.write(target, replacement)
                self.index()
                result = package.export_package(self.attempt, self.root / f"invalid-{number}.zip", allow_partial=True)
                self.assertEqual(result["completeness"], "partial")
                self.assertTrue(any(item["reason"] == reason for item in result["omissions"]))
                self.assertFalse(any(item["reason"] in ("public_transport_mismatch", "raw_public_mismatch")
                                     for item in result["omissions"]))
                target.write_bytes(original)
                self.index()

    def test_public_transport_disagreement_detected_even_after_reindexing(self):
        self.write(self.event / "public.json", {"user": "Exact request.", "assistant": "Different public reply."})
        self.index()
        with self.assertRaisesRegex(ValueError, "public_transport_mismatch"):
            package.export_package(self.attempt, self.output)

    def test_failed_transport_preserves_corrupt_raw_output(self):
        self.write(self.event / "transport/stdout.txt", "unparseable provider noise\n")
        self.write(self.event / "transport/transport.json", {"message": None, "error": "invalid_response"})
        self.write(self.event / "public.json", {"user": "Exact request.", "assistant": None})
        self.index()
        result = package.export_package(self.attempt, self.output)
        self.assertEqual(result["completeness"], "complete")

    def test_finalized_state_and_bound_observations(self):
        observations = {"evidence_sha256": self.review_index["sha256"], "findings": []}
        self.write(self.attempt / "review-observations.json", observations)
        sha = package._sha_file(self.attempt / "review-observations.json")
        self.review_index["observations_sha256"] = sha
        self.write(self.attempt / "review-index.json", self.review_index)
        self.write(self.attempt / "assessment.json", {"evidence_sha256": self.review_index["sha256"], "observations_sha256": sha})
        self.write(self.attempt / "state.json", {**self.state, "status": "finished"})
        result = package.export_package(self.attempt, self.output)
        self.assertEqual(result["completeness"], "complete")
        (self.attempt / "review-observations.json").unlink()
        with self.assertRaisesRegex(ValueError, "review-observations.json"):
            package.export_package(self.attempt, self.root / "missing-observations.zip")

    def test_finished_without_assessment_is_partial(self):
        self.write(self.attempt / "state.json", {**self.state, "status": "finished"})
        with self.assertRaisesRegex(ValueError, "assessment.json"):
            package.export_package(self.attempt, self.output)

    def test_new_profile_requires_review_observations_even_if_index_field_is_removed(self):
        frozen = json.loads((self.attempt / "freeze.json").read_text())
        self.write(self.attempt / "freeze.json", {**frozen, "review_package_profile": "review-observations-v1"})
        self.index()
        with self.assertRaisesRegex(ValueError, "missing_observations_identity"):
            package.export_package(self.attempt, self.output)
        self.assertFalse(self.output.exists())

    def test_relocated_work_requires_explicit_override_and_keeps_original_state(self):
        self.state["work"] = str(self.root / "old-work")
        self.write(self.attempt / "state.json", self.state)
        self.index()
        with self.assertRaisesRegex(ValueError, "complete package refused"):
            package.export_package(self.attempt, self.output)
        package.export_package(self.attempt, self.output, work=self.work)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(json.loads(archive.read("private/state.json"))["work"], self.state["work"])
            self.assertTrue(json.loads(archive.read(package.MANIFEST))["work_override"])

    def test_output_overlap_existing_output_and_lock_refused(self):
        for target in (self.attempt / "export.zip", self.work / "export.zip"):
            with self.assertRaisesRegex(ValueError, "outside attempt and work"):
                package.export_package(self.attempt, target)
            self.assertFalse(target.exists())
        self.output.write_bytes(b"keep me")
        with self.assertRaisesRegex(ValueError, "already exists"):
            package.export_package(self.attempt, self.output)
        self.assertEqual(self.output.read_bytes(), b"keep me")
        self.write(self.attempt / "operator.lock", "pending")
        with self.assertRaisesRegex(ValueError, "operator lock"):
            package.export_package(self.attempt, self.root / "locked.zip")

    def test_index_traversal_rejected_even_for_partial(self):
        self.review_index["files"]["private/../../escape"] = "a" * 64
        self.review_index["sha256"] = package._identity(self.review_index["files"])
        self.write(self.attempt / "review-index.json", self.review_index)
        with self.assertRaisesRegex(ValueError, "unsafe package path"):
            package.export_package(self.attempt, self.output, allow_partial=True)
        self.assertFalse(self.output.exists())

    def test_source_link_rejected(self):
        link = self.attempt / "linked.txt"
        try:
            link.symlink_to(self.work / "unexpected-noise.txt")
        except OSError:
            self.skipTest("creating symlinks requires OS permission")
        with self.assertRaisesRegex(ValueError, "links are not package paths"):
            package.export_package(self.attempt, self.output, allow_partial=True)

    def test_archive_tampering_and_member_omission_fail(self):
        package.export_package(self.attempt, self.output)
        target = self.rewrite_zip(lambda entries: entries.update({"private/events/001/transport/stdout.txt": b"tampered"}))
        with self.assertRaisesRegex(ValueError, "file hash mismatch"):
            package.check_package(target)
        target.unlink()
        target = self.rewrite_zip(lambda entries: entries.pop("private/events/001/public.json"))
        with self.assertRaisesRegex(ValueError, "member inventory differs"):
            package.check_package(target)

    def test_partial_manifest_cannot_falsely_claim_complete(self):
        (self.event / "public.json").unlink()
        package.export_package(self.attempt, self.output, allow_partial=True)

        def claim_complete(entries):
            manifest = json.loads(entries[package.MANIFEST])
            manifest.update(completeness="complete", omissions=[])
            entries[package.MANIFEST] = json.dumps(manifest).encode()

        target = self.rewrite_zip(claim_complete)
        with self.assertRaisesRegex(ValueError, "completeness declaration differs"):
            package.check_package(target)

    def test_unsafe_archive_entries_rejected(self):
        for filename, mode in (("../escape.txt", stat.S_IFREG), ("link.txt", stat.S_IFLNK)):
            with self.subTest(filename=filename):
                target = self.root / "unsafe.zip"
                with zipfile.ZipFile(target, "w") as archive:
                    info = zipfile.ZipInfo(filename)
                    info.external_attr = mode << 16
                    archive.writestr(info, "target")
                with self.assertRaises(ValueError):
                    package.check_package(target)

    def test_concurrent_source_change_removes_only_new_failed_output(self):
        original = zipfile.ZipFile.write

        def mutate(archive, filename, arcname=None, *args, **kwargs):
            if arcname == "work/unexpected-noise.txt":
                Path(filename).write_bytes(b"changed while packaging")
            return original(archive, filename, arcname, *args, **kwargs)

        with patch.object(zipfile.ZipFile, "write", mutate):
            with self.assertRaisesRegex(ValueError, "file hash mismatch"):
                package.export_package(self.attempt, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
