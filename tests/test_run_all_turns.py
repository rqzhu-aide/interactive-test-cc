import importlib.util
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "run_all_turns.py"
SPEC = importlib.util.spec_from_file_location("run_all_turns", MODULE_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class RunnerTests(unittest.TestCase):
    def passing_record(self):
        return {
            "turn": 1,
            "label": "Activation",
            "prompt": "Prompt.",
            "response": "[> Framing]\nFrame.\n[! Boundary]\nBoundary.\n[? Next Steps]\nNext.",
            "response_received": True,
            "response_accepted": True,
            "session_id": "session-1",
            "duration_seconds": 1.5,
            "input_tokens": 10,
            "output_tokens": 5,
            "models": ["claude-opus"],
            "fast_mode_state": "off",
            "shell": {"ok": True, "errors": []},
            "state": {"ok": True, "errors": []},
            "scope": {"ok": True, "applicable": False, "errors": []},
            "artifacts": {
                "ok": True,
                "expected": {"total": 0, "new": 0},
                "new_count": 0,
                "counts": {},
                "errors": [],
            },
        }

    def summary_target(self):
        return {
            "test_suite_version": "5.2.2",
            "test_suite_runtime_sha256": "suite123",
            "test_case_sha256": "case123",
            "causal_consultant_version": "5.1.4",
            "statectl_sha256": "abc123",
            "skill_runtime_sha256": "def456",
            "input_data": None,
        }

    def write_assessable_summary(self, results_dir, summary):
        (results_dir / "conversation.md").write_text("# Conversation\n", encoding="utf-8")
        (results_dir / "test-reference.md").write_text("# Rubric\n", encoding="utf-8")
        summary["review_evidence"] = RUNNER.capture_review_evidence(results_dir)
        RUNNER.write_summary_files(results_dir, summary)

    def test_heading_shell_rejects_prose_preamble(self):
        preambles = [
            "Operation closed.\n\n",
            "[OK Confirmed] Work completed.\n\nOperation closed.\n\n",
        ]
        for preamble in preambles:
            with self.subTest(preamble=preamble):
                result = RUNNER.check_headings(
                    preamble
                    + "[> Framing]\nFraming.\n\n"
                    "[! Boundary]\nBoundary.\n\n"
                    "[? Next Steps]\nNext step."
                )
                self.assertIn("prose appears before the heading shell", result["errors"])

    def test_heading_shell_accepts_allowed_openings(self):
        shell = (
            "[> Framing]\nFraming.\n\n"
            "[! Boundary]\nBoundary.\n\n"
            "[? Next Steps]\nNext step."
        )
        openings = [
            "",
            "[OK Confirmed] Work completed.\n\n",
            "[Causal-Consultant Loaded] This is a new project. Causal analysis team ready.\n\n",
            (
                "[OK Confirmed] Previous state archived.\n\n"
                "[Causal-Consultant Loaded] This is a new project. Causal analysis team ready.\n\n"
            ),
            (
                "[Causal-Consultant Loaded] This is a new project. Causal analysis team ready.\n\n"
                "[OK Confirmed] Project initialized.\n\n"
            ),
        ]
        for opening in openings:
            with self.subTest(opening=opening):
                self.assertEqual(RUNNER.check_headings(opening + shell)["errors"], [])

    def test_heading_shell_accepts_structured_consultant_options(self):
        response = (
            "[> Framing]\nFraming.\n\n"
            "[+ Consultant Options]\n"
            "    1. Audit the data.\n"
            "       Consultant read: Establish data readiness.\n"
            "       Tradeoff: Defers causal review.\n"
            "    2. Review the causal design.\n"
            "       Consultant read: Establish claim boundaries.\n"
            "       Tradeoff: Defers data-specific checks.\n\n"
            "[! Boundary]\nBoundary.\n\n"
            "[? Next Steps]\nChoose option 1 or 2."
        )
        self.assertEqual(RUNNER.check_headings(response)["errors"], [])

    def state_payload(self, revision):
        return {
            "ok": True,
            "code": "VALID",
            "active_operation": None,
            "plan": [],
            "warnings": [],
            "project_id": "project-1",
            "revision": revision,
        }

    def validate_revision(
        self,
        previous_revision,
        revision,
        previous_manifest_count=0,
        manifest_count=0,
    ):
        with patch.object(
            RUNNER,
            "run_json",
            return_value=(0, self.state_payload(revision), ""),
        ):
            _, errors = RUNNER.validate_state(
                Path("statectl.cjs"),
                "node",
                Path("."),
                "project-1" if previous_revision is not None else None,
                previous_revision,
                previous_manifest_count,
                manifest_count,
            )
        return errors

    def test_revision_budget_rejects_delta_one(self):
        errors = self.validate_revision(25, 26)
        self.assertIn(
            "revision increased by 1; one completed operation requires at least 2 mutations",
            errors,
        )

    def test_revision_budget_rejects_delta_four_without_artifact(self):
        errors = self.validate_revision(25, 29)
        self.assertIn(
            "revision increased by 4 without a new artifact; expected at most 3",
            errors,
        )

    def test_revision_budget_allows_delta_three_without_artifact(self):
        self.assertEqual(self.validate_revision(25, 28), [])

    def test_revision_budget_allows_delta_four_with_one_artifact(self):
        self.assertEqual(self.validate_revision(25, 29, 2, 3), [])

    def test_revision_budget_rejects_incomplete_artifact_lifecycle(self):
        for revision in (27, 28):
            with self.subTest(revision=revision):
                errors = self.validate_revision(25, revision, 2, 3)
                self.assertIn(
                    f"revision increased by {revision - 25} with one new artifact; expected 4",
                    errors,
                )

    def test_revision_budget_rejects_multiple_new_artifacts(self):
        errors = self.validate_revision(25, 29, 2, 4)
        self.assertIn(
            "artifact manifest count changed by 2; expected 0 or 1",
            errors,
        )

    def test_scope_oracle_suites_require_scope_snapshot_capability(self):
        for test_id in ("standard", "mechanical-edge", "causal-edge"):
            with self.subTest(test_id=test_id):
                with self.assertRaisesRegex(RUNNER.RunError, "scope_snapshot 1"):
                    RUNNER.require_controller_capabilities(test_id, {"capabilities": {}})
                RUNNER.require_controller_capabilities(
                    test_id,
                    {"capabilities": {"scope_snapshot": 1}},
                )
        RUNNER.require_controller_capabilities("smoke", {"capabilities": {}})

    def test_registry_rejects_unknown_artifact_expectation(self):
        registry = json.loads(RUNNER.CASES_PATH.read_text(encoding="utf-8"))
        registry["tests"]["smoke"]["turns"][0]["artifacts"] = {"analysis_exection": 0}
        with TemporaryDirectory() as temporary:
            registry_path = Path(temporary) / "test-cases.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            with patch.object(RUNNER, "CASES_PATH", registry_path):
                with self.assertRaisesRegex(RUNNER.RunError, "unknown artifact expectation"):
                    RUNNER.load_cases()

    def test_registry_rejects_nonobject_root(self):
        with TemporaryDirectory() as temporary:
            registry_path = Path(temporary) / "test-cases.json"
            registry_path.write_text("[]\n", encoding="utf-8")
            with patch.object(RUNNER, "CASES_PATH", registry_path):
                with self.assertRaisesRegex(RUNNER.RunError, "schema_version 1"):
                    RUNNER.load_cases()

    def test_mechanical_edge_registry_tracks_all_artifacts(self):
        turns = RUNNER.load_cases()["mechanical-edge"]["turns"]
        self.assertEqual(
            [turn["artifacts"].get("total") for turn in turns],
            [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2],
        )
        self.assertIn("Do not run causal review", turns[1]["prompt"])
        self.assertIn("create any durable artifact", turns[1]["prompt"])

    def test_mechanical_edge_registry_primes_replacement_gate(self):
        turns = RUNNER.load_cases()["mechanical-edge"]["turns"]
        review_prompt = turns[4]["prompt"]
        replacement_prompt = turns[5]["prompt"]

        for requirement in (
            "mature for later scope review",
            "`single_time_observational`",
            "`heterogeneous-effects`",
            "without changing the current average-effect scope",
            "Bound the claim to exploratory variation across Private strata",
            "do not attribute that variation to Private status itself",
        ):
            self.assertIn(requirement, review_prompt)

        for requirement in (
            "Using only the current design and support recommendations",
            "bounded claim established in the prior turn",
            "replace the current average-effect scope",
            "Do not rerun causal review",
        ):
            self.assertIn(requirement, replacement_prompt)

    def test_mechanical_edge_reference_documents_gate_handoff(self):
        reference = (ROOT / "references" / "mechanical-edge.md").read_text(encoding="utf-8")
        for requirement in (
            "`single_time_observational` + `heterogeneous-effects`",
            "does not attribute variation to Private itself",
            "original scope remains current",
            "without another causal review",
            "turn 6 consumed them without rerunning causal review",
        ):
            self.assertIn(requirement, reference)

    def test_standard_registry_allows_only_optional_data_audit_artifacts_on_turns_3_and_4(self):
        turns = RUNNER.load_cases()["standard"]["turns"]
        for turn in turns[2:4]:
            with self.subTest(label=turn["label"]):
                expected = turn["artifacts"]
                self.assertNotIn("new", expected)
                self.assertEqual(expected["causal_discovery"], 0)
                self.assertEqual(expected["analysis_execution"], 0)
                self.assertEqual(expected["report_writer"], 0)

    def test_registered_data_uses_canonical_fingerprint(self):
        cases = RUNNER.load_cases()
        fingerprints = {
            case["data"]["canonical_sha256"]
            for case in cases.values()
            if case["data"] is not None
        }
        self.assertEqual(
            fingerprints,
            {"5a373ac7af1bc13caae0e08bc3e7230fac28eb5be265132372f5bc5ffe65806c"},
        )

    def test_standard_scope_oracle_accepts_causal_review_then_new_scope(self):
        sequence = self.standard_scope_sequence()
        history = {7: sequence[7]}
        self.assertEqual(RUNNER.check_standard_scopes(8, sequence[8], history), [])
        self.assertEqual(RUNNER.check_standard_scopes(9, sequence[9], history), [])

    def standard_scope_sequence(self):
        empty = {"analysis": {}, "report": None}
        first_ready = self.analysis_snapshot(
            "analysis-1", 1, "ready", "2026-01-01T00:00:06Z"
        )
        first_ready["analysis"]["single_time_observational"]["support"] = None
        first_done = deepcopy(first_ready)
        first_done["analysis"]["single_time_observational"].update(
            {"current_status": "done", "last_updated": "2026-01-01T00:00:07Z"}
        )
        second_ready = deepcopy(first_done)
        second_ready["analysis"]["descriptive_association"] = {
            "scope_id": "analysis-2",
            "scope_revision": 1,
            "current_status": "ready",
            "support": "heterogeneous-effects",
            "last_updated": "2026-01-01T00:00:09Z",
        }
        second_done = deepcopy(second_ready)
        second_done["analysis"]["descriptive_association"].update(
            {"current_status": "done", "last_updated": "2026-01-01T00:00:10Z"}
        )
        report_ready = self.report_snapshot(
            second_done, "report-1", 1, "ready", "2026-01-01T00:00:11Z"
        )
        report_done = self.report_snapshot(
            second_done, "report-1", 1, "done", "2026-01-01T00:00:12Z"
        )
        derivative_ready = self.report_snapshot(
            second_done, "report-2", 1, "ready", "2026-01-01T00:00:13Z"
        )
        return {
            **{turn: deepcopy(empty) for turn in range(1, 6)},
            6: first_ready,
            7: first_done,
            8: deepcopy(first_done),
            9: second_ready,
            10: second_done,
            11: report_ready,
            12: report_done,
            13: derivative_ready,
        }

    def test_standard_scope_oracle_accepts_full_lifecycle(self):
        history = {}
        for turn, snapshot in self.standard_scope_sequence().items():
            self.assertEqual(
                RUNNER.check_standard_scopes(turn, snapshot, history),
                [],
                f"turn {turn}",
            )

    def test_standard_scope_oracle_rejects_dropped_completed_scope(self):
        history = {}
        sequence = self.standard_scope_sequence()
        for turn in range(1, 9):
            self.assertEqual(RUNNER.check_standard_scopes(turn, sequence[turn], history), [])
        dropped = deepcopy(sequence[9])
        del dropped["analysis"]["single_time_observational"]
        errors = RUNNER.check_standard_scopes(9, dropped, history)
        self.assertIn("turn 9 must preserve completed analysis scopes", errors)

    def test_standard_scope_oracle_rejects_wrong_first_route(self):
        ready = deepcopy(self.standard_scope_sequence()[6])
        entry = ready["analysis"].pop("single_time_observational")
        ready["analysis"]["panel_longitudinal"] = entry
        errors = RUNNER.check_standard_scopes(6, ready, {})
        self.assertIn(
            "turn 6 ready scope must use the single_time_observational route",
            errors,
        )

    def test_standard_scope_oracle_rejects_turn_8_scope_change(self):
        completed = self.analysis_snapshot("analysis-1", 1, "done", "2026-01-01T00:00:07Z")
        history = {7: completed}
        changed = self.analysis_snapshot("analysis-2", 1, "ready", "2026-01-01T00:00:08Z")
        errors = RUNNER.check_standard_scopes(8, changed, history)
        self.assertIn("turn 8 must leave the completed analysis scope unchanged", errors)

    def test_standard_scope_oracle_rejects_reused_scope_identity(self):
        sequence = self.standard_scope_sequence()
        history = {7: sequence[7]}
        reused = deepcopy(sequence[9])
        reused["analysis"]["descriptive_association"].update(
            {"scope_id": "analysis-1", "scope_revision": 2}
        )
        self.assertEqual(RUNNER.check_standard_scopes(8, sequence[8], history), [])
        errors = RUNNER.check_standard_scopes(9, reused, history)
        self.assertIn("turn 9 must create a new analysis scope identity", errors)

    def test_standard_scope_oracle_rejects_wrong_support(self):
        sequence = self.standard_scope_sequence()
        history = {7: sequence[7]}
        ready = deepcopy(sequence[9])
        ready["analysis"]["descriptive_association"]["support"] = None
        self.assertEqual(RUNNER.check_standard_scopes(8, sequence[8], history), [])
        errors = RUNNER.check_standard_scopes(9, ready, history)
        self.assertIn("turn 9 ready scope must use heterogeneous-effects support", errors)

    def test_standard_scope_oracle_rejects_wrong_second_route(self):
        sequence = self.standard_scope_sequence()
        history = {7: sequence[7]}
        ready = deepcopy(sequence[9])
        entry = ready["analysis"].pop("descriptive_association")
        ready["analysis"]["panel_longitudinal"] = entry
        self.assertEqual(RUNNER.check_standard_scopes(8, sequence[8], history), [])
        errors = RUNNER.check_standard_scopes(9, ready, history)
        self.assertIn(
            "turn 9 ready scope must use the descriptive_association route",
            errors,
        )

    def test_standard_scope_oracle_rejects_multiple_new_ready_scopes(self):
        sequence = self.standard_scope_sequence()
        history = {7: sequence[7]}
        ready = deepcopy(sequence[9])
        ready["analysis"]["panel_longitudinal"] = {
            **ready["analysis"]["descriptive_association"],
            "scope_id": "analysis-3",
        }
        self.assertEqual(RUNNER.check_standard_scopes(8, sequence[8], history), [])
        errors = RUNNER.check_standard_scopes(9, ready, history)
        self.assertIn("turn 9 must contain exactly one ready analysis scope", errors)

    def analysis_snapshot(self, scope_id, revision, status, last_updated):
        return {
            "analysis": {
                "single_time_observational": {
                    "scope_id": scope_id,
                    "scope_revision": revision,
                    "current_status": status,
                    "support": "heterogeneous-effects",
                    "last_updated": last_updated,
                }
            },
            "report": None,
        }

    def report_snapshot(self, analysis, scope_id, revision, status, last_updated):
        return {
            "analysis": analysis["analysis"],
            "report": {
                "scope_id": scope_id,
                "scope_revision": revision,
                "current_status": status,
                "last_updated": last_updated,
            },
        }

    def valid_scope_sequence(self):
        empty = {"analysis": {}, "report": None}
        original = self.analysis_snapshot("analysis-1", 1, "ready", "2026-01-01T00:00:04Z")
        replacement = self.analysis_snapshot("analysis-2", 1, "ready", "2026-01-01T00:00:06Z")
        completed = self.analysis_snapshot("analysis-2", 1, "done", "2026-01-01T00:00:08Z")
        report_original = self.report_snapshot(completed, "report-1", 1, "ready", "2026-01-01T00:00:10Z")
        report_replacement = self.report_snapshot(completed, "report-1", 2, "ready", "2026-01-01T00:00:11Z")
        report_completed = self.report_snapshot(completed, "report-1", 2, "done", "2026-01-01T00:00:13Z")
        return {
            1: empty,
            2: empty,
            3: empty,
            4: original,
            5: original,
            6: replacement,
            7: replacement,
            8: completed,
            9: completed,
            10: report_original,
            11: report_replacement,
            12: report_replacement,
            13: report_completed,
        }

    def test_mechanical_edge_scope_oracle_accepts_fixed_sequence(self):
        history = {}
        for turn, snapshot in self.valid_scope_sequence().items():
            self.assertEqual(
                RUNNER.check_mechanical_edge_scopes(turn, snapshot, history),
                [],
            )

    def test_mechanical_edge_scope_oracle_rejects_unchanged_replacement(self):
        history = {}
        sequence = self.valid_scope_sequence()
        for turn in range(1, 6):
            self.assertEqual(
                RUNNER.check_mechanical_edge_scopes(turn, sequence[turn], history),
                [],
            )
        errors = RUNNER.check_mechanical_edge_scopes(6, sequence[4], history)
        self.assertIn("turn 6 must replace or revise the original analysis scope", errors)

    def test_mechanical_edge_scope_oracle_rejects_wrong_replacement_route(self):
        history = {}
        sequence = self.valid_scope_sequence()
        for turn in range(1, 6):
            self.assertEqual(
                RUNNER.check_mechanical_edge_scopes(turn, sequence[turn], history),
                [],
            )
        replacement = deepcopy(sequence[6])
        entry = replacement["analysis"].pop("single_time_observational")
        replacement["analysis"]["descriptive_association"] = entry
        errors = RUNNER.check_mechanical_edge_scopes(6, replacement, history)
        self.assertIn(
            "turn 6 replacement must use the single_time_observational route",
            errors,
        )

    def test_mechanical_edge_scope_oracle_rejects_wrong_replacement_support(self):
        history = {}
        sequence = self.valid_scope_sequence()
        for turn in range(1, 6):
            self.assertEqual(
                RUNNER.check_mechanical_edge_scopes(turn, sequence[turn], history),
                [],
            )
        replacement = deepcopy(sequence[6])
        replacement["analysis"]["single_time_observational"]["support"] = None
        errors = RUNNER.check_mechanical_edge_scopes(6, replacement, history)
        self.assertIn(
            "turn 6 replacement must use heterogeneous-effects support",
            errors,
        )

    def test_mechanical_edge_scope_oracle_rejects_shape_drift(self):
        snapshot = self.analysis_snapshot("analysis-1", 1, "ready", "2026-01-01T00:00:04Z")
        del snapshot["analysis"]["single_time_observational"]["support"]
        errors = RUNNER.check_mechanical_edge_scopes(4, snapshot, {})
        self.assertTrue(any("invalid shape" in error for error in errors))

    def test_mechanical_edge_scope_oracle_ignores_additive_diagnostics(self):
        snapshot = self.analysis_snapshot("analysis-1", 1, "ready", "2026-01-01T00:00:04Z")
        snapshot["future_field"] = {"version": 1}
        snapshot["analysis"]["single_time_observational"]["future_field"] = True
        self.assertEqual(RUNNER.check_mechanical_edge_scopes(4, snapshot, {}), [])

    def test_mechanical_edge_scope_oracle_rejects_preserved_scope_activity(self):
        history = {}
        sequence = self.valid_scope_sequence()
        for turn in range(1, 5):
            self.assertEqual(RUNNER.check_mechanical_edge_scopes(turn, sequence[turn], history), [])
        changed = self.analysis_snapshot("analysis-1", 1, "ready", "2026-01-01T00:00:05Z")
        errors = RUNNER.check_mechanical_edge_scopes(5, changed, history)
        self.assertIn("turn 5 must leave the original analysis scope unchanged", errors)

    def test_mechanical_edge_scope_oracle_rejects_wrong_completed_scope(self):
        history = {}
        sequence = self.valid_scope_sequence()
        for turn in range(1, 8):
            self.assertEqual(
                RUNNER.check_mechanical_edge_scopes(turn, sequence[turn], history),
                [],
            )
        wrong = self.analysis_snapshot("analysis-3", 1, "done", "2026-01-01T00:00:08Z")
        errors = RUNNER.check_mechanical_edge_scopes(8, wrong, history)
        self.assertIn("turn 8 must complete the exact replacement analysis scope", errors)

    def test_mechanical_edge_scope_oracle_rejects_stale_report_mutation(self):
        history = {}
        sequence = self.valid_scope_sequence()
        for turn in range(1, 12):
            self.assertEqual(
                RUNNER.check_mechanical_edge_scopes(turn, sequence[turn], history),
                [],
            )
        wrong = self.report_snapshot(sequence[8], "report-2", 1, "ready", "2026-01-01T00:00:12Z")
        errors = RUNNER.check_mechanical_edge_scopes(12, wrong, history)
        self.assertIn(
            "turn 12 stale approval must leave the replacement report scope unchanged",
            errors,
        )

    def test_html_links_accept_valid_local_targets(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            report = workdir / "output" / "report" / "index.html"
            evidence = workdir / "output" / "evidence"
            report.parent.mkdir(parents=True)
            evidence.mkdir(parents=True)
            (evidence / "figure.png").write_bytes(b"figure")
            (report.parent / "appendix.html").write_text(
                '<div id="detail"></div>', encoding="utf-8"
            )
            report.write_text(
                '<div id="section"></div><a href="#section">section</a>'
                '<a href="appendix.html#detail">detail</a>'
                '<a href="../evidence/">evidence</a>'
                '<img src="../evidence/figure.png">'
                '<a href="https://example.com">external</a>',
                encoding="utf-8",
            )
            self.assertEqual(RUNNER.inspect_html_links(report, workdir), [])

    def test_html_links_reject_broken_targets(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            report = workdir / "output" / "report" / "index.html"
            report.parent.mkdir(parents=True)
            (report.parent / "appendix.html").write_text(
                '<div id="detail"></div>', encoding="utf-8"
            )
            report.write_text(
                '<div id="duplicate"></div><div id="duplicate"></div>'
                '<a href="#missing">fragment</a>'
                '<a href="appendix.html#missing">cross-file fragment</a>'
                '<a href="missing.txt">missing file</a>'
                '<a href="../../../outside.txt">outside</a>'
                '<img src="missing.png">'
                '<img src="%00">'
                '<a href="http://[broken">malformed</a>',
                encoding="utf-8",
            )
            errors = RUNNER.inspect_html_links(report, workdir)
            self.assertTrue(any("duplicate HTML id" in error for error in errors))
            self.assertTrue(any("missing HTML fragment target" in error for error in errors))
            self.assertIn(
                "missing HTML fragment target (appendix.html#missing)", errors
            )
            self.assertTrue(any("missing project-local HTML link target" in error for error in errors))
            self.assertTrue(any("outside the project" in error for error in errors))
            self.assertTrue(any("malformed HTML link" in error for error in errors))
            self.assertTrue(any("missing project-local HTML source target" in error for error in errors))
            self.assertTrue(any("malformed HTML source reference (%00)" in error for error in errors))

    def test_html_links_reject_nonportable_local_references(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            report = workdir / "output" / "report" / "index.html"
            report.parent.mkdir(parents=True)
            report.write_text(
                '<img src="file:///tmp/figure.png">'
                '<a href="C:/private/evidence.txt">evidence</a>',
                encoding="utf-8",
            )
            errors = RUNNER.inspect_html_links(report, workdir)
            self.assertEqual(
                sum("nonportable local HTML" in error for error in errors),
                2,
            )

    def write_artifact_state(self, workdir, manifest, location):
        record = {
            "artifact_id": "11111111-1111-4111-8111-111111111111",
            "operation_id": manifest["operation_id"],
            "route": manifest["route"],
            "location": location,
            "created_at": "2026-01-01T00:00:01Z",
            "summary": manifest["summary"],
        }
        lines = ["artifact_records:"]
        for index, (key, value) in enumerate(record.items()):
            prefix = "  - " if index == 0 else "    "
            lines.append(f"{prefix}{key}: {json.dumps(value)}")
        (workdir / "project_state.yaml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def write_data_audit_artifact(self, workdir, route="data_audit"):
        artifact = workdir / "output" / "audit"
        artifact.mkdir(parents=True)
        deliverable = artifact / "audit.txt"
        deliverable.write_text("first audit\n", encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "operation_id": "22222222-2222-4222-8222-222222222222",
            "route": route,
            "scope_ref": None,
            "files": ["output/audit/audit.txt"],
            "completed_at": "2026-01-01T00:00:00Z",
            "summary": "Audit output.",
        }
        (artifact / "artifact-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        self.write_artifact_state(workdir, manifest, "output/audit")
        return deliverable

    def write_report_artifact(self, workdir, html_content=""):
        artifact = workdir / "output" / "report"
        artifact.mkdir(parents=True)
        (artifact / "index.html").write_text(html_content, encoding="utf-8")
        (artifact / "notes.txt").write_text("report notes\n", encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "operation_id": "33333333-3333-4333-8333-333333333333",
            "route": "report_writer",
            "scope_ref": {
                "kind": "report",
                "id": "44444444-4444-4444-8444-444444444444",
                "revision": 1,
            },
            "files": ["output/report/index.html", "output/report/notes.txt"],
            "completed_at": "2026-01-01T00:00:00Z",
            "summary": "Report output.",
        }
        (artifact / "artifact-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        self.write_artifact_state(workdir, manifest, "output/report")

    def test_artifact_snapshot_rejects_changed_prior_file(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            deliverable = self.write_data_audit_artifact(workdir)
            first = RUNNER.inspect_artifacts(
                workdir, {"total": 1, "new": 1}
            )
            self.assertTrue(first["ok"], first["errors"])
            deliverable.write_text("changed audit\n", encoding="utf-8")
            second = RUNNER.inspect_artifacts(
                workdir, {"total": 1, "new": 0}, first
            )
            self.assertFalse(second["ok"])
            self.assertIn(
                "previous artifact file changed: output/audit/audit.txt",
                second["errors"],
            )

    def test_artifact_snapshot_rejects_deleted_prior_manifest(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_data_audit_artifact(workdir)
            first = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
            (workdir / "output" / "audit" / "artifact-manifest.json").unlink()
            second = RUNNER.inspect_artifacts(workdir, {"total": 0, "new": 0}, first)
            self.assertFalse(second["ok"])
            self.assertTrue(
                any("previous artifact manifests disappeared" in error for error in second["errors"])
            )

    def test_artifact_scan_rejects_symlinked_output_directory(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary) / "project"
            workdir.mkdir()
            output = workdir / "output"
            with patch.object(Path, "is_symlink", autospec=True, side_effect=lambda path: path == output):
                result = RUNNER.inspect_artifacts(workdir, {"total": 0, "new": 0})
            self.assertFalse(result["ok"])
            self.assertIn("output directory must not be a symlink", result["errors"])

    def test_artifact_growth_is_exact_when_registered(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_data_audit_artifact(workdir)
            optional = RUNNER.inspect_artifacts(
                workdir, {"analysis_execution": 0, "report_writer": 0}
            )
            self.assertTrue(optional["ok"], optional["errors"])
            forbidden = RUNNER.inspect_artifacts(
                workdir,
                {"analysis_execution": 0, "report_writer": 0, "new": 0},
            )
            self.assertFalse(forbidden["ok"])
            self.assertIn("expected 0 new artifact(s), found 1", forbidden["errors"])

    def test_standard_optional_artifact_rejects_causal_discovery(self):
        expected = RUNNER.load_cases()["standard"]["turns"][2]["artifacts"]
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_data_audit_artifact(workdir)
            audit = RUNNER.inspect_artifacts(workdir, expected)
            self.assertTrue(audit["ok"], audit["errors"])
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_data_audit_artifact(workdir, route="causal_discovery")
            discovery = RUNNER.inspect_artifacts(workdir, expected)
            self.assertFalse(discovery["ok"])
            self.assertIn(
                "expected 0 causal_discovery artifact(s), found 1",
                discovery["errors"],
            )

    def test_artifact_manifest_schema_is_strict(self):
        cases = (
            ("schema", lambda manifest: manifest.update(schema_version=2), "schema_version"),
            ("operation", lambda manifest: manifest.update(operation_id="op-1"), "not a UUID"),
            ("timestamp", lambda manifest: manifest.update(completed_at="12:00:00"), "RFC3339 UTC"),
            ("scope", lambda manifest: manifest.update(scope_ref={"kind": "analysis"}), "must be null"),
            ("summary", lambda manifest: manifest.update(summary=""), "summary must be nonempty"),
            ("missing", lambda manifest: manifest.pop("summary"), "manifest is missing: summary"),
            ("unknown", lambda manifest: manifest.update(extra=True), "unknown fields"),
        )
        for label, mutate, message in cases:
            with self.subTest(label=label), TemporaryDirectory() as temporary:
                workdir = Path(temporary)
                self.write_data_audit_artifact(workdir)
                manifest_path = workdir / "output" / "audit" / "artifact-manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest)
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                result = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
                self.assertFalse(result["ok"])
                self.assertTrue(any(message in error for error in result["errors"]))

    def test_artifact_registration_is_structural(self):
        cases = (
            (
                "operation",
                "22222222-2222-4222-8222-222222222222",
                "55555555-5555-4555-8555-555555555555",
                "operation_id is not exactly registered",
            ),
            ("location", "output/audit", "output/audit-decoy", "location does not match"),
        )
        for label, original, replacement, message in cases:
            with self.subTest(label=label), TemporaryDirectory() as temporary:
                workdir = Path(temporary)
                self.write_data_audit_artifact(workdir)
                state_path = workdir / "project_state.yaml"
                state_path.write_text(
                    state_path.read_text(encoding="utf-8").replace(original, replacement),
                    encoding="utf-8",
                )
                result = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
                self.assertFalse(result["ok"])
                self.assertTrue(any(message in error for error in result["errors"]))

    def test_artifact_manifest_rejects_file_outside_reserved_location(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_data_audit_artifact(workdir)
            escaped = workdir / "output" / "escaped.txt"
            escaped.write_text("escaped\n", encoding="utf-8")
            manifest_path = workdir / "output" / "audit" / "artifact-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"] = ["output/escaped.txt"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
            self.assertFalse(result["ok"])
            self.assertTrue(
                any("outside the reserved location" in error for error in result["errors"])
            )

    def test_artifact_manifest_requires_nonempty_deliverable(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            deliverable = self.write_data_audit_artifact(workdir)
            deliverable.write_bytes(b"")
            result = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
            self.assertFalse(result["ok"])
            self.assertTrue(any("no nonempty deliverable" in error for error in result["errors"]))

    def test_file_artifact_manifest_accepts_reserved_primary_file(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            output = workdir / "output"
            output.mkdir()
            deliverable = output / "audit.txt"
            deliverable.write_text("audit\n", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "operation_id": "66666666-6666-4666-8666-666666666666",
                "route": "data_audit",
                "scope_ref": None,
                "files": ["output/audit.txt"],
                "completed_at": "2026-01-01T00:00:00Z",
                "summary": "File audit output.",
            }
            (output / "audit.txt.manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            self.write_artifact_state(workdir, manifest, "output/audit.txt")
            result = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
            self.assertTrue(result["ok"], result["errors"])

    def test_artifact_manifest_cannot_list_itself_as_deliverable(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_data_audit_artifact(workdir)
            manifest_path = workdir / "output" / "audit" / "artifact-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"] = ["output/audit/artifact-manifest.json"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
            self.assertFalse(result["ok"])
            self.assertTrue(any("must not list itself" in error for error in result["errors"]))

    def test_report_manifest_requires_nonempty_html(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_report_artifact(workdir, html_content="")
            result = RUNNER.inspect_artifacts(
                workdir, {"report_writer": 1, "new": 1}
            )
            self.assertFalse(result["ok"])
            self.assertTrue(any("report HTML file is empty" in error for error in result["errors"]))

    def test_artifact_scan_reports_invalid_listed_path(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_data_audit_artifact(workdir)
            manifest_path = workdir / "output" / "audit" / "artifact-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"] = ["output/audit/\x00invalid.txt"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
            self.assertFalse(result["ok"])
            self.assertTrue(
                any("listed file path is invalid" in error for error in result["errors"])
            )

    def test_new_manifest_binds_prior_ready_scope(self):
        previous = self.analysis_snapshot(
            "analysis-1", 1, "ready", "2026-01-01T00:00:01Z"
        )
        current = self.analysis_snapshot(
            "analysis-1", 1, "done", "2026-01-01T00:00:02Z"
        )
        artifacts = {
            "new_manifests": [
                {
                    "path": "output/result/artifact-manifest.json",
                    "route": "analysis_execution",
                    "scope_ref": {"kind": "analysis", "id": "analysis-1", "revision": 1},
                }
            ]
        }
        self.assertEqual(
            RUNNER.check_new_manifest_scope_bindings(current, previous, artifacts),
            [],
        )
        artifacts["new_manifests"][0]["scope_ref"]["revision"] = 2
        errors = RUNNER.check_new_manifest_scope_bindings(current, previous, artifacts)
        self.assertTrue(any("not exactly ready" in error for error in errors))
        self.assertTrue(any("not exactly done" in error for error in errors))

    def test_report_manifest_binds_prior_ready_scope(self):
        analysis = self.analysis_snapshot(
            "analysis-1", 1, "done", "2026-01-01T00:00:01Z"
        )
        previous = self.report_snapshot(
            analysis, "report-1", 1, "ready", "2026-01-01T00:00:02Z"
        )
        current = self.report_snapshot(
            analysis, "report-1", 1, "done", "2026-01-01T00:00:03Z"
        )
        artifacts = {
            "new_manifests": [
                {
                    "path": "output/report/artifact-manifest.json",
                    "route": "report_writer",
                    "scope_ref": {"kind": "report", "id": "report-1", "revision": 1},
                }
            ]
        }
        self.assertEqual(
            RUNNER.check_new_manifest_scope_bindings(current, previous, artifacts),
            [],
        )

    def test_validate_data_uses_canonical_content(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "data.csv"
            rows = [["Private", "Expend"], ["Yes", "1000"]]
            path.write_text("Private,Expend\nYes,1000\n", encoding="utf-8")
            canonical = hashlib.sha256(
                json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            metadata = RUNNER.validate_data(
                path,
                {
                    "rows": 1,
                    "required_columns": ["Private", "Expend"],
                    "canonical_sha256": canonical,
                },
            )
            self.assertEqual(metadata["canonical_sha256"], canonical)
            path.write_text("Private,Expend\nNo,1000\n", encoding="utf-8")
            with self.assertRaisesRegex(RUNNER.RunError, "registered College dataset"):
                RUNNER.validate_data(
                    path,
                    {
                        "rows": 1,
                        "required_columns": ["Private", "Expend"],
                        "canonical_sha256": canonical,
                    },
                )

    def test_skill_runtime_hash_is_deterministic_and_content_sensitive(self):
        with TemporaryDirectory() as temporary:
            skill_root = Path(temporary)
            (skill_root / "references").mkdir()
            (skill_root / "assets").mkdir()
            (skill_root / "scripts").mkdir()
            (skill_root / "SKILL.md").write_text("skill\n", encoding="utf-8")
            (skill_root / "package.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
            (skill_root / "scripts" / "statectl.cjs").write_bytes(b"controller\n")
            reference = skill_root / "references" / "route.md"
            reference.write_text("route one\n", encoding="utf-8")
            (skill_root / "assets" / "template.yaml").write_text("value: 1\n", encoding="utf-8")

            first = RUNNER.skill_runtime_sha256(skill_root)
            self.assertEqual(first, RUNNER.skill_runtime_sha256(skill_root))
            target = {
                "skill_root": str(skill_root),
                "skill_runtime_sha256": first,
                "test_suite_runtime_sha256": RUNNER.suite_runtime_sha256(),
                "input_data": None,
            }
            RUNNER.validate_runtime_provenance(target)
            (skill_root / "project-hooks").mkdir()
            (skill_root / "project-hooks" / "stop.cjs").write_text(
                "hook\n", encoding="utf-8"
            )
            with_hooks = RUNNER.skill_runtime_sha256(skill_root)
            self.assertNotEqual(first, with_hooks)
            target["skill_runtime_sha256"] = with_hooks
            RUNNER.validate_runtime_provenance(target)
            reference.write_text("route two\n", encoding="utf-8")
            self.assertNotEqual(with_hooks, RUNNER.skill_runtime_sha256(skill_root))
            with self.assertRaisesRegex(RUNNER.RunError, "runtime changed"):
                RUNNER.validate_runtime_provenance(target)

    def test_summary_records_suite_target_and_runtime_provenance(self):
        record = self.passing_record()
        target = {
            "test_suite_version": "5.1.1",
            "test_suite_runtime_sha256": "suite123",
            "test_case_sha256": "case123",
            "causal_consultant_version": "5.1.0",
            "statectl_sha256": "abc123",
            "skill_runtime_sha256": "def456",
            "input_data": None,
        }
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary)
            returned = RUNNER.write_summary(
                results_dir,
                "smoke",
                1,
                [record],
                None,
                target,
            )
            summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(returned["final_result"]["status"], "pass")
        self.assertEqual(summary["schema_version"], 2)
        self.assertEqual(summary["test_suite"]["version"], "5.1.1")
        self.assertEqual(summary["test_suite"]["runtime_sha256"], "suite123")
        self.assertEqual(summary["test_suite"]["case_sha256"], "case123")
        self.assertEqual(summary["target"]["causal_consultant_version"], "5.1.0")
        self.assertEqual(summary["target"]["statectl_sha256"], "abc123")
        self.assertEqual(summary["target"]["skill_runtime_sha256"], "def456")
        self.assertEqual(summary["runtime"]["models"], ["claude-opus"])
        self.assertEqual(summary["runtime"]["fast_mode_states"], ["off"])
        self.assertEqual(summary["automated_checks"]["status"], "pass")
        self.assertEqual(summary["workflow_assessment"]["status"], "not_required")
        self.assertEqual(summary["final_result"]["status"], "pass")

    def test_standard_automated_pass_remains_pending(self):
        summary = RUNNER.build_summary(
            "standard",
            1,
            [self.passing_record()],
            None,
            self.summary_target(),
        )
        self.assertEqual(summary["automated_checks"]["status"], "pass")
        self.assertEqual(summary["workflow_assessment"]["status"], "pending")
        self.assertEqual(summary["final_result"]["status"], "pending")

    def test_mechanical_edge_automated_pass_remains_pending(self):
        summary = RUNNER.build_summary(
            "mechanical-edge",
            1,
            [self.passing_record()],
            None,
            self.summary_target(),
        )
        self.assertEqual(summary["automated_checks"]["status"], "pass")
        self.assertEqual(summary["workflow_assessment"]["status"], "pending")
        self.assertEqual(summary["final_result"]["status"], "pending")

    def test_assessment_finalizes_causal_edge_summary(self):
        summary = RUNNER.build_summary(
            "causal-edge",
            1,
            [self.passing_record()],
            None,
            self.summary_target(),
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            self.write_assessable_summary(results_dir, summary)
            notes = results_dir / "causal-assessment.md"
            notes.write_text("All registered boundaries were preserved.\n", encoding="utf-8")
            notes_sha256 = hashlib.sha256(notes.read_bytes()).hexdigest()
            final = RUNNER.assess_results(results_dir, "safe", notes)
            recorded = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
            markdown = (results_dir / "summary.md").read_text(encoding="utf-8")
        self.assertEqual(final, "pass")
        self.assertEqual(recorded["workflow_assessment"]["status"], "complete")
        self.assertEqual(recorded["workflow_assessment"]["rating"], "safe")
        self.assertEqual(
            recorded["workflow_assessment"]["notes_sha256"],
            notes_sha256,
        )
        self.assertEqual(recorded["final_result"]["status"], "pass")
        self.assertIn("Final result: **PASS**", markdown)

    def test_assessment_rejects_invalid_rating(self):
        summary = RUNNER.build_summary(
            "standard",
            1,
            [self.passing_record()],
            None,
            self.summary_target(),
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            RUNNER.write_summary_files(results_dir, summary)
            notes = results_dir / "workflow-assessment.md"
            notes.write_text("Review complete.\n", encoding="utf-8")
            with self.assertRaisesRegex(RUNNER.RunError, "invalid standard rating"):
                RUNNER.assess_results(results_dir, "safe", notes)

    def test_assessment_is_blocked_after_automated_failure(self):
        failed = self.passing_record()
        failed["state"] = {"ok": False, "errors": ["active operation remains"]}
        summary = RUNNER.build_summary(
            "standard", 1, [failed], None, self.summary_target()
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            RUNNER.write_summary_files(results_dir, summary)
            notes = results_dir / "workflow-assessment.md"
            notes.write_text("Review cannot proceed.\n", encoding="utf-8")
            with self.assertRaisesRegex(RUNNER.RunError, "automated checks did not pass"):
                RUNNER.assess_results(results_dir, "fail", notes)

    def test_assessment_notes_must_stay_inside_results(self):
        summary = RUNNER.build_summary(
            "standard", 1, [self.passing_record()], None, self.summary_target()
        )
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            results_dir = root / "results"
            results_dir.mkdir()
            RUNNER.write_summary_files(results_dir, summary)
            notes = root / "outside.md"
            notes.write_text("Review complete.\n", encoding="utf-8")
            with self.assertRaisesRegex(RUNNER.RunError, "inside results-dir"):
                RUNNER.assess_results(results_dir, "pass", notes)

    def test_assessment_notes_cannot_be_a_generated_summary(self):
        summary = RUNNER.build_summary(
            "standard", 1, [self.passing_record()], None, self.summary_target()
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            RUNNER.write_summary_files(results_dir, summary)
            with self.assertRaisesRegex(RUNNER.RunError, "generated summary"):
                RUNNER.assess_results(results_dir, "pass", results_dir / "summary.md")

    def test_causal_edge_weak_rating_remains_nonpassing(self):
        summary = RUNNER.build_summary(
            "causal-edge", 1, [self.passing_record()], None, self.summary_target()
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            self.write_assessable_summary(results_dir, summary)
            notes = results_dir / "causal-assessment.md"
            notes.write_text("Boundaries were safe but unclear.\n", encoding="utf-8")
            final = RUNNER.assess_results(results_dir, "weak", notes)
        self.assertEqual(final, "weak")

    def test_final_result_exit_codes_distinguish_pending(self):
        self.assertEqual(RUNNER.final_result_exit_code("pass"), 0)
        self.assertEqual(RUNNER.final_result_exit_code("pending"), RUNNER.EXIT_PENDING)
        self.assertNotEqual(RUNNER.final_result_exit_code("pending"), 0)
        self.assertEqual(RUNNER.final_result_exit_code("weak"), 1)
        self.assertEqual(RUNNER.final_result_exit_code("fail"), 1)

    def test_assessment_rejects_changed_review_evidence(self):
        summary = RUNNER.build_summary(
            "standard", 1, [self.passing_record()], None, self.summary_target()
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            self.write_assessable_summary(results_dir, summary)
            (results_dir / "conversation.md").write_text(
                "# Changed conversation\n", encoding="utf-8"
            )
            notes = results_dir / "workflow-assessment.md"
            notes.write_text("Review complete.\n", encoding="utf-8")
            with self.assertRaisesRegex(RUNNER.RunError, "review evidence changed"):
                RUNNER.assess_results(results_dir, "pass", notes)

    def test_assessment_notes_cannot_reuse_review_evidence(self):
        summary = RUNNER.build_summary(
            "standard", 1, [self.passing_record()], None, self.summary_target()
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            self.write_assessable_summary(results_dir, summary)
            with self.assertRaisesRegex(RUNNER.RunError, "separate from"):
                RUNNER.assess_results(results_dir, "pass", results_dir / "conversation.md")

    def test_summary_counts_attempted_response_and_validated_turns(self):
        failed = self.passing_record()
        failed["shell"] = {"ok": False, "errors": ["missing heading"]}
        failed["outcome"] = "fail"
        summary = RUNNER.build_summary(
            "smoke", 2, [failed], "turn 2 transport failed", self.summary_target()
        )
        markdown = RUNNER.render_summary_markdown(summary)
        self.assertEqual(summary["attempted_turns"], 1)
        self.assertEqual(summary["response_turns"], 1)
        self.assertEqual(summary["accepted_response_turns"], 1)
        self.assertEqual(summary["validated_turns"], 0)
        self.assertEqual(summary["automated_checks"]["status"], "fail")
        self.assertIn("Turn 1 response shell: missing heading", markdown)

    def test_response_and_accepted_response_counts_are_distinct(self):
        record = self.passing_record()
        record["response_accepted"] = False
        summary = RUNNER.build_summary(
            "smoke", 1, [record], "turn 1 resumed a different session", self.summary_target()
        )
        self.assertEqual(summary["response_turns"], 1)
        self.assertEqual(summary["accepted_response_turns"], 0)
        self.assertEqual(summary["automated_checks"]["status"], "fail")

    def test_summary_json_commits_after_markdown(self):
        summary = RUNNER.build_summary(
            "standard", 1, [self.passing_record()], None, self.summary_target()
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            self.write_assessable_summary(results_dir, summary)
            original_json = (results_dir / "summary.json").read_bytes()
            changed = deepcopy(summary)
            changed["workflow_assessment"]["status"] = "complete"
            changed["workflow_assessment"]["rating"] = "pass"
            changed["final_result"]["status"] = "pass"
            real_replace = RUNNER.os.replace

            def fail_json_commit(source, destination):
                if Path(destination).name == "summary.json":
                    raise OSError("simulated JSON commit failure")
                return real_replace(source, destination)

            with patch.object(RUNNER.os, "replace", side_effect=fail_json_commit):
                with self.assertRaisesRegex(RUNNER.RunError, "cannot write summary files"):
                    RUNNER.write_summary_files(results_dir, changed)
            self.assertEqual((results_dir / "summary.json").read_bytes(), original_json)
            self.assertFalse(list(results_dir.glob(".summary.*.tmp")))

    def test_conversation_keeps_failed_attempt(self):
        record = {
            "turn": 1,
            "label": "Attempt",
            "prompt": "Original prompt.",
            "response": None,
            "failure_phase": "transport",
            "failure_reason": "transport exited before a response was returned",
        }
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary)
            RUNNER.write_conversation(results_dir, [record])
            conversation = (results_dir / "conversation.md").read_text(encoding="utf-8")
        self.assertIn("Original prompt.", conversation)
        self.assertIn("_No completed response._", conversation)
        self.assertIn("Phase: `transport`", conversation)
        self.assertIn("transport exited before a response was returned", conversation)

    def test_suite_version_comes_from_skill_metadata(self):
        self.assertRegex(RUNNER.load_test_suite_version(), r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
