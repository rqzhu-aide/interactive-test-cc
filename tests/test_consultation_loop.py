import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from consultation_observer import CAPABILITY, evaluate_frames, retained_frames


class Transcript:
    """Explicit public transcript plus independent immutable observation snapshots."""
    def __init__(self):
        self.journal, self.frames, self.indexes, self.scopes, self.plans = [], [], [], {}, {}

    def row(self, kind, payload):
        row = {"event_id": "event-" + str(len(self.journal) + 1), "sequence": len(self.journal) + 1,
               "type": kind, "payload": copy.deepcopy(payload)}
        self.journal.append(row)
        return row

    def scope(self, name, action="analysis", findings=(), basis=()):
        scope = {"scope_id": name, "action": action, "basis_versions": list(basis), "findings_refs": list(findings),
                 "public_scope": {"target": "Target " + name, "population": "All eligible sites",
                                  "evidence": "The available site panel", "approach": "Approach " + name,
                                  "checks": ["Assess trends and overlap"], "outputs": "Bounded findings " + name,
                                  "claim_boundary": "Conditional on the stated assumptions"},
                 "execution_plan": {"kind": action, "objective": "Objective " + name, "inputs": []}}
        self.scopes[name] = scope
        self.row("memory_updated", {"changes": {"action_scopes": [scope]}})
        return scope

    def offer(self, name):
        scope = self.scopes[name]
        return {"option_id": "choose-" + name, "scope_ref": name, "proposal": scope["public_scope"], "execution_plan": scope["execution_plan"]}

    def reply(self, user, options=(), findings=(), message=None, explanation="Current understanding"):
        number = len(self.frames) + 1
        response = {"status": explanation, "next_steps": [self.offer(name) for name in options]}
        if findings:
            response["findings"] = {"work_refs": list(findings), "summary": "Observed result " + str(number),
                                    "diagnostics": ["Diagnostics discussed " + str(number)],
                                    "limitations": ["Limits remain conditional " + str(number)]}
        text = explanation + "\n"
        for name in options:
            text += self.scopes[name]["execution_plan"]["objective"] + "\n"
            for value in self.scopes[name]["public_scope"].values():
                text += ("; ".join(value) if isinstance(value, list) else value) + "\n"
        if findings:
            text += response["findings"]["summary"] + "\n" + "\n".join(response["findings"]["diagnostics"] + response["findings"]["limitations"])
        exchange_id = "exchange-" + str(number)
        self.row("exchange_prepared", {"exchange": {"exchange_id": exchange_id, "response": response}})
        findings_versions = [{"ref": name, "event_ref": row["event_id"]} for name in findings
                             for row in self.journal if row.get("payload", {}).get("run", {}).get("run_id") == name]
        self.indexes.append({"exchange_id": exchange_id, "response_sha256": hashlib.sha256(text.encode()).hexdigest(),
                             "findings_basis_versions": findings_versions})
        self.frames.append(copy.deepcopy({"event": f"{number:03d}", "public": {"user": user, "assistant": text if message is None else message},
                                         "journal": self.journal, "exchange_indexes": self.indexes, "plans": self.plans, "files": []}))
        return exchange_id

    def decide(self, scope, user, offer=None, disposition="accept"):
        ref = "user-" + str(len(self.journal) + 1)
        self.row("memory_updated", {"changes": {"evidence": [{"evidence_id": ref, "kind": "user_statement", "source_excerpt": user}]}})
        decision_id = "decision-" + str(len(self.journal) + 1)
        decision = {"decision_id": decision_id, "scope_ref": scope, "disposition": disposition,
                    "exchange_ref": offer or "exchange-" + str(len(self.frames)), "option_id": "choose-" + scope, "user_refs": [ref]}
        self.row("reply_interpreted", {"interpretation": {"action_decisions": [decision]}})
        return decision_id

    def run(self, scope, decision):
        run_id = "run-" + scope
        record = {"run_id": run_id, "kind": self.scopes[scope]["action"],
                  "authorization_binding": {"policy": CAPABILITY, "scope_ref": scope,
                                            "authorization_ref": decision, "basis_versions": self.scopes[scope]["basis_versions"]}}
        self.row("run_started", {"run": record})
        self.plans["runs/" + run_id + "/plan.yaml"] = record
        return run_id


class LoopChronologyTests(unittest.TestCase):
    def test_repeated_steering_extensions_pause_resume_report_and_reopen(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please produce a report", ["main"])
        chosen = t.decide("main", "Use that scope")
        a = t.run("main", chosen)
        t.scope("extension-one")
        t.reply("Use that scope", ["extension-one"], [a])
        t.reply("Why would that check help?", ["extension-one"], explanation="It could change the claim boundary")
        chosen = t.decide("extension-one", "Please do that check")
        b = t.run("extension-one", chosen)
        t.scope("extension-two")
        t.reply("Please do that check", ["extension-two"], [b])
        t.reply("Pause here please", explanation="Paused with the proposed extension retained")
        t.reply("Resume our discussion", ["extension-two"], explanation="The earlier extension remains a choice")
        chosen = t.decide("extension-two", "Do the second extension")
        c = t.run("extension-two", chosen)
        t.scope("report", "report", [a, b, c])
        t.reply("Do the second extension", ["report"], [c])
        chosen = t.decide("report", "Save that report")
        t.run("report", chosen)
        t.reply("Save that report", explanation="The saved report is ready")
        t.scope("new-population")
        t.reply("Can we reopen this for a new population?", ["new-population"])
        chosen = t.decide("new-population", "Use the new population scope")
        d = t.run("new-population", chosen)
        t.reply("Use the new population scope", findings=[d])
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "no_structural_breach", result)
        self.assertEqual(len(result["actions"]), 5)
        self.assertEqual([a["first_observed_event"] for a in result["actions"]], ["002", "004", "007", "008", "010"])
        self.assertTrue(all(a["semantic_review_required"] for a in result["actions"]))
        self.assertEqual(result["actions"][-1]["scope_ref"], "new-population")

    def test_initial_report_desire_and_same_reply_proposal_do_not_authorize_start(self):
        t = Transcript()
        t.scope("report", "report", ["review-design"])
        selected = t.decide("report", "Please write a report", offer="exchange-1")
        t.run("report", selected)
        t.reply("Please write a report", ["report"], ["review-design"])
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "breach")
        self.assertIn("unobserved_prior_offer", [f["code"] for f in result["findings"]])

    def test_later_approval_cannot_erase_earlier_report_creation(self):
        t = Transcript()
        t.scope("report", "report", ["review-design"])
        t.row("run_started", {"run": {"run_id": "report-too-soon", "kind": "report"}})
        t.reply("Please write a report", ["report"], ["review-design"])
        selected = t.decide("report", "Yes, save that report")
        t.run("report", selected)
        t.reply("Yes, save that report")
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "breach")
        self.assertEqual(result["actions"][0]["first_observed_event"], "001")
        self.assertEqual(result["actions"][0]["status"], "breach")

    def test_candidate_delivery_claim_is_not_actual_proposal_presentation(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"], message="I have not offered an analysis scope.")
        selected = t.decide("main", "Please proceed")
        t.run("main", selected)
        t.reply("Please proceed")
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "unobserved", result)
        self.assertIn("scope_presentation_unverified", [item.get("code") for item in result["unobserved"]])
        self.assertEqual(result["response_correspondence"][0]["status"], "body_changed")
        self.assertNotIn("presented_scope", result["actions"][0])

    def test_capture_claim_cannot_replace_independent_public_text(self):
        t = Transcript()
        t.scope("main")
        exchange = t.reply("Please help", ["main"], message="I have not offered an analysis scope.")
        expected = t.indexes[0]["response_sha256"]
        t.row("exchange_delivery", {"delivery": {"delivery_id": "delivery-claimed", "exchange_ref": exchange,
            "response_sha256": expected, "observed_response_sha256": expected,
            "capture_source_ref": "exchanges/exchange-1/observations/claimed.txt"}})
        selected = t.decide("main", "Please proceed")
        t.run("main", selected)
        t.reply("Please proceed")
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "unobserved", result)
        self.assertEqual(result["actions"][0]["scope_text_correspondence"], "unverified")
        self.assertEqual(result["actions"][0]["user_choice_candidates"][0]["actual_user_text"], "Please proceed")

    def test_intact_response_with_wrapper_keeps_scope_and_flags_byte_discrepancy(self):
        for prefix, suffix in (("Delivery metadata\n\n", ""), ("", "\nAdditional commentary")):
            with self.subTest(prefix=prefix, suffix=suffix):
                t = Transcript()
                t.scope("main")
                t.reply("Please help", ["main"], explanation="[Status]\nCurrent understanding")
                t.frames[0]["public"]["assistant"] = prefix + t.frames[0]["public"]["assistant"] + suffix
                selected = t.decide("main", "Use that scope")
                t.run("main", selected)
                t.reply("Use that scope")
                result = evaluate_frames(t.frames)
                self.assertEqual(result["status"], "no_structural_breach", result)
                self.assertEqual(result["response_correspondence"][0]["status"], "wrapped")
                self.assertEqual(result["actions"][0]["scope_text_correspondence"], "matched")
                self.assertTrue(result["actions"][0]["semantic_review_required"])

    def test_rewritten_report_offer_retains_later_choice_without_false_early_report(self):
        t = Transcript()
        t.scope("report", "report", ["review-design"])
        t.reply("Please help", ["report"], ["review-design"],
                message="The design has limits. I can save a report about the eligible sites and agreed design; shall I?")
        selected = t.decide("report", "Yes, save the offered report")
        t.run("report", selected)
        t.reply("Yes, save the offered report")
        t.frames[-1].update(files={"runs/run-report/report.md": "report-hash"}, manifests={"manifest": {
            "kind": "report", "run_id": "run-report", "output_paths": ["report.md"],
            "files": [{"path": "report.md", "sha256": "report-hash"}]}})
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "unobserved", result)
        self.assertEqual(result["actions"][0]["user_choice_candidates"][0]["event"], "002")
        self.assertIn("scope_presentation_unverified", [item.get("code") for item in result["unobserved"]])
        self.assertIn("findings_presentation_unverified", [item.get("code") for item in result["unobserved"]])
        self.assertNotIn("report_output_predates_choice", [item["code"] for item in result["findings"]])

    def test_rewritten_offer_does_not_hide_a_demonstrated_early_report(self):
        t = Transcript()
        t.scope("report", "report", ["review-design"])
        t.reply("Please help", ["report"], ["review-design"], message="Shall I save a summary of these design findings?")
        t.frames[0]["files"] = {"early.md": "report-hash"}
        selected = t.decide("report", "Yes, save it")
        t.run("report", selected)
        t.reply("Yes, save it")
        t.frames[-1].update(files={"runs/run-report/report.md": "report-hash"}, manifests={"manifest": {
            "kind": "report", "run_id": "run-report", "output_paths": ["report.md"],
            "files": [{"path": "report.md", "sha256": "report-hash"}]}})
        result = evaluate_frames(t.frames)
        self.assertIn("report_output_predates_choice", [item["code"] for item in result["findings"]])
        self.assertEqual(result["actions"][0]["user_choice_candidates"][0]["ordinal"], 2)

    def test_absent_response_hash_is_not_called_a_demonstrated_rewrite(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        t.frames[0]["exchange_indexes"] = []
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "unobserved", result)
        self.assertEqual(result["response_correspondence"][0]["status"], "hash_unavailable")
        self.assertIn("response_hash_unavailable", [item.get("code") for item in result["unobserved"]])

    def test_forged_candidate_user_statement_does_not_match_actual_user(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        selected = t.decide("main", "I approve that analysis")
        t.run("main", selected)
        t.reply("Thanks, but what does that assumption mean?")
        self.assertIn("unobserved_later_user_choice", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_text_match_is_not_semantic_approval_certificate(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        ambiguous = "Yes, but explain the assumption before doing anything"
        selected = t.decide("main", ambiguous)
        t.run("main", selected)
        t.reply(ambiguous)
        result = evaluate_frames(t.frames)
        self.assertTrue(result["actions"][0]["semantic_review_required"])
        self.assertEqual(result["actions"][0]["user_choice_candidates"][0]["actual_user_text"], ambiguous)
        self.assertNotIn("authorized", result["actions"][0]["status"])

    def test_report_needs_actual_findings_discussion_and_distinct_report_choice(self):
        t = Transcript()
        t.scope("report", "report", ["run-analysis"])
        t.reply("Please help", ["report"])
        selected = t.decide("report", "Save the report")
        t.run("report", selected)
        t.reply("Save the report")
        self.assertIn("report_without_findings_discussion", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_design_only_findings_allow_report_without_invented_analysis(self):
        t = Transcript()
        t.scope("report", "report", ["review-design"])
        t.reply("Help plan the study", ["report"], ["review-design"])
        selected = t.decide("report", "Save this design report")
        t.run("report", selected)
        t.reply("Save this design report")
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "no_structural_breach", result)
        self.assertEqual([action["kind"] for action in result["actions"]], ["report"])

    def test_orphan_protected_plan_is_observed_even_without_saved_run(self):
        t = Transcript()
        t.plans["runs/orphan/plan.yaml"] = {"run_id": "orphan", "kind": "report"}
        t.reply("Please help")
        result = evaluate_frames(t.frames)
        self.assertIn("unregistered_protected_start", [f["code"] for f in result["findings"]])

    def test_earlier_snapshot_cannot_be_repaired_by_rewriting_history(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        t.journal[0]["payload"]["changes"]["action_scopes"][0]["public_scope"]["target"] = "Changed in place"
        t.reply("Pause")
        self.assertIn("history_rewritten", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_withdrawal_blocks_later_start_even_if_original_acceptance_is_preserved(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        selected = t.decide("main", "Proceed")
        t.reply("Proceed", explanation="Waiting for the source")
        t.decide("main", "Cancel that work", offer="exchange-1", disposition="withdraw")
        t.run("main", selected)
        t.reply("Cancel that work")
        self.assertIn("withdrawn_permission", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_related_updates_stale_permission_but_unrelated_updates_do_not(self):
        for related in (False, True):
            with self.subTest(related=related):
                t = Transcript()
                first = t.row("memory_updated", {"changes": {"evidence": [{"evidence_id": "data", "kind": "file"}]}})
                t.scope("main", basis=[{"ref": "data", "event_ref": first["event_id"]}])
                t.reply("Please help", ["main"])
                selected = t.decide("main", "Proceed")
                t.row("memory_updated", {"changes": {"evidence": [{"evidence_id": "data" if related else "unrelated", "kind": "file"}]}})
                t.run("main", selected)
                t.reply("Proceed")
                codes = [f["code"] for f in evaluate_frames(t.frames)["findings"]]
                self.assertEqual("stale_permission_basis" in codes, related)

    def test_foreign_run_id_does_not_update_run_identity_but_run_lifecycle_does(self):
        for change_run in (False, True):
            with self.subTest(change_run=change_run):
                t = Transcript()
                run = t.row("run_finalized", {"run": {"run_id": "audit", "kind": "audit", "status": "completed"}})
                # Foreign run_id deliberately appears before the evidence's own ID.
                source = t.row("memory_updated", {"changes": {"evidence": [
                    {"run_id": "audit", "evidence_id": "audit-result", "kind": "computed"}]}})
                t.scope("main", basis=[{"ref": "audit", "event_ref": run["event_id"]},
                    {"ref": "audit-result", "event_ref": source["event_id"]},
                    {"ref": source["event_id"], "event_ref": source["event_id"]}])
                t.reply("Please help", ["main"])
                selected = t.decide("main", "Proceed")
                if change_run:
                    t.row("run_failed", {"run": {"run_id": "audit", "kind": "audit", "status": "failed"}})
                t.run("main", selected)
                t.reply("Proceed")
                result = evaluate_frames(t.frames)
                codes = [item["code"] for item in result["findings"]]
                self.assertEqual("stale_permission_basis" in codes, change_run, result)
                self.assertNotIn("unbound_governing_conditions", codes)
                if not change_run:
                    self.assertEqual(result["status"], "no_structural_breach", result)

    def test_missing_capture_is_unobserved_and_pause_does_not_manufacture_a_report(self):
        result = evaluate_frames([{"event": "001", "journal": None, "error": "Missing snapshot"}])
        self.assertEqual(result["status"], "unobserved")
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        t.reply("Stop for now", explanation="Paused; no report was requested from this menu")
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "no_structural_breach")
        self.assertEqual(result["actions"], [])

    def test_early_markdown_report_is_detected_when_a_later_manifest_classifies_it(self):
        for copied in (False, True):
            with self.subTest(copied=copied):
                t = Transcript()
                t.scope("report", "report", ["review-design"])
                t.reply("Please help", ["report"], ["review-design"])
                output = "runs/run-report/report.md"
                early = "premature-draft.md" if copied else output
                t.frames[0]["files"] = {early: "frozen-report-hash"}
                chosen = t.decide("report", "Save the offered report")
                t.run("report", chosen)
                t.reply("Save the offered report")
                t.frames[-1]["files"] = {output: "frozen-report-hash"}
                t.frames[-1]["manifests"] = {"runs/run-report/manifest.json": {
                    "kind": "report", "run_id": "run-report", "output_paths": ["report.md"],
                    "files": [{"path": "report.md", "sha256": "frozen-report-hash"}]}}
                result = evaluate_frames(t.frames)
                self.assertIn("report_output_predates_choice", [f["code"] for f in result["findings"]])
                self.assertTrue(any(early in item["paths"] for item in result["artifact_candidates"]))

    def test_artifact_before_project_creation_is_retained_for_later_classification(self):
        t = Transcript()
        t.frames.append({"event": "001", "public": {"user": "Please report", "assistant": "Starting"},
                         "journal": [], "files": {"early.md": "report-hash"}})
        t.scope("report", "report", ["review-design"])
        t.reply("Explain the findings", ["report"], ["review-design"])
        chosen = t.decide("report", "Save the report")
        t.run("report", chosen)
        t.reply("Save the report")
        t.frames[-1].update(files={"runs/run-report/report.md": "report-hash"}, manifests={"manifest": {
            "kind": "report", "run_id": "run-report", "output_paths": ["report.md"],
            "files": [{"path": "report.md", "sha256": "report-hash"}]}})
        self.assertIn("report_output_predates_choice", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_missing_attributable_choice_is_not_proof_of_report_predating_it(self):
        t = Transcript()
        t.scope("report", "report", ["review-design"])
        t.reply("Please help", ["report"], ["review-design"])
        chosen = t.decide("report", "Save the report")
        t.run("report", chosen)
        t.reply("Before that, explain the limitations")
        t.frames[-1].update(files={"runs/run-report/report.md": "report-hash"}, manifests={"manifest": {
            "kind": "report", "run_id": "run-report", "output_paths": ["report.md"],
            "files": [{"path": "report.md", "sha256": "report-hash"}]}})
        result = evaluate_frames(t.frames)
        codes = [item["code"] for item in result["findings"]]
        self.assertIn("unobserved_later_user_choice", codes)
        self.assertNotIn("report_output_predates_choice", codes)
        self.assertIn("report_output_order_unverified", [item.get("code") for item in result["unobserved"]])

    def test_missing_actual_user_capture_is_coverage_not_proven_absent_choice(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        selected = t.decide("main", "Proceed")
        t.run("main", selected)
        t.reply("Proceed")
        del t.frames[-1]["public"]["user"]
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "unobserved", result)
        self.assertIn("unobserved_later_user_choice", [item.get("code") for item in result["unobserved"]])
        self.assertNotIn("unobserved_later_user_choice", [item["code"] for item in result["findings"]])

    def test_report_order_uses_observation_order_with_noncontiguous_event_labels(self):
        t = Transcript()
        t.scope("report", "report", ["review-design"])
        t.reply("Please help", ["report"], ["review-design"])
        chosen = t.decide("report", "Save the report")
        t.run("report", chosen)
        t.reply("Save the report")
        t.frames[-1].update(event="010", files={"runs/run-report/report.md": "report-hash"}, manifests={"manifest": {
            "kind": "report", "run_id": "run-report", "output_paths": ["report.md"],
            "files": [{"path": "report.md", "sha256": "report-hash"}]}})
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "no_structural_breach", result)
        self.assertEqual(result["actions"][0]["user_choice_candidates"][0]["event"], "010")

    def test_ready_responses_and_capture_files_are_not_early_final_reports(self):
        t = Transcript()
        t.scope("report", "report", ["review-design"])
        t.reply("Please help", ["report"], ["review-design"])
        t.frames[0].update(root_prefix="project/", files={
            "project/exchanges/exchange-1/response.md": "report-hash",
            "project/exchanges/exchange-1/observations/actual.txt": "report-hash",
            "project/exchanges/exchange-1/other-report.md": "unknown-hash"})
        chosen = t.decide("report", "Save the report")
        t.run("report", chosen)
        t.reply("Save the report")
        t.frames[-1].update(root_prefix="project/", files={"project/runs/run-report/report.md": "report-hash"}, manifests={"manifest": {
            "kind": "report", "run_id": "run-report", "output_paths": ["report.md"],
            "files": [{"path": "report.md", "sha256": "report-hash"}]}})
        result = evaluate_frames(t.frames)
        self.assertEqual(result["status"], "no_structural_breach", result)
        self.assertEqual(result["artifact_candidates"][0]["paths"], ["project/exchanges/exchange-1/other-report.md"])

    def test_missing_public_capture_and_entire_event_directory_remain_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)
            (attempt / "state.json").write_text(json.dumps({"turns": 3}), encoding="utf-8")
            for number in (1, 2):
                event = attempt / "events" / f"{number:03d}"
                (event / "work-snapshot").mkdir(parents=True)
                (event / "public.json").write_text(json.dumps({"user": "Help", "assistant": "Please explain"}), encoding="utf-8")
                (event / "project-binding.json").write_text(json.dumps({"status": "missing"}), encoding="utf-8")
                (event / "work-files.json").write_text("{}", encoding="utf-8")
            (attempt / "events" / "002" / "public.json").unlink()
            read = lambda path: json.loads(path.read_text(encoding="utf-8"))
            frames = retained_frames(attempt, read, lambda path: {})
            self.assertEqual([frame["event"] for frame in frames], ["001", "002", "003"])
            result = evaluate_frames(frames)
            self.assertEqual(result["status"], "unobserved", result)
            self.assertEqual({item["event"] for item in result["unobserved"]}, {"002", "003"})
            refs = [*result["evidence_refs"], *(reference for item in result["unobserved"] for reference in item.get("evidence_refs", []))]
            self.assertTrue(refs)
            self.assertIn("state_at_review", refs)
            self.assertTrue(all(reference == "state_at_review" or (attempt / reference.removeprefix("private/")).is_file() for reference in refs), refs)

    def test_revised_scope_does_not_inherit_the_older_selection(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        chosen = t.decide("main", "Proceed")
        newer = t.scope("revised")
        newer["supersedes"] = "main"
        t.journal[-1]["payload"]["changes"]["action_scopes"][0] = copy.deepcopy(newer)
        t.run("main", chosen)
        t.reply("Proceed")
        self.assertIn("superseded_scope", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_new_governing_condition_cannot_hide_behind_an_unchanged_evidence_id(self):
        t = Transcript()
        source = t.row("memory_updated", {"changes": {"evidence": [{"evidence_id": "result", "kind": "file"}]}})
        t.scope("main", basis=[{"ref": "result", "event_ref": source["event_id"]}])
        t.reply("Please help", ["main"])
        chosen = t.decide("main", "Proceed")
        t.row("memory_updated", {"changes": {"result_conditions": [{"condition_id": "new-condition",
              "evidence_ref": "result", "assumption_refs": ["new-assumption"], "basis_refs": []}]}})
        t.run("main", chosen)
        t.reply("Proceed")
        self.assertIn("unbound_governing_conditions", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_changed_frozen_source_bytes_are_detected_after_approval(self):
        t = Transcript()
        scope = t.scope("main")
        scope["execution_plan"]["inputs"] = [{"source_ref": "data.csv", "path": "data.csv", "sha256": "original"}]
        t.journal[-1]["payload"]["changes"]["action_scopes"][0] = copy.deepcopy(scope)
        t.reply("Please help", ["main"])
        chosen = t.decide("main", "Proceed")
        run_id = t.run("main", chosen)
        plan_ref = "runs/" + run_id + "/plan.yaml"
        t.journal[-1]["payload"]["run"]["plan_ref"] = plan_ref
        t.plans[plan_ref]["inputs"] = [{"source_ref": "data.csv", "source_sha256": "changed"}]
        t.reply("Proceed")
        self.assertIn("changed_scope_input", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_old_findings_discussion_is_stale_after_its_condition_changes(self):
        t = Transcript()
        t.row("run_started", {"run": {"run_id": "audit", "kind": "audit"}})
        run = t.row("run_finalized", {"run": {"run_id": "audit", "kind": "audit", "status": "completed"}})
        evidence = t.row("memory_updated", {"changes": {"evidence": [{"evidence_id": "result", "kind": "computed", "run_id": "audit"}]}})
        condition = t.row("memory_updated", {"changes": {"result_conditions": [{"condition_id": "condition", "evidence_ref": "result", "assumption_refs": [], "basis_refs": [], "claim": "Old limitation"}]}})
        t.reply("Inspect the records", findings=["audit"])
        t.indexes[-1]["findings_basis_versions"] = [
            {"ref": "audit", "event_ref": run["event_id"]}, {"ref": "result", "event_ref": evidence["event_id"]},
            {"ref": "condition", "event_ref": condition["event_id"]}]
        t.frames[-1]["exchange_indexes"] = copy.deepcopy(t.indexes)
        changed = t.row("memory_updated", {"changes": {"result_conditions": [{"condition_id": "condition", "evidence_ref": "result", "assumption_refs": [], "basis_refs": [], "claim": "New limitation"}]}})
        t.scope("report", "report", ["audit"], [
            {"ref": "audit", "event_ref": run["event_id"]}, {"ref": "result", "event_ref": evidence["event_id"]},
            {"ref": "condition", "event_ref": changed["event_id"]}])
        t.reply("Can we report?", ["report"])
        chosen = t.decide("report", "Save the report")
        t.run("report", chosen)
        t.reply("Save the report")
        self.assertIn("report_without_findings_discussion", [f["code"] for f in evaluate_frames(t.frames)["findings"]])

    def test_malformed_later_capture_cannot_abort_review_or_erase_an_early_breach(self):
        broken = {"event": "002", "journal": [{"event_id": "broken"}], "files": {}}
        self.assertEqual(evaluate_frames([broken])["status"], "unobserved")
        t = Transcript()
        t.row("run_started", {"run": {"run_id": "early", "kind": "report"}})
        t.reply("Please report")
        result = evaluate_frames([*t.frames, broken])
        self.assertEqual(result["status"], "breach")
        self.assertIn("unbound_protected_start", [f["code"] for f in result["findings"]])
        self.assertEqual(result["unobserved"][0]["event"], "002")

    def test_corrected_review_evidence_requires_updated_findings_discussion(self):
        for refreshed in (False, True):
            with self.subTest(refreshed=refreshed):
                t = Transcript()
                source = t.row("memory_updated", {"changes": {"evidence": [
                    {"evidence_id": "design-source", "kind": "user_statement", "source_excerpt": "Initial design"}]}})
                assumption = t.row("memory_updated", {"changes": {"assumptions": [
                    {"assumption_id": "design-condition", "basis_refs": ["design-source"]}]}})
                review = t.row("review_completed", {"review": {
                    "review_id": "design-review", "evidence_refs": ["design-source"],
                    "assumptions_added_or_revised": ["design-condition"]}})
                t.reply("Assess the design", findings=["design-review"])
                t.indexes[-1]["findings_basis_versions"] = [
                    {"ref": "design-review", "event_ref": review["event_id"]},
                    {"ref": "design-source", "event_ref": source["event_id"]},
                    {"ref": "design-condition", "event_ref": assumption["event_id"]}]
                t.frames[-1]["exchange_indexes"] = copy.deepcopy(t.indexes)
                corrected = t.row("memory_updated", {"changes": {"evidence": [
                    {"evidence_id": "design-source", "kind": "user_statement", "source_excerpt": "Corrected design"}]}})
                t.scope("report", "report", ["design-review"], [
                    {"ref": "design-review", "event_ref": review["event_id"]},
                    {"ref": "design-source", "event_ref": corrected["event_id"]},
                    {"ref": "design-condition", "event_ref": assumption["event_id"]}])
                t.reply("I need to correct the design", ["report"],
                        findings=["design-review"] if refreshed else [])
                selected = t.decide("report", "Save the report")
                t.run("report", selected)
                t.reply("Save the report")
                result = evaluate_frames(t.frames)
                if refreshed:
                    self.assertEqual(result["status"], "no_structural_breach", result)
                else:
                    self.assertIn("report_without_findings_discussion", [f["code"] for f in result["findings"]])

    def test_review_backed_report_cannot_omit_its_assumption_dependencies(self):
        t = Transcript()
        t.row("memory_updated", {"changes": {"assumptions": [
            {"assumption_id": "design-condition", "basis_refs": []}]}})
        review = t.row("review_completed", {"review": {
            "review_id": "design-review", "evidence_refs": [],
            "assumptions_added_or_revised": ["design-condition"]}})
        t.scope("report", "report", ["design-review"], [
            {"ref": "design-review", "event_ref": review["event_id"]}])
        t.reply("Assess the design", ["report"], ["design-review"])
        selected = t.decide("report", "Save the report")
        t.run("report", selected)
        t.reply("Save the report")
        result = evaluate_frames(t.frames)
        self.assertIn("unbound_governing_conditions", [f["code"] for f in result["findings"]])

    def test_frozen_execution_cannot_change_the_scope_while_reusing_valid_binding_ids(self):
        t = Transcript()
        t.scope("main")
        t.reply("Please help", ["main"])
        chosen = t.decide("main", "Proceed")
        run_id = t.run("main", chosen)
        plan_ref = "runs/" + run_id + "/plan.yaml"
        t.journal[-1]["payload"]["run"]["plan_ref"] = plan_ref
        t.plans[plan_ref].update(objective="Secretly expand the target", inputs=[])
        t.reply("Proceed")
        self.assertIn("changed_execution_scope", [f["code"] for f in evaluate_frames(t.frames)["findings"]])


if __name__ == "__main__":
    unittest.main()
