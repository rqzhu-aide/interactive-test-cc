import importlib.util
import hashlib
import json
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
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
                "manifest_counts": {},
                "counts": {},
                "role_counts": {"completion": {}, "infeasibility_evidence": {}},
                "errors": [],
            },
        }

    def summary_target(self):
        return {
            "test_suite_version": "5.2.8",
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
                    "[? Next Steps]\nNext step.",
                    2,
                )
                self.assertIn("prose appears before the heading shell", result["errors"])

    def test_heading_shell_accepts_allowed_openings(self):
        shell = (
            "[> Framing]\nFraming.\n\n"
            "[! Boundary]\nBoundary.\n\n"
            "[? Next Steps]\nNext step."
        )
        first_turn_openings = [
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
        for opening in first_turn_openings:
            with self.subTest(opening=opening):
                self.assertEqual(RUNNER.check_headings(opening + shell, 1)["errors"], [])
        for opening in ("", "[OK Confirmed] Work completed.\n\n"):
            with self.subTest(opening=opening):
                self.assertEqual(RUNNER.check_headings(opening + shell, 2)["errors"], [])

    def test_heading_shell_requires_welcome_only_on_first_turn(self):
        shell = (
            "[> Framing]\nFraming.\n\n"
            "[! Boundary]\nBoundary.\n\n"
            "[? Next Steps]\nNext step."
        )
        missing = RUNNER.check_headings(shell, 1)
        self.assertIn(
            "fresh-project welcome appears 0 times; expected 1 on turn 1",
            missing["errors"],
        )
        repeated = RUNNER.check_headings(f"{RUNNER.WELCOME_LINE}\n\n{shell}", 2)
        self.assertIn(
            "fresh-project welcome appears 1 times; expected 0 on turn 2",
            repeated["errors"],
        )

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
        self.assertEqual(RUNNER.check_headings(response, 2)["errors"], [])

    def test_response_state_accepts_exact_receipt_and_matching_menu(self):
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
        validator = {
            "response_receipt": {"response_markdown": response},
            "pending_decision": {
                "options": [{"number": 1}, {"number": 2}],
            },
        }
        self.assertEqual(RUNNER.check_response_state(response, validator), [])

    def test_response_state_accepts_exact_receipt_without_menu(self):
        response = (
            "[> Framing]\nFraming.\n\n"
            "[! Boundary]\nBoundary.\n\n"
            "[? Next Steps]\nContinue."
        )
        validator = {
            "response_receipt": {"response_markdown": response},
            "pending_decision": None,
        }
        self.assertEqual(RUNNER.check_response_state(response, validator), [])

    def test_response_state_rejects_missing_receipt_and_diagnoses_mismatch(self):
        response = "Rendered response"
        missing = RUNNER.check_response_state(
            response,
            {"response_receipt": None, "pending_decision": None},
        )
        self.assertIn("response_receipt is missing", missing)
        validator = {
            "response_receipt": {"response_markdown": "Different response"},
            "pending_decision": None,
        }
        self.assertEqual(RUNNER.check_response_state(response, validator), [])
        self.assertEqual(
            RUNNER.response_diagnostics(response, validator),
            ["delivered response differs from response_receipt.response_markdown"],
        )

    def test_response_receipt_comparison_normalizes_only_line_endings(self):
        validator = {
            "response_receipt": {"response_markdown": "First line\nSecond line"}
        }
        self.assertTrue(
            RUNNER.response_matches_receipt("First line\r\nSecond line", validator)
        )
        self.assertFalse(
            RUNNER.response_matches_receipt("First line - Second line", validator)
        )

    def test_scope_id_omission_does_not_block_bound_menu_approval(self):
        receipt = (
            "[> Framing]\nThe current report scope `f91e1e5c` is ready.\n\n"
            "[+ Consultant Options]\n"
            "    1. Revise the report scope.\n"
            "       Consultant read: Prepare a replacement.\n"
            "       Tradeoff: Defers report generation.\n"
            "    2. Generate the current report.\n"
            "       Consultant read: Use the exact ready scope.\n"
            "       Tradeoff: Produces the report now.\n\n"
            "[! Boundary]\nNo report was generated.\n\n"
            "[? Next Steps]\nChoose option 1 or 2."
        )
        delivered = receipt.replace("scope `f91e1e5c` is", "scope is")
        scope_id = "f91e1e5c-1111-4111-8111-111111111111"
        validator = {
            "response_receipt": {"response_markdown": receipt},
            "pending_decision": {
                "options": [
                    {
                        "number": 1,
                        "assignment": {"route": "report_writer", "scope_ref": None},
                    },
                    {
                        "number": 2,
                        "assignment": {
                            "route": "report_writer",
                            "scope_ref": {
                                "kind": "report",
                                "id": scope_id,
                                "revision": 1,
                            },
                        },
                    },
                ],
            },
        }
        self.assertFalse(RUNNER.response_matches_receipt(delivered, validator))
        approval_receipt_matches = RUNNER.response_matches_approval_receipt(
            delivered, validator
        )
        self.assertTrue(approval_receipt_matches)
        unbound = deepcopy(validator)
        unbound["pending_decision"]["options"][1]["assignment"]["scope_ref"]["id"] = (
            "aaaaaaaa-1111-4111-8111-111111111111"
        )
        self.assertFalse(
            RUNNER.response_matches_approval_receipt(delivered, unbound)
        )

        sequence = self.valid_scope_sequence()
        artifacts = {
            "counts": {"analysis_execution": 1},
            "usable_scope_refs": {
                "analysis_execution": [["analysis-2", 1]],
            },
            "changed_scope_refs": {"analysis_execution": []},
        }
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "mechanical-edge",
                13,
                sequence[12],
                {6: sequence[6], 11: sequence[11]},
                artifacts,
                approval_receipt_matches=approval_receipt_matches,
            ),
            [],
        )

    def test_scope_id_exception_rejects_multiple_omissions(self):
        first = "aaaaaaaa-1111-4111-8111-111111111111"
        second = "bbbbbbbb-2222-4222-8222-222222222222"
        receipt = (
            "The report scope `aaaaaaaa` is ready. "
            "The analysis scope `bbbbbbbb` is ready."
        )
        delivered = receipt.replace(" `aaaaaaaa`", "").replace(" `bbbbbbbb`", "")
        validator = {
            "response_receipt": {"response_markdown": receipt},
            "pending_decision": {
                "options": [
                    {
                        "number": 1,
                        "assignment": {
                            "route": "report_writer",
                            "scope_ref": {"kind": "report", "id": first, "revision": 1},
                        },
                    },
                    {
                        "number": 2,
                        "assignment": {
                            "route": "analysis_execution.single_time_observational",
                            "scope_ref": {"kind": "analysis", "id": second, "revision": 1},
                        },
                    },
                ],
            },
        }
        self.assertFalse(
            RUNNER.response_matches_approval_receipt(delivered, validator)
        )

    def test_material_receipt_mismatch_blocks_registered_approval_turns(self):
        receipt = (
            "[> Framing]\nThe current report scope `f91e1e5c` is ready.\n"
            "[+ Consultant Options]\n"
            "    1. Revise the scope.\n"
            "    2. Generate the scope.\n"
            "[! Boundary]\nNo report was generated.\n"
            "[? Next Steps]\nChoose option 1 or 2."
        )
        delivered = receipt.replace("is ready.", "is not ready.")
        validator = {
            "response_receipt": {"response_markdown": receipt},
            "pending_decision": {
                "options": [{"number": 1}, {"number": 2}],
            },
        }
        approval_receipt_matches = RUNNER.response_matches_approval_receipt(
            delivered, validator
        )
        self.assertFalse(approval_receipt_matches)
        sequence = self.valid_scope_sequence()
        blockers = RUNNER.next_prompt_blockers(
            "mechanical-edge",
            13,
            sequence[12],
            {6: sequence[6], 11: sequence[11]},
            {
                "counts": {"analysis_execution": 1},
                "usable_scope_refs": {
                    "analysis_execution": [["analysis-2", 1]],
                },
                "changed_scope_refs": {"analysis_execution": []},
            },
            approval_receipt_matches=approval_receipt_matches,
        )
        self.assertIn(
            "the next approval does not match its committed response",
            blockers,
        )
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "smoke",
                2,
                {"analysis": {}, "report": None},
                {},
                {"counts": {}},
                approval_receipt_matches=False,
            ),
            [],
        )

    def test_direct_approval_still_requires_exact_receipt(self):
        validator = {
            "response_receipt": {"response_markdown": "Committed response"},
            "pending_decision": None,
        }
        approval_receipt_matches = RUNNER.response_matches_approval_receipt(
            "Different response", validator
        )
        self.assertFalse(approval_receipt_matches)
        ready = self.standard_scope_sequence()[6]
        self.assertIn(
            "the next approval does not match its committed response",
            RUNNER.next_prompt_blockers(
                "standard",
                7,
                ready,
                {6: ready},
                {"counts": {}},
                approval_receipt_matches=approval_receipt_matches,
            ),
        )

    def test_response_state_rejects_unbacked_menu_and_diagnoses_hidden_menu(self):
        menu = (
            "[> Framing]\nFrame.\n"
            "[+ Consultant Options]\n"
            "    1. First.\n"
            "    2. Second.\n"
            "[! Boundary]\nBoundary.\n"
            "[? Next Steps]\nChoose."
        )
        without_menu = (
            "[> Framing]\nFrame.\n"
            "[! Boundary]\nBoundary.\n"
            "[? Next Steps]\nContinue."
        )
        unbacked = {
            "response_receipt": {"response_markdown": menu},
            "pending_decision": None,
        }
        self.assertIn(
            "Consultant Options have no pending_decision",
            RUNNER.check_response_state(menu, unbacked),
        )
        hidden = {
            "response_receipt": {"response_markdown": without_menu},
            "pending_decision": {"options": [{"number": 1}, {"number": 2}]},
        }
        self.assertEqual(RUNNER.check_response_state(without_menu, hidden), [])
        self.assertIn(
            "pending_decision has no visible Consultant Options",
            RUNNER.response_diagnostics(without_menu, hidden),
        )

    def test_response_state_rejects_visible_option_number_mismatch(self):
        response = (
            "[> Framing]\nFrame.\n"
            "[+ Consultant Options]\n"
            "    1. First.\n"
            "    3. Third.\n"
            "[! Boundary]\nBoundary.\n"
            "[? Next Steps]\nChoose."
        )
        errors = RUNNER.check_response_state(
            response,
            {
                "response_receipt": {"response_markdown": response},
                "pending_decision": {
                    "options": [{"number": 1}, {"number": 2}],
                },
            },
        )
        self.assertIn(
            "Consultant Options numbers do not match pending_decision.options",
            errors,
        )

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
            _, errors, blockers = RUNNER.validate_state(
                Path("statectl.cjs"),
                "node",
                Path("."),
                "project-1" if previous_revision is not None else None,
                previous_revision,
                previous_manifest_count,
                manifest_count,
            )
        return errors, blockers

    def test_response_diagnostic_does_not_invalidate_idle_boundary(self):
        response = "Delivered response"
        with patch.object(
            RUNNER,
            "run_json",
            return_value=(0, self.state_payload(3), ""),
        ):
            validator, errors, blockers = RUNNER.validate_state(
                Path("statectl.cjs"),
                "node",
                Path("."),
                None,
                None,
                0,
                0,
            )
        validator = {
            **validator,
            "response_receipt": {"response_markdown": "Stored response"},
            "pending_decision": None,
        }
        errors.extend(RUNNER.check_response_state(response, validator))
        diagnostics = RUNNER.response_diagnostics(response, validator)
        self.assertEqual(errors, [])
        self.assertIn(
            "delivered response differs from response_receipt.response_markdown",
            diagnostics,
        )
        self.assertEqual(blockers, [])

    def test_active_operation_blocks_continuation(self):
        payload = self.state_payload(3)
        payload["active_operation"] = {"id": "operation-1"}
        with patch.object(RUNNER, "run_json", return_value=(0, payload, "")):
            _, errors, blockers = RUNNER.validate_state(
                Path("statectl.cjs"),
                "node",
                Path("."),
                None,
                None,
                0,
                0,
            )
        self.assertIn("active_operation is not null", errors)
        self.assertEqual(blockers, ["active_operation is not null"])

    def test_validator_warning_shape_blocks_but_known_warnings_do_not(self):
        invalid = self.state_payload(3)
        del invalid["warnings"]
        with patch.object(RUNNER, "run_json", return_value=(0, invalid, "")):
            _, errors, blockers = RUNNER.validate_state(
                Path("statectl.cjs"), "node", Path("."), None, None, 0, 0
            )
        self.assertIn("validator warnings is missing or invalid", errors)
        self.assertEqual(blockers, ["validator warnings is missing or invalid"])

        warning = self.state_payload(3)
        warning["warnings"] = [{"code": "ARTIFACT_UNAVAILABLE"}]
        with patch.object(RUNNER, "run_json", return_value=(0, warning, "")):
            _, errors, blockers = RUNNER.validate_state(
                Path("statectl.cjs"), "node", Path("."), None, None, 0, 0
            )
        self.assertEqual(errors, [f"validator warnings: {warning['warnings']}"])
        self.assertEqual(blockers, [])

    def test_revision_must_strictly_increase(self):
        for revision, prior_manifests, manifests in (
            (26, 0, 0),
            (29, 0, 0),
            (29, 2, 3),
            (29, 2, 4),
        ):
            with self.subTest(
                revision=revision,
                prior_manifests=prior_manifests,
                manifests=manifests,
            ):
                self.assertEqual(
                    self.validate_revision(
                        25, revision, prior_manifests, manifests
                    ),
                    ([], []),
                )

    def test_nonincreasing_revision_blocks_continuation(self):
        for revision in (25, 24):
            with self.subTest(revision=revision):
                errors, blockers = self.validate_revision(25, revision)
                self.assertEqual(
                    errors,
                    ["revision did not increase during the completed turn"],
                )
                self.assertEqual(blockers, errors)

    def test_all_suites_require_response_state_capabilities(self):
        required = {
            "response_rendering": 1,
            "pending_decision": 1,
            "response_receipt": 1,
            "startup_notice": 1,
            "scope_snapshot": 1,
            "analysis_contract": 1,
            "completion_protocol": 1,
            "artifact_roles": 1,
        }
        for capability in required:
            capabilities = dict(required)
            del capabilities[capability]
            with self.subTest(capability=capability):
                with self.assertRaisesRegex(RUNNER.RunError, f"{capability} 1"):
                    RUNNER.require_controller_capabilities(
                        "college-observational-policy",
                        {"capabilities": capabilities},
                    )
        RUNNER.require_controller_capabilities(
            "college-observational-policy", {"capabilities": required}
        )

    def test_discovery_suite_requires_discovery_contract_capability(self):
        base = {
            "response_rendering": 1,
            "pending_decision": 1,
            "response_receipt": 1,
            "startup_notice": 1,
            "scope_snapshot": 1,
            "analysis_contract": 1,
            "completion_protocol": 1,
            "artifact_roles": 1,
        }
        with self.assertRaisesRegex(RUNNER.RunError, "discovery_contract 1"):
            RUNNER.require_controller_capabilities(
                "college-discovery-handoff", {"capabilities": base}
            )
        RUNNER.require_controller_capabilities(
            "college-discovery-handoff",
            {"capabilities": {**base, "discovery_contract": 1}},
        )

    def test_registry_rejects_unknown_artifact_expectation(self):
        registry = json.loads(RUNNER.CASES_PATH.read_text(encoding="utf-8"))
        registry["tests"]["college-observational-policy"]["turns"][0]["artifacts"] = {
            "analysis_exection": 0
        }
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

    def test_registry_contains_exactly_four_live_cases(self):
        cases = RUNNER.load_cases()
        self.assertEqual(tuple(cases), RUNNER.TEST_IDS)
        self.assertEqual(
            {test_id: len(case["turns"]) for test_id, case in cases.items()},
            {
                "college-observational-policy": 13,
                "college-discovery-handoff": 8,
                "star-interference-saturation": 9,
                "schooling-iv-late": 9,
            },
        )

    def test_discovery_registry_tracks_handoff(self):
        turns = RUNNER.load_cases()["college-discovery-handoff"]["turns"]
        self.assertEqual(
            [turn["artifacts"]["total"] for turn in turns],
            [0, 0, 0, 1, 1, 1, 2, 2],
        )
        self.assertEqual(
            [turn["artifacts"]["causal_discovery"] for turn in turns],
            [0, 0, 0, 1, 1, 1, 1, 1],
        )
        self.assertEqual(
            RUNNER.APPROVAL_BOUND_TURNS["college-discovery-handoff"], {7}
        )
        prompts = "\n".join(turn["prompt"] for turn in turns)
        for requirement in (
            "hypothesis generation only",
            "exactly one durable discovery artifact",
            "must not determine adjustment",
            "approve the exact current analysis scope",
            "Separate hypothesis-generating structure",
        ):
            self.assertIn(requirement, prompts)
        reference = (ROOT / "references" / "college-discovery-handoff.md").read_text(
            encoding="utf-8"
        )
        for requirement in (
            "candidate-only",
            "neither selects an adjustment set",
            "One ready analysis scope",
        ):
            self.assertIn(requirement, reference)

    def test_new_method_cases_have_distinct_fixed_routes_and_support(self):
        expected = {
            "star-interference-saturation": (
                "interference_spillovers",
                "policy-making-and-transportability",
            ),
            "schooling-iv-late": ("instrumental_variables", "statistical-validity"),
        }
        self.assertEqual(RUNNER.SINGLE_ANALYSIS_REPORT_CASES, expected)
        for test_id, (route, support) in expected.items():
            with self.subTest(test_id=test_id):
                reference = (ROOT / "references" / f"{test_id}.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn(route, reference)
                self.assertIn(support, reference)

        interference = RUNNER.load_cases()["star-interference-saturation"]
        prompts = "\n".join(turn["prompt"] for turn in interference["turns"])
        for requirement in (
            "leave-one-out school exposure map",
            "randomization of other-pupil exposure",
            "Do not estimate a separate direct intention-to-treat effect",
            "Label outcome patterns across saturation as noncausal",
        ):
            self.assertIn(requirement, prompts)
        reference = (
            ROOT / "references" / "star-interference-saturation.md"
        ).read_text(encoding="utf-8")
        for requirement in (
            "does not invent classroom or peer ties",
            "rather than an interference solution",
            "causal spillover estimates",
        ):
            self.assertIn(requirement, reference)

    def interference_snapshot(
        self,
        status,
        *,
        route="interference_spillovers",
        support="policy-making-and-transportability",
        scope_id="interference-1",
    ):
        return {
            "analysis": {
                route: {
                    "scope_id": scope_id,
                    "scope_revision": 1,
                    "current_status": status,
                    "support": support,
                    "last_updated": "2026-01-01T00:00:04Z",
                }
            },
            "report": None,
        }

    def test_interference_approval_requires_exact_route_and_support(self):
        ready = self.interference_snapshot("ready")
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "star-interference-saturation",
                5,
                ready,
                {4: ready},
                {"counts": {}},
            ),
            [],
        )
        wrong_route = self.interference_snapshot(
            "ready", route="randomized_assignment"
        )
        wrong_support = self.interference_snapshot("ready", support=None)
        for snapshot in (wrong_route, wrong_support):
            with self.subTest(snapshot=snapshot):
                blockers = RUNNER.next_prompt_blockers(
                    "star-interference-saturation",
                    5,
                    snapshot,
                    {4: snapshot},
                    {"counts": {}},
                )
                self.assertIn(
                    "the next approval requires one ready interference_spillovers "
                    "scope with policy-making-and-transportability support",
                    blockers,
                )

    def test_interference_scope_oracle_requires_exact_preservation(self):
        ready = self.interference_snapshot("ready")
        completed = self.interference_snapshot("done")
        history = {}
        self.assertEqual(
            RUNNER.check_single_analysis_report_scopes(
                4,
                ready,
                history,
                "interference_spillovers",
                "policy-making-and-transportability",
            ),
            [],
        )
        self.assertEqual(
            RUNNER.check_single_analysis_report_scopes(
                5,
                completed,
                history,
                "interference_spillovers",
                "policy-making-and-transportability",
            ),
            [],
        )
        changed = self.interference_snapshot("done", scope_id="interference-2")
        errors = RUNNER.check_single_analysis_report_scopes(
            5,
            changed,
            {4: ready},
            "interference_spillovers",
            "policy-making-and-transportability",
        )
        self.assertIn("turn 5 must preserve the exact approved analysis scope", errors)

    def test_interference_continuation_accepts_completion_or_infeasibility(self):
        ready = self.interference_snapshot("ready")
        reference = ["interference-1", 1]
        cases = (
            (
                self.interference_snapshot("done"),
                {
                    "counts": {"analysis_execution": 1},
                    "usable_scope_refs": {"analysis_execution": [reference]},
                },
            ),
            (
                self.interference_snapshot("blocked"),
                {
                    "counts": {},
                    "infeasibility_scope_refs": {
                        "analysis_execution": [reference]
                    },
                },
            ),
        )
        for current, evidence in cases:
            status = next(iter(current["analysis"].values()))["current_status"]
            with self.subTest(status=status):
                evidence.update(
                    {
                        "intact_routes": {"analysis_execution": True},
                        "changed_scope_refs": {"analysis_execution": []},
                    }
                )
                self.assertEqual(
                    RUNNER.next_prompt_blockers(
                        "star-interference-saturation",
                        6,
                        current,
                        {4: ready, 5: current},
                        evidence,
                    ),
                    [],
                )

    def test_observational_registry_allows_only_optional_audit_artifacts(self):
        turns = RUNNER.load_cases()["college-observational-policy"]["turns"]
        for turn in turns[2:4]:
            with self.subTest(label=turn["label"]):
                expected = turn["artifacts"]
                self.assertEqual(expected["new"], 0)
                self.assertEqual(expected["causal_discovery"], 0)
                self.assertEqual(expected["analysis_execution"], 0)
                self.assertEqual(expected["report_writer"], 0)

    def test_registered_data_uses_canonical_fingerprints(self):
        fingerprints = {
            case["data"]["canonical_sha256"]
            for case in RUNNER.load_cases().values()
        }
        self.assertEqual(
            fingerprints,
            {
                "5a373ac7af1bc13caae0e08bc3e7230fac28eb5be265132372f5bc5ffe65806c",
                "0613304257a0722d776cfaac3b2d9fae513e32969395f7b312ed6303db8a7b27",
                "23a5bf9cd485e660f7d7c8af1c10ff8efdad84d36302f35ab056e12a7f98afbf",
            },
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

    def standard_same_route_scope_sequence(self):
        sequence = self.standard_scope_sequence()
        for turn in (6, 7, 8):
            entry = sequence[turn]["analysis"].pop("single_time_observational")
            sequence[turn]["analysis"]["descriptive_association"] = entry
        for turn in range(9, 14):
            sequence[turn]["analysis"].pop("single_time_observational", None)
        return sequence

    def test_standard_scope_oracle_accepts_same_design_replacement(self):
        history = {}
        for turn, snapshot in self.standard_same_route_scope_sequence().items():
            self.assertEqual(
                RUNNER.check_standard_scopes(turn, snapshot, history),
                [],
                f"turn {turn}",
            )

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
        self.assertIn("turn 9 must create or replace exactly one analysis scope", errors)

    def test_standard_scope_oracle_accepts_controller_valid_first_route(self):
        ready = deepcopy(self.standard_scope_sequence()[6])
        entry = ready["analysis"].pop("single_time_observational")
        ready["analysis"]["descriptive_association"] = entry
        history = {}
        self.assertEqual(RUNNER.check_standard_scopes(6, ready, history), [])
        self.assertEqual(history[6]["analysis"], ready["analysis"])

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

    def test_standard_scope_oracle_rejects_new_scope_with_prior_revision(self):
        sequence = self.standard_scope_sequence()
        history = {7: sequence[7]}
        ready = deepcopy(sequence[9])
        ready["analysis"]["descriptive_association"]["scope_revision"] = 2
        self.assertEqual(RUNNER.check_standard_scopes(8, sequence[8], history), [])
        errors = RUNNER.check_standard_scopes(9, ready, history)
        self.assertIn("turn 9 new analysis scope must start at revision 1", errors)

    def test_standard_scope_oracle_accepts_optional_support(self):
        sequence = self.standard_scope_sequence()
        history = {7: sequence[7]}
        ready = deepcopy(sequence[9])
        ready["analysis"]["descriptive_association"]["support"] = None
        self.assertEqual(RUNNER.check_standard_scopes(8, sequence[8], history), [])
        self.assertEqual(RUNNER.check_standard_scopes(9, ready, history), [])

    def test_standard_scope_oracle_accepts_controller_selected_second_route(self):
        sequence = self.standard_scope_sequence()
        history = {7: sequence[7]}
        ready = deepcopy(sequence[9])
        entry = ready["analysis"].pop("descriptive_association")
        ready["analysis"]["panel_longitudinal"] = entry
        self.assertEqual(RUNNER.check_standard_scopes(8, sequence[8], history), [])
        self.assertEqual(RUNNER.check_standard_scopes(9, ready, history), [])

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

    def discovery_contract(self):
        return {
            "target": "Expend increase and later Grad.Rate",
            "input_refs": ["data.csv"],
            "variables": [
                "Private",
                "Top10perc",
                "S.F.Ratio",
                "Expend",
                "Grad.Rate",
            ],
            "method_plan": "stable PC with bootstrap edge-stability diagnostics",
            "constraints": [
                "Private and Top10perc are baseline",
                "Expend precedes Grad.Rate",
            ],
            "diagnostic_requirements": ["stability or sensitivity diagnostics"],
            "output_type": "local adjacency or neighborhood",
            "claim_boundary": "candidate_only",
        }

    def discovery_entry(self, status, last_updated):
        return {
            "scope_id": "55555555-5555-4555-8555-555555555555",
            "scope_revision": 1,
            "status": status,
            "execution_contract": self.discovery_contract(),
            "last_updated": last_updated,
        }

    def discovery_scope_sequence(self):
        empty = {"analysis": {}, "report": None, "discovery": None}
        scoped = {
            "analysis": {},
            "report": None,
            "discovery": self.discovery_entry("scoped", "2026-01-01T00:00:03Z"),
        }
        artifact = {
            "analysis": {},
            "report": None,
            "discovery": self.discovery_entry(
                "artifact_created", "2026-01-01T00:00:04Z"
            ),
        }
        ready = self.analysis_snapshot(
            "discovery-analysis", 1, "ready", "2026-01-01T00:00:06Z"
        )
        ready["analysis"]["single_time_observational"]["support"] = None
        ready["discovery"] = deepcopy(artifact["discovery"])
        completed = deepcopy(ready)
        completed["analysis"]["single_time_observational"].update(
            {
                "current_status": "done",
                "last_updated": "2026-01-01T00:00:07Z",
            }
        )
        return {
            1: deepcopy(empty),
            2: deepcopy(empty),
            3: scoped,
            4: deepcopy(artifact),
            5: deepcopy(artifact),
            6: ready,
            7: completed,
            8: deepcopy(completed),
        }

    def test_discovery_scope_oracle_accepts_fixed_sequence(self):
        history = {}
        for turn, snapshot in self.discovery_scope_sequence().items():
            self.assertEqual(
                RUNNER.check_discovery_scopes(turn, snapshot, history),
                [],
            )

    def test_discovery_scope_oracle_rejects_wrong_boundaries(self):
        sequence = self.discovery_scope_sequence()
        early = deepcopy(sequence[4])
        early["analysis"] = self.analysis_snapshot(
            "early", 1, "ready", "2026-01-01T00:00:04Z"
        )["analysis"]
        self.assertIn(
            "turn 4 must not prepare an analysis scope",
            RUNNER.check_discovery_scopes(4, early, {3: sequence[3]}),
        )

        incomplete = deepcopy(sequence[3])
        incomplete["discovery"]["execution_contract"]["diagnostic_requirements"] = []
        self.assertIn(
            "turn 3 discovery contract must preserve constraints and diagnostics",
            RUNNER.check_discovery_scopes(3, incomplete, {}),
        )

        drifted = deepcopy(sequence[4])
        drifted["discovery"]["execution_contract"]["method_plan"] = (
            "different discovery family"
        )
        self.assertIn(
            "turn 4 must run the exact scoped discovery contract",
            RUNNER.check_discovery_scopes(4, drifted, {3: sequence[3]}),
        )

        wrong = self.analysis_snapshot(
            "other", 1, "done", "2026-01-01T00:00:07Z"
        )
        wrong["discovery"] = deepcopy(sequence[7]["discovery"])
        self.assertIn(
            "turn 7 must complete the exact ready analysis scope",
            RUNNER.check_discovery_scopes(7, wrong, {6: sequence[6]}),
        )

        changed = deepcopy(sequence[8])
        changed["analysis"]["single_time_observational"]["support"] = (
            "heterogeneous-effects"
        )
        self.assertIn(
            "turn 8 must leave the completed analysis scope unchanged",
            RUNNER.check_discovery_scopes(8, changed, {7: sequence[7]}),
        )

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

    def test_scope_oracle_keeps_failed_snapshot_for_later_diagnostics(self):
        history = {}
        missing = {"analysis": {}, "report": None}
        errors = RUNNER.check_mechanical_edge_scopes(4, missing, history)
        self.assertIn("turn 4 must have one analysis scope; found none", errors)
        self.assertEqual(history[4], missing)
        later = RUNNER.check_mechanical_edge_scopes(6, missing, history)
        self.assertTrue(later)
        self.assertEqual(history[6], missing)

    def test_standard_approval_requires_one_ready_scope(self):
        ready = deepcopy(self.standard_scope_sequence()[6])
        ready["analysis"]["panel_longitudinal"] = {
            "scope_id": "analysis-2",
            "scope_revision": 1,
            "current_status": "ready",
            "support": None,
            "last_updated": "2026-01-01T00:00:06Z",
        }
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard",
                7,
                ready,
                {6: ready},
                {"counts": {}},
            )
        )

    def test_discovery_continuation_requires_its_durable_handoff(self):
        sequence = self.discovery_scope_sequence()
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "discovery",
                4,
                sequence[3],
                {3: sequence[3]},
                {"counts": {}},
            ),
            [],
        )
        missing_scope = deepcopy(sequence[3])
        missing_scope["discovery"] = None
        self.assertIn(
            "the bounded discovery run requires one complete scoped contract",
            RUNNER.next_prompt_blockers(
                "discovery",
                4,
                missing_scope,
                {3: missing_scope},
                {"counts": {}},
            ),
        )
        incomplete_contract = deepcopy(sequence[3])
        incomplete_contract["discovery"]["execution_contract"]["constraints"] = []
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "discovery",
                4,
                incomplete_contract,
                {3: incomplete_contract},
                {"counts": {}},
            )
        )

        discovery_ref = list(RUNNER.scope_ref(sequence[4]["discovery"]))
        discovery = {
            "counts": {"causal_discovery": 1},
            "intact_routes": {
                "causal_discovery": True,
                "analysis_execution": True,
            },
            "usable_scope_refs": {"causal_discovery": [discovery_ref]},
            "changed_scope_refs": {
                "causal_discovery": [],
                "analysis_execution": [],
            },
            "manifests": [
                {
                    "route": "causal_discovery",
                    "scope_ref": {
                        "kind": "discovery",
                        "id": discovery_ref[0],
                        "revision": discovery_ref[1],
                    },
                    "discovery_contract": self.discovery_contract(),
                }
            ],
        }
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "discovery",
                5,
                sequence[4],
                {4: sequence[4]},
                discovery,
            ),
            [],
        )

        missing = deepcopy(discovery)
        missing["counts"]["causal_discovery"] = 0
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "discovery",
                5,
                sequence[4],
                {4: sequence[4]},
                missing,
            )
        )
        unbound = deepcopy(discovery)
        unbound["usable_scope_refs"]["causal_discovery"] = []
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "discovery",
                5,
                sequence[4],
                {4: sequence[4]},
                unbound,
            )
        )
        mismatched_contract = deepcopy(discovery)
        mismatched_contract["manifests"][0]["discovery_contract"]["method_plan"] = (
            "GES"
        )
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "discovery",
                5,
                sequence[4],
                {4: sequence[4]},
                mismatched_contract,
            )
        )
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "discovery",
                7,
                sequence[6],
                {6: sequence[6]},
                discovery,
            ),
            [],
        )

        completed = deepcopy(discovery)
        completed["counts"]["analysis_execution"] = 1
        completed["usable_scope_refs"]["analysis_execution"] = [
            ["discovery-analysis", 1]
        ]
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "discovery",
                8,
                sequence[7],
                {6: sequence[6]},
                completed,
            ),
            [],
        )

        completed["usable_scope_refs"]["analysis_execution"] = [["other", 1]]
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "discovery",
                8,
                sequence[7],
                {6: sequence[6]},
                completed,
            )
        )

    def test_standard_continuation_allows_wrong_but_unique_ready_route(self):
        ready = deepcopy(self.standard_scope_sequence()[6])
        entry = ready["analysis"].pop("single_time_observational")
        ready["analysis"]["panel_longitudinal"] = entry
        blockers = RUNNER.next_prompt_blockers(
            "standard",
            7,
            ready,
            {6: ready},
            {"counts": {}},
        )
        self.assertEqual(blockers, [])

    def test_standard_continuation_blocks_missing_consumed_evidence(self):
        empty = {"analysis": {}, "report": None}
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard",
                7,
                empty,
                {6: empty},
                {"counts": {}},
            )
        )
        sequence = self.standard_scope_sequence()
        completed = sequence[7]
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard",
                8,
                completed,
                {6: sequence[6], 7: completed},
                {"counts": {}},
            )
        )
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "standard",
                8,
                completed,
                {6: sequence[6], 7: completed},
                {
                    "counts": {"analysis_execution": 1},
                    "usable_scope_refs": {
                        "analysis_execution": [["analysis-1", 1]],
                    },
                },
            ),
            [],
        )

    def test_standard_continuation_requires_the_approved_scope_identity(self):
        sequence = self.standard_scope_sequence()
        wrong = self.analysis_snapshot(
            "analysis-other", 1, "done", "2026-01-01T00:00:07Z"
        )
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard",
                8,
                wrong,
                {6: sequence[6]},
                {
                    "counts": {"analysis_execution": 1},
                    "usable_scope_refs": {
                        "analysis_execution": [["analysis-1", 1]],
                    },
                },
            )
        )

    def test_standard_continuation_rejects_wrong_artifact_scope_identity(self):
        sequence = self.standard_scope_sequence()
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard",
                8,
                sequence[7],
                {6: sequence[6]},
                {
                    "counts": {"analysis_execution": 1},
                    "usable_scope_refs": {
                        "analysis_execution": [["analysis-other", 1]],
                    },
                },
            )
        )

    def test_standard_continuation_ignores_unrelated_scope_and_artifact(self):
        sequence = self.standard_scope_sequence()
        current = deepcopy(sequence[7])
        current["analysis"]["panel_longitudinal"] = {
            "scope_id": "analysis-other",
            "scope_revision": 1,
            "current_status": "done",
            "support": None,
            "last_updated": "2026-01-01T00:00:07Z",
        }
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "standard",
                8,
                current,
                {6: sequence[6]},
                {
                    "counts": {"analysis_execution": 2},
                    "usable_scope_refs": {
                        "analysis_execution": [
                            ["analysis-1", 1],
                            ["analysis-other", 1],
                        ],
                    },
                },
            ),
            [],
        )

    def test_standard_continuation_rejects_duplicate_required_evidence(self):
        sequence = self.standard_scope_sequence()
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard",
                8,
                sequence[7],
                {6: sequence[6]},
                {
                    "counts": {"analysis_execution": 2},
                    "usable_scope_refs": {
                        "analysis_execution": [
                            ["analysis-1", 1],
                            ["analysis-1", 1],
                        ],
                    },
                },
            )
        )

    def test_standard_report_gate_accepts_displaced_first_scope_with_exact_artifacts(self):
        sequence = self.standard_same_route_scope_sequence()
        history = {6: sequence[6], 9: sequence[9]}
        artifacts = {
            "counts": {"analysis_execution": 2},
            "usable_scope_refs": {
                "analysis_execution": [["analysis-1", 1], ["analysis-2", 1]],
            },
            "changed_scope_refs": {"analysis_execution": []},
        }
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "standard", 11, sequence[10], history, artifacts
            ),
            [],
        )

        missing = deepcopy(artifacts)
        missing["usable_scope_refs"]["analysis_execution"].pop(0)
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard", 11, sequence[10], history, missing
            )
        )
        duplicated = deepcopy(artifacts)
        duplicated["usable_scope_refs"]["analysis_execution"].append(["analysis-1", 1])
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard", 11, sequence[10], history, duplicated
            )
        )
        changed = deepcopy(artifacts)
        changed["changed_scope_refs"]["analysis_execution"] = [["analysis-1", 1]]
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard", 11, sequence[10], history, changed
            )
        )
        latest_not_done = deepcopy(sequence[10])
        latest_not_done["analysis"]["descriptive_association"]["current_status"] = "ready"
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard", 11, latest_not_done, history, artifacts
            )
        )

    def test_standard_derivative_gate_uses_only_required_report_integrity(self):
        sequence = self.standard_scope_sequence()
        artifacts = {
            "counts": {"analysis_execution": 2, "report_writer": 1},
            "usable_scope_refs": {
                "analysis_execution": [["analysis-1", 1], ["analysis-2", 1]],
                "report_writer": [["report-1", 1]],
            },
            "intact_routes": {
                "analysis_execution": False,
                "report_writer": False,
            },
            "changed_scope_refs": {
                "analysis_execution": [["analysis-other", 1]],
                "report_writer": [["report-other", 1]],
            },
        }
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "standard",
                13,
                sequence[12],
                {11: sequence[11]},
                artifacts,
            ),
            [],
        )
        artifacts["changed_scope_refs"]["report_writer"].append(["report-1", 1])
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "standard",
                13,
                sequence[12],
                {11: sequence[11]},
                artifacts,
            )
        )

    def test_mechanical_continuation_requires_distinct_scope_references(self):
        sequence = self.valid_scope_sequence()
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "mechanical-edge",
                7,
                sequence[6],
                {4: sequence[4], 6: sequence[6]},
                {"counts": {}},
            ),
            [],
        )
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "mechanical-edge",
                7,
                sequence[4],
                {4: sequence[4], 6: sequence[4]},
                {"counts": {}},
            )
        )

    def test_mechanical_stale_report_check_does_not_require_analysis_bytes(self):
        sequence = self.valid_scope_sequence()
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "mechanical-edge",
                12,
                sequence[11],
                {6: sequence[6], 10: sequence[10], 11: sequence[11]},
                {"counts": {}},
            ),
            [],
        )

    def test_mechanical_stale_report_requires_distinct_scope_references(self):
        sequence = self.valid_scope_sequence()
        unchanged = sequence[10]
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "mechanical-edge",
                12,
                unchanged,
                {6: sequence[6], 10: unchanged, 11: unchanged},
                {"counts": {}},
            )
        )

    def test_causal_edge_approval_requires_one_ready_report_scope(self):
        empty = {"analysis": {}, "report": None}
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "causal-edge",
                8,
                empty,
                {},
                {"counts": {}},
            )
        )
        ready = self.report_snapshot(
            empty,
            "report-1",
            1,
            "ready",
            "2026-01-01T00:00:07Z",
        )
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "causal-edge",
                8,
                ready,
                {},
                {"counts": {}},
            ),
            [],
        )

    def test_causal_edge_continuation_blocks_false_report_premise(self):
        empty = {"analysis": {}, "report": None}
        self.assertEqual(
            RUNNER.next_prompt_blockers(
                "causal-edge",
                7,
                empty,
                {},
                {"counts": {}},
            ),
            [],
        )
        completed = self.analysis_snapshot(
            "analysis-1",
            1,
            "done",
            "2026-01-01T00:00:06Z",
        )
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "causal-edge",
                7,
                completed,
                {},
                {"counts": {"analysis_execution": 1}},
            )
        )
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "causal-edge",
                7,
                empty,
                {4: completed},
                {"counts": {}},
            )
        )
        self.assertTrue(
            RUNNER.next_prompt_blockers(
                "causal-edge",
                7,
                empty,
                {},
                {
                    "counts": {},
                    "intact_routes": {"analysis_execution": False},
                },
            )
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
        if "artifact_role" in manifest:
            record["artifact_role"] = manifest["artifact_role"]
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

    def write_schema2_analysis_artifact(self, workdir, artifact_role):
        artifact = workdir / "output" / "analysis"
        artifact.mkdir(parents=True)
        evidence_path = "output/analysis/evidence.txt"
        (artifact / "evidence.txt").write_text(
            "execution evidence\n", encoding="utf-8"
        )
        requirement = "fit approved estimator"
        reference = {
            "kind": "analysis",
            "id": "55555555-5555-4555-8555-555555555555",
            "revision": 1,
        }
        infeasible = artifact_role == "infeasibility_evidence"
        manifest = {
            "schema_version": 2,
            "operation_id": "66666666-6666-4666-8666-666666666666",
            "route": "analysis_execution",
            "scope_ref": reference,
            "files": [evidence_path],
            "completed_at": "2026-01-01T00:00:00Z",
            "summary": "Analysis execution evidence.",
            "artifact_role": artifact_role,
            "execution_receipt": {
                "contract_hash": "0" * 64,
                "completed_requirements": [] if infeasible else [requirement],
                "unmet_requirements": [requirement] if infeasible else [],
                "supplemental_work": [],
                "evidence_files": [evidence_path],
            },
        }
        (artifact / "artifact-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        self.write_artifact_state(workdir, manifest, "output/analysis")
        return reference

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
            self.assertFalse(second["intact_routes"]["data_audit"])
            self.assertTrue(second["intact_routes"]["analysis_execution"])
            third = RUNNER.inspect_artifacts(
                workdir, {"total": 1, "new": 0}, second
            )
            self.assertFalse(third["intact_routes"]["data_audit"])

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
            self.assertFalse(second["intact_routes"]["data_audit"])

    def test_artifact_snapshot_tracks_changed_scope_identity(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_report_artifact(workdir, html_content="<p>Original</p>")
            first = RUNNER.inspect_artifacts(
                workdir, {"report_writer": 1, "new": 1}
            )
            report = workdir / "output" / "report" / "index.html"
            report.write_text("<p>Changed</p>", encoding="utf-8")
            second = RUNNER.inspect_artifacts(
                workdir, {"report_writer": 1, "new": 0}, first
            )
            reference = ("44444444-4444-4444-8444-444444444444", 1)
            self.assertIn(reference, second["changed_scope_refs"]["report_writer"])
            third = RUNNER.inspect_artifacts(
                workdir, {"report_writer": 1, "new": 0}, second
            )
            self.assertIn(reference, third["changed_scope_refs"]["report_writer"])

    def test_unknown_artifact_change_does_not_contaminate_known_routes(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            output = workdir / "output"
            output.mkdir()
            manifest = output / "unknown.manifest.json"
            manifest.write_text("{invalid", encoding="utf-8")
            first = RUNNER.inspect_artifacts(workdir, {})
            manifest.write_text("{still-invalid", encoding="utf-8")
            second = RUNNER.inspect_artifacts(workdir, {}, first)
            self.assertTrue(second["intact_routes"]["analysis_execution"])
            self.assertEqual(second["changed_scope_refs"]["analysis_execution"], [])

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

    def test_observational_audit_turn_rejects_unexpected_artifacts(self):
        expected = RUNNER.load_cases()["college-observational-policy"]["turns"][2]["artifacts"]
        for route in ("data_audit", "causal_discovery"):
            with self.subTest(route=route), TemporaryDirectory() as temporary:
                workdir = Path(temporary)
                self.write_data_audit_artifact(workdir, route=route)
                result = RUNNER.inspect_artifacts(workdir, expected)
                self.assertFalse(result["ok"])
                self.assertIn(
                    "expected 0 new artifact(s), found 1",
                    result["errors"],
                )
                if route == "causal_discovery":
                    self.assertIn(
                        "expected 0 causal_discovery artifact(s), found 1",
                        result["errors"],
                    )
    def test_discovery_manifest_is_scope_bound_and_usable(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            artifact = workdir / "output" / "discovery"
            artifact.mkdir(parents=True)
            deliverable = artifact / "candidate-graph.csv"
            deliverable.write_text("from,to\nExpend,Grad.Rate\n", encoding="utf-8")
            reference = {
                "kind": "discovery",
                "id": "55555555-5555-4555-8555-555555555555",
                "revision": 1,
            }
            manifest = {
                "schema_version": 1,
                "operation_id": "66666666-6666-4666-8666-666666666666",
                "route": "causal_discovery",
                "scope_ref": reference,
                "discovery_contract": self.discovery_contract(),
                "files": ["output/discovery/candidate-graph.csv"],
                "completed_at": "2026-01-01T00:00:00Z",
                "summary": "Bound discovery output.",
            }
            (artifact / "artifact-manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            self.write_artifact_state(workdir, manifest, "output/discovery")

            result = RUNNER.inspect_artifacts(
                workdir, {"causal_discovery": 1, "new": 1}
            )
            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(
                result["usable_scope_refs"]["causal_discovery"],
                [(reference["id"], reference["revision"])],
            )
            self.assertEqual(
                result["manifests"][0]["discovery_contract"],
                self.discovery_contract(),
            )

    def test_schema2_roles_separate_completion_from_infeasibility(self):
        for artifact_role in ("completion", "infeasibility_evidence"):
            with self.subTest(artifact_role=artifact_role), TemporaryDirectory() as temporary:
                workdir = Path(temporary)
                reference = self.write_schema2_analysis_artifact(
                    workdir, artifact_role
                )
                result = RUNNER.inspect_artifacts(
                    workdir, {"analysis_execution": 1, "new": 1}
                )
                self.assertTrue(result["ok"], result["errors"])
                self.assertEqual(result["manifest_counts"]["analysis_execution"], 1)
                self.assertEqual(
                    result["role_counts"][artifact_role]["analysis_execution"],
                    1,
                )
                identity = [(reference["id"], reference["revision"])]
                if artifact_role == "completion":
                    self.assertEqual(
                        result["usable_scope_refs"]["analysis_execution"],
                        identity,
                    )
                    self.assertNotIn(
                        "analysis_execution", result["infeasibility_scope_refs"]
                    )
                else:
                    self.assertEqual(result["counts"].get("analysis_execution", 0), 0)
                    self.assertEqual(
                        result["infeasibility_scope_refs"]["analysis_execution"],
                        identity,
                    )
                    self.assertNotIn(
                        "analysis_execution", result["usable_scope_refs"]
                    )

    def test_execution_receipt_enforces_role_semantics(self):
        receipt = {
            "contract_hash": "0" * 64,
            "completed_requirements": ["fit approved estimator"],
            "unmet_requirements": ["fit approved estimator"],
            "supplemental_work": [],
            "evidence_files": ["output/analysis/evidence.txt"],
        }
        completion_errors = RUNNER.validate_execution_receipt(
            receipt, "completion", ["output/analysis/evidence.txt"], "manifest"
        )
        self.assertTrue(any("must not overlap" in error for error in completion_errors))
        self.assertTrue(any("requires no unmet" in error for error in completion_errors))
        receipt["completed_requirements"] = []
        receipt["unmet_requirements"] = []
        infeasibility_errors = RUNNER.validate_execution_receipt(
            receipt,
            "infeasibility_evidence",
            ["output/analysis/evidence.txt"],
            "manifest",
        )
        self.assertTrue(
            any("requires at least one unmet" in error for error in infeasibility_errors)
        )

    def test_artifact_manifest_schema_is_strict(self):
        cases = (
            ("schema", lambda manifest: manifest.update(schema_version=3), "schema_version"),
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

    def test_unlisted_output_fails_without_invalidating_registered_evidence(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_data_audit_artifact(workdir)
            extra = workdir / "output" / "unlisted.txt"
            extra.write_text("extra\n", encoding="utf-8")
            result = RUNNER.inspect_artifacts(workdir, {"total": 1, "new": 1})
            self.assertFalse(result["ok"])
            self.assertEqual(result["orphaned_files"], ["output/unlisted.txt"])
            self.assertTrue(result["scope_refs_trustworthy"])
            self.assertEqual(result["integrity_errors"], [])
            self.assertTrue(
                any("unlisted output files" in error for error in result["expectation_errors"])
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
            self.assertNotIn("report_writer", result["usable_scope_refs"])

    def test_usable_report_artifact_keeps_its_scope_identity(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_report_artifact(workdir, html_content="<p>Report</p>")
            result = RUNNER.inspect_artifacts(
                workdir, {"report_writer": 1, "new": 1}
            )
            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(
                result["usable_scope_refs"]["report_writer"],
                [("44444444-4444-4444-8444-444444444444", 1)],
            )

    def test_invalid_report_manifest_is_not_usable_evidence(self):
        with TemporaryDirectory() as temporary:
            workdir = Path(temporary)
            self.write_report_artifact(workdir, html_content="<p>Report</p>")
            manifest_path = workdir / "output" / "report" / "artifact-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["completed_at"] = "12:00:00"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = RUNNER.inspect_artifacts(
                workdir, {"report_writer": 1, "new": 1}
            )
            self.assertFalse(result["ok"])
            self.assertNotIn("report_writer", result["usable_scope_refs"])

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
                    "valid": True,
                    "artifact_role": "completion",
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
        self.assertTrue(any("does not match its completion status" in error for error in errors))

    def test_discovery_manifest_binds_scoped_contract(self):
        sequence = self.discovery_scope_sequence()
        contract = self.discovery_contract()
        artifacts = {
            "new_manifests": [
                {
                    "path": "output/discovery/artifact-manifest.json",
                    "route": "causal_discovery",
                    "valid": True,
                    "artifact_role": "completion",
                    "scope_ref": {
                        "kind": "discovery",
                        "id": "55555555-5555-4555-8555-555555555555",
                        "revision": 1,
                    },
                    "discovery_contract": contract,
                }
            ]
        }
        self.assertEqual(
            RUNNER.check_new_manifest_scope_bindings(
                sequence[4], sequence[3], artifacts
            ),
            [],
        )
        artifacts["new_manifests"][0]["discovery_contract"] = {
            **contract,
            "method_plan": "different discovery family",
        }
        errors = RUNNER.check_new_manifest_scope_bindings(
            sequence[4], sequence[3], artifacts
        )
        self.assertTrue(any("prior scope" in error for error in errors))
        self.assertTrue(any("completion handoff" in error for error in errors))

    def test_discovery_manifest_binding_accepts_legal_direct_transitions(self):
        sequence = self.discovery_scope_sequence()
        prior = sequence[4]
        reference = {
            "kind": "discovery",
            "id": prior["discovery"]["scope_id"],
            "revision": 1,
        }
        manifest = {
            "path": "output/discovery/artifact-manifest.json",
            "route": "causal_discovery",
            "valid": True,
            "artifact_role": "completion",
            "scope_ref": reference,
            "discovery_contract": self.discovery_contract(),
        }
        self.assertEqual(
            RUNNER.check_new_manifest_scope_bindings(
                sequence[4], None, {"new_manifests": [manifest]}
            ),
            [],
        )
        invalid_direct = deepcopy(sequence[4])
        invalid_direct["discovery"]["scope_revision"] = 2
        invalid_manifest = deepcopy(manifest)
        invalid_manifest["scope_ref"]["revision"] = 2
        self.assertTrue(
            any(
                "prior scope" in error
                for error in RUNNER.check_new_manifest_scope_bindings(
                    invalid_direct,
                    None,
                    {"new_manifests": [invalid_manifest]},
                )
            )
        )
        self.assertEqual(
            RUNNER.check_new_manifest_scope_bindings(
                sequence[4], prior, {"new_manifests": [manifest]}
            ),
            [],
        )

        revised = deepcopy(sequence[4])
        revised["discovery"]["scope_revision"] = 2
        revised["discovery"]["execution_contract"]["method_plan"] = (
            "revised discovery method"
        )
        revised_manifest = deepcopy(manifest)
        revised_manifest["scope_ref"]["revision"] = 2
        revised_manifest["discovery_contract"] = deepcopy(
            revised["discovery"]["execution_contract"]
        )
        self.assertEqual(
            RUNNER.check_new_manifest_scope_bindings(
                revised, prior, {"new_manifests": [revised_manifest]}
            ),
            [],
        )

        replacement = deepcopy(sequence[4])
        replacement["discovery"]["scope_id"] = (
            "77777777-7777-4777-8777-777777777777"
        )
        replacement_manifest = deepcopy(manifest)
        replacement_manifest["scope_ref"]["id"] = replacement["discovery"]["scope_id"]
        self.assertEqual(
            RUNNER.check_new_manifest_scope_bindings(
                replacement, prior, {"new_manifests": [replacement_manifest]}
            ),
            [],
        )

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
                    "valid": True,
                    "artifact_role": "completion",
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
            with self.assertRaisesRegex(RUNNER.RunError, "registered case dataset"):
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
        turn_artifacts = summary["turns"][0]["artifacts"]
        self.assertEqual(turn_artifacts["manifest_counts"], {})
        self.assertEqual(turn_artifacts["counts"], {})
        self.assertEqual(
            turn_artifacts["role_counts"], {"completion": {}, "infeasibility_evidence": {}}
        )
        self.assertEqual(summary["automated_checks"]["status"], "pass")
        self.assertEqual(summary["workflow_assessment"]["status"], "not_required")
        self.assertEqual(summary["final_result"]["status"], "pass")

    def test_diagnostic_only_summary_remains_passing(self):
        record = self.passing_record()
        record["state"]["diagnostics"] = [
            "delivered response differs from response_receipt.response_markdown"
        ]
        summary = RUNNER.build_summary(
            "smoke", 1, [record], None, self.summary_target()
        )
        markdown = RUNNER.render_summary_markdown(summary)
        self.assertEqual(summary["validated_turns"], 1)
        self.assertEqual(
            summary["automated_checks"]["categories"]["state_protocol"], "pass"
        )
        self.assertEqual(summary["final_result"]["status"], "pass")
        self.assertIn("## Diagnostics", markdown)
        self.assertNotIn("## Failures", markdown)

    def test_all_live_cases_require_manual_assessment(self):
        for test_id in RUNNER.TEST_IDS:
            with self.subTest(test_id=test_id):
                summary = RUNNER.build_summary(
                    test_id,
                    1,
                    [self.passing_record()],
                    None,
                    self.summary_target(),
                )
                self.assertEqual(summary["automated_checks"]["status"], "pass")
                self.assertEqual(summary["workflow_assessment"]["status"], "pending")
                self.assertEqual(summary["final_result"]["status"], "pending")

    def test_assessment_finalizes_live_summary(self):
        summary = RUNNER.build_summary(
            "college-observational-policy",
            1,
            [self.passing_record()],
            None,
            self.summary_target(),
        )
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            self.write_assessable_summary(results_dir, summary)
            notes = results_dir / "workflow-assessment.md"
            notes.write_text(
                "All material workflow boundaries were preserved.\n",
                encoding="utf-8",
            )
            notes_sha256 = hashlib.sha256(notes.read_bytes()).hexdigest()
            final = RUNNER.assess_results(results_dir, "pass", notes)
            recorded = json.loads(
                (results_dir / "summary.json").read_text(encoding="utf-8")
            )
            markdown = (results_dir / "summary.md").read_text(encoding="utf-8")
        self.assertEqual(final, "pass")
        self.assertEqual(recorded["workflow_assessment"]["status"], "complete")
        self.assertEqual(recorded["workflow_assessment"]["rating"], "pass")
        self.assertEqual(
            recorded["workflow_assessment"]["notes_sha256"],
            notes_sha256,
        )
        self.assertEqual(recorded["final_result"]["status"], "pass")
        self.assertIn("Final result: **PASS**", markdown)

    def test_assessment_rejects_invalid_rating(self):
        summary = RUNNER.build_summary(
            "college-observational-policy",
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
            with self.assertRaisesRegex(RUNNER.RunError, "invalid college-observational-policy rating"):
                RUNNER.assess_results(results_dir, "safe", notes)

    def test_completed_automated_failure_can_be_assessed_but_cannot_pass(self):
        failed = self.passing_record()
        failed["shell"] = {"ok": False, "errors": ["missing heading"]}
        summary = RUNNER.build_summary(
            "standard", 1, [failed], None, self.summary_target()
        )
        self.assertEqual(summary["automated_checks"]["status"], "fail")
        self.assertEqual(summary["workflow_assessment"]["status"], "pending")
        self.assertEqual(RUNNER.run_completion_status(summary), "complete")
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            self.write_assessable_summary(results_dir, summary)
            notes = results_dir / "workflow-assessment.md"
            notes.write_text("The workflow itself remained usable.\n", encoding="utf-8")
            final = RUNNER.assess_results(results_dir, "pass", notes)
            recorded = json.loads(
                (results_dir / "summary.json").read_text(encoding="utf-8")
            )
        self.assertEqual(final, "fail")
        self.assertEqual(recorded["workflow_assessment"]["status"], "complete")
        self.assertEqual(recorded["workflow_assessment"]["rating"], "pass")
        self.assertEqual(recorded["final_result"]["status"], "fail")
        self.assertEqual(RUNNER.final_result_exit_code(final), 1)

    def test_assessment_is_blocked_after_aborted_run(self):
        summary = RUNNER.build_summary(
            "standard",
            2,
            [self.passing_record()],
            "turn 1 cannot continue",
            self.summary_target(),
        )
        self.assertEqual(summary["workflow_assessment"]["status"], "blocked")
        self.assertEqual(RUNNER.run_completion_status(summary), "aborted")
        with TemporaryDirectory() as temporary:
            results_dir = Path(temporary).resolve()
            RUNNER.write_summary_files(results_dir, summary)
            notes = results_dir / "workflow-assessment.md"
            notes.write_text("Review cannot proceed.\n", encoding="utf-8")
            with self.assertRaisesRegex(RUNNER.RunError, "run did not complete"):
                RUNNER.assess_results(results_dir, "fail", notes)

    def test_run_completion_distinguishes_incomplete_without_abort(self):
        summary = RUNNER.build_summary(
            "smoke",
            2,
            [self.passing_record()],
            None,
            self.summary_target(),
        )
        self.assertEqual(RUNNER.run_completion_status(summary), "incomplete")
        self.assertIn(
            "Run completion: **INCOMPLETE**",
            RUNNER.render_summary_markdown(summary),
        )

    def test_live_loop_continues_and_records_a_final_boundary_failure(self):
        first = (
            f"{RUNNER.WELCOME_LINE}\n\n"
            "[> Framing]\nFirst.\n\n"
            "[! Boundary]\nBoundary.\n\n"
            "[? Next Steps]\nContinue."
        )
        second = (
            "[> Framing]\nSecond.\n\n"
            "[! Boundary]\nBoundary.\n\n"
            "[? Next Steps]\nDone."
        )
        responses = iter((first, second))
        validators = [
            {
                "project_id": "project-1",
                "revision": 3,
                "scope_snapshot": {"analysis": {}, "report": None},
                "response_receipt": {"response_markdown": "Different response"},
                "pending_decision": None,
            },
            {
                "project_id": "project-1",
                "revision": 6,
                "scope_snapshot": {"analysis": {}, "report": None},
                "response_receipt": {"response_markdown": second},
                "pending_decision": None,
            },
        ]
        artifact_result = {
            "ok": True,
            "expected": {"total": 0, "new": 0},
            "manifest_count": 0,
            "new_count": 0,
            "counts": {},
            "manifests": [],
            "new_manifests": [],
            "manifest_paths": [],
            "hashes": {},
            "orphaned_files": [],
            "errors": [],
        }

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            workdir = root / "work"
            results_dir = root / "results"
            workdir.mkdir()
            results_dir.mkdir()
            args = SimpleNamespace(
                test="college-observational-policy",
                workdir=workdir,
                results_dir=results_dir,
                statectl=root / "statectl.cjs",
                node="node",
                claude_bin="claude",
                max_turns=30,
                timeout=60,
            )
            case = {
                "turns": [
                    {"label": "First", "prompt": "First prompt.", "artifacts": {"total": 0, "new": 0}},
                    {"label": "Second", "prompt": "Second prompt.", "artifacts": {"total": 0, "new": 0}},
                ]
            }
            target = self.summary_target()

            def send_response(command, **_kwargs):
                response_text = next(responses)
                output = Path(command[command.index("--out-file") + 1])
                output.write_text(
                    json.dumps(
                        {
                            "result": response_text,
                            "session_id": "session-1",
                            "is_error": False,
                        }
                    ),
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with ExitStack() as stack:
                stack.enter_context(patch.object(RUNNER, "preflight", return_value=target))
                stack.enter_context(patch.object(RUNNER, "validate_runtime_provenance"))
                stack.enter_context(
                    patch.object(RUNNER.subprocess, "run", side_effect=send_response)
                )
                validate_state = stack.enter_context(
                    patch.object(
                        RUNNER,
                        "validate_state",
                        side_effect=[
                            (validators[0], [], []),
                            (
                                validators[1],
                                ["active_operation is not null"],
                                ["active_operation is not null"],
                            ),
                        ],
                    )
                )
                inspect_artifacts = stack.enter_context(
                    patch.object(
                        RUNNER,
                        "inspect_artifacts",
                        side_effect=[deepcopy(artifact_result), deepcopy(artifact_result)],
                    )
                )
                exit_code = RUNNER.run_test(args, case)

            summary = json.loads(
                (results_dir / "summary.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(summary["attempted_turns"], 2)
        self.assertIsNone(summary["abort_reason"])
        self.assertEqual(
            summary["automated_checks"]["categories"]["run_integrity"],
            "pass",
        )
        self.assertEqual(
            summary["automated_checks"]["categories"]["state_protocol"],
            "fail",
        )
        self.assertEqual(validate_state.call_args_list[1].args[3:5], ("project-1", 3))
        self.assertEqual(
            summary["turns"][0]["state_protocol"]["diagnostics"],
            ["delivered response differs from response_receipt.response_markdown"],
        )
        self.assertIn(
            "## Diagnostics",
            RUNNER.render_summary_markdown(summary),
        )
        self.assertIsNotNone(inspect_artifacts.call_args_list[1].args[2])

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

    def test_live_weak_and_fail_ratings_remain_nonpassing(self):
        for rating in ("weak", "fail"):
            with self.subTest(rating=rating), TemporaryDirectory() as temporary:
                summary = RUNNER.build_summary(
                    "college-observational-policy",
                    1,
                    [self.passing_record()],
                    None,
                    self.summary_target(),
                )
                results_dir = Path(temporary).resolve()
                self.write_assessable_summary(results_dir, summary)
                notes = results_dir / "workflow-assessment.md"
                notes.write_text("Review found a material issue.\n", encoding="utf-8")
                final = RUNNER.assess_results(results_dir, rating, notes)
                self.assertEqual(final, rating)

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
