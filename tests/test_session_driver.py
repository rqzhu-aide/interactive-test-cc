import copy
import json
from pathlib import Path
import shutil
import subprocess
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
            raise RuntimeError("Integration tests require a shared Node and the sibling consultant " +
                               ", ".join(driver.CONSULTANT_VERSIONS) + " package")

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

    def full_report_case(self):
        manifest = driver.read(self.case / "case.json")
        manifest["completion_contract"] = "full_report"
        driver.write(self.case / "case.json", manifest)
        reviewer = driver.read(self.case / "reviewer.json")
        reviewer["useful_stop"] = True  # Exercise both otherwise-successful review outcomes.
        driver.write(self.case / "reviewer.json", reviewer)
        self.manifest()

    def saved_run(self, run_id="report-main", status="completed", content="<html><body>Test-only report.</body></html>",
                  kind="report", project_root="consultation"):
        """Produce actual v7 journal/manifest evidence with the staged helper, not fake status JSON."""
        script = r"""
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const [scripts, root] = process.argv.slice(1);
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
const store = require(path.join(scripts, 'lib/store.cjs'));
const runs = require(path.join(scripts, 'lib/runs.cjs'));
const current = () => store.status(root).project.state_meta;
const ids = event_id => ({event_id, expected_project_id: current().project_id, expected_last_event_id: current().last_event_id});
if (!fs.existsSync(path.join(root, 'journal.jsonl'))) {
  store.init(root, {event_id:'event-init', project_id:'project-test', project_understanding:{objective:'Test-only report evidence'}});
  store.record(root, {...ids('event-source'), type:'memory_updated', payload:{changes:{evidence:[{
    evidence_id:'source-data', kind:'file', source_ref:'data.csv', summary:'Frozen public input for a structural test.',
    source_sha256:crypto.createHash('sha256').update(fs.readFileSync(spec.source)).digest('hex')
  }]}}});
}
const plan = {kind:spec.kind, objective:'Save a test-only artifact.', claim_boundary:'Structural test only.',
  inputs:[{source_ref:'data.csv',path:spec.source}],
  ...(spec.kind === 'report' ? {purpose:'Test report completion.',evidence_refs:['source-data'],format:'html'} :
    {question:'Test an audit artifact.',diagnostics:[]})};
runs.start(root, {...ids('event-start-'+spec.run_id),run_id:spec.run_id,plan});
const {event_id, ...writeIds} = ids('unused');
runs.write(root, {...writeIds,run_id:spec.run_id,path:'report.html',content:spec.content});
if (spec.status === 'completed') {
  runs.finalize(root, {...ids('event-final-'+spec.run_id),run_id:spec.run_id,code_paths:[],output_paths:['report.html'],
    diagnostic_paths:[],environment:{test_only:true},deviations:[]});
} else if (spec.status !== 'in_progress') {
  const terminal = spec.status === 'failed' ? runs.failRun : runs.abandon;
  terminal(root, {...ids('event-terminal-'+spec.run_id),run_id:spec.run_id,reason:'Test-only unfinished revision.'});
}
process.stdout.write(JSON.stringify(store.status(root)));
"""
        result = subprocess.run([self.node, "-e", script,
                                 str(self.work / ".claude/skills/causal-consultant/scripts"), str(self.work / project_root)],
                                input=json.dumps({"run_id": run_id, "status": status, "content": content,
                                                  "kind": kind, "source": str(self.work / "data.csv")}),
                                text=True, encoding="utf-8", capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def completion_check(self):
        state = driver.read(self.attempt / "state.json")
        return driver.full_report_completion(self.attempt, state, driver.evidence(self.attempt, state))

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

    def test_private_world_identity_and_staging(self):
        manifest = driver.read(self.case / "case.json")
        manifest.update(world="world.json", world_id="world-test", world_version="1.0.0", persona_id="user-test")
        driver.write(self.case / "case.json", manifest)
        actor = driver.read(self.case / "actor.json")
        actor["persona_id"] = "user-test"
        driver.write(self.case / "actor.json", actor)
        world = {"world_id": "world-test", "world_version": "1.0.0", "private_truth": "TEST_ONLY_PRIVATE_VALUE"}
        driver.write(self.case / "world.json", world)
        self.manifest()
        driver.validate_case(self.case)
        for changed in ({**world, "world_id": "wrong"}, {**world, "world_version": "2.0.0"}):
            driver.write(self.case / "world.json", changed)
            self.manifest()
            with self.assertRaisesRegex(ValueError, "world identity mismatch"):
                driver.validate_case(self.case)
        driver.write(self.case / "world.json", world)
        self.manifest()
        self.begin()
        self.assertFalse((self.work / "world.json").exists())
        self.assertNotIn("TEST_ONLY_PRIVATE_VALUE", json.dumps(driver.inspect(self.attempt, "actor")))
        driver.step(self.attempt, self.reply(initial=True))
        with self.assertRaisesRegex(ValueError, "private path leaked"):
            driver.step(self.attempt, self.reply(message="Please read world.json."))

    def test_private_actor_learning_survives_replies_without_public_leak(self):
        self.begin()
        change = {"subject": "belief-spending", "before": "The spreadsheet specifies an intervention.",
                  "after": "The extra spending still needs a concrete purpose.",
                  "evidence": "The consultant's first reply asks what extra funding would pay for."}
        with self.assertRaisesRegex(ValueError, "initial dispatch"):
            driver.step(self.attempt, self.reply(initial=True, belief_updates=[change]))
        driver.step(self.attempt, self.reply(initial=True))
        for invalid in ({"belief_updates": {}}, {"knowledge_updates": [{"subject": "x"}]},
                        {"decision_updates": [{**change, "evidence": ""}]},
                        {"belief_updates": [{**change, "extra": "reviewer truth"}]}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                driver.step(self.attempt, self.reply(**invalid))
        driver.step(self.attempt, self.reply(belief_updates=[change]))
        driver.step(self.attempt, self.reply(message="Please explain the available options."))
        visible = driver.inspect(self.attempt, "actor")
        self.assertEqual(visible["actor_updates"], [{"event": "002", "belief_updates": [change]}])
        self.assertEqual(len(visible["conversation"]), 3)
        self.assertNotIn("belief-spending", json.dumps(visible["conversation"]))
        sent = (self.attempt / "events/002/transport/request.txt").read_text(encoding="utf-8")
        self.assertNotIn("belief-spending", sent)
        self.assertEqual(driver.read(self.attempt / "events/002/actor.json")["belief_updates"], [change])

    def test_candidate_inventory_accepts_only_explicit_compatible_versions(self):
        candidate = self.root / "version-probe"
        candidate.mkdir()
        (candidate / "SKILL.md").write_text("Test-only runtime file.", encoding="utf-8")
        for version in ("7.0.0", "7.0.1", "7.0.2", "7.0.4", "7.0.5", "7.0.6"):
            with self.subTest(version=version):
                driver.write(candidate / "package.json", {"version": version, "files": ["SKILL.md"]})
                self.assertEqual(driver.candidate_inventory(candidate), {
                    "SKILL.md": driver.digest(candidate / "SKILL.md"),
                    "package.json": driver.digest(candidate / "package.json")})
        for version in ("6.9.9", "7.0.3", "7.0.7", "7.1.0", "7.0.2-preview", "7.0.4-preview", "7.0.5-preview", "7.0.6-preview"):
            with self.subTest(version=version):
                driver.write(candidate / "package.json", {"version": version, "files": ["SKILL.md"]})
                with self.assertRaisesRegex(ValueError, "observation profile"):
                    driver.candidate_inventory(candidate)

    def test_new_profile_requires_capability_and_preserves_old_profile(self):
        candidate = self.root / "profile-probe"
        candidate.mkdir()
        for version in ("7.0.5", "7.0.6"):
            driver.write(candidate / "package.json", {"version": version})
            for code, body in ((1, {}), (0, {"capabilities": []}), (0, []),
                               (0, {"capabilities": driver.EXCHANGE_CAPABILITY})):
                with self.subTest(version=version, code=code, body=body), patch.object(driver.subprocess, "run") as run:
                    run.return_value = subprocess.CompletedProcess([], code, json.dumps(body).encode(), b"")
                    with self.assertRaisesRegex(ValueError, version + ".*(capability|lacks)"):
                        driver.candidate_observation_profile(candidate, self.config)
            with self.subTest(version=version), patch.object(driver.subprocess, "run") as run:
                run.return_value = subprocess.CompletedProcess([], 0, json.dumps({
                    "capabilities": [driver.EXCHANGE_CAPABILITY]}).encode(), b"")
                profile = driver.candidate_observation_profile(candidate, self.config)
                self.assertEqual(profile["consultant_version"], version)
                self.assertEqual(profile["capabilities"], [driver.EXCHANGE_CAPABILITY])
                self.assertFalse(profile["user_question_routing"])
                self.assertEqual(profile["enforcement"], "observational_only")
                self.assertEqual(run.call_args.args[0][-1], "capabilities")
                run.return_value = subprocess.CompletedProcess([], 0, json.dumps({
                    "capabilities": [driver.EXCHANGE_CAPABILITY, driver.USER_QUESTION_CAPABILITY]}).encode(), b"")
                self.assertTrue(driver.candidate_observation_profile(candidate, self.config)["user_question_routing"])
        with patch.object(driver.subprocess, "run") as run:
            driver.write(candidate / "package.json", {"version": "7.0.4"})
            self.assertEqual(driver.candidate_observation_profile(candidate, self.config)["capabilities"], [])
            run.assert_not_called()

    def test_project_root_binding_is_explicit_or_unique_and_contained(self):
        files = {"journal.jsonl": "root", ".claude/skills/example/journal.jsonl": "runtime"}
        self.assertEqual(driver.project_binding(files, {})["project_root"], ".")
        files["nested/journal.jsonl"] = "second"
        self.assertEqual(driver.project_binding(files, {})["status"], "ambiguous")
        self.assertEqual(driver.project_binding(files, {"project_root": "nested"})["project_root"], "nested")
        self.assertEqual(driver.project_binding({}, {})["status"], "missing")
        for value in ("../outside", "C:/outside", "nested/../outside", "nested/", "", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                driver.validate_config({**self.config, "project_root": value})

    def test_work_root_journal_is_observed_and_report_completion_uses_same_root(self):
        self.full_report_case()
        self.begin()
        self.saved_run(project_root=".")
        driver.step(self.attempt, self.reply(initial=True))
        event = self.attempt / "events/001"
        self.assertEqual(driver.read(event / "project-binding.json")["project_root"], ".")
        for command in ("status", "context", "verify"):
            self.assertEqual(driver.read(event / ("project-" + command) / "process.json")["exit_code"], 0)
        completion = self.completion_check()
        self.assertTrue(completion["satisfied"], completion["reason"])
        self.assertIn("work/runs/report-main/report.html", completion["evidence_refs"])
        self.assertFalse((self.work / "consultation").exists())

    def test_ambiguous_projects_are_not_silently_observed_or_counted_as_report(self):
        self.full_report_case()
        self.begin()
        self.saved_run(project_root="first")
        self.saved_run(project_root="second")
        driver.step(self.attempt, self.reply(initial=True))
        event = self.attempt / "events/001"
        self.assertEqual(driver.read(event / "project-binding.json")["status"], "ambiguous")
        self.assertFalse((event / "project-status").exists())
        self.assertFalse(self.completion_check()["satisfied"])

    def test_explicit_project_binding_selects_recorded_report_among_projects(self):
        self.full_report_case()
        self.config["project_root"] = "second"
        self.begin()
        self.saved_run(project_root="first")
        self.saved_run(project_root="second")
        driver.step(self.attempt, self.reply(initial=True))
        completion = self.completion_check()
        self.assertTrue(completion["satisfied"], completion["reason"])
        self.assertEqual(completion["project_root"], "second")
        self.assertIn("work/second/runs/report-main/report.html", completion["evidence_refs"])

    def test_durable_final_correspondence_is_observed_without_journal_mutation(self):
        self.begin()
        project = self.work / "consultation"
        script = r"""
const fs = require('fs'), path = require('path');
const [scripts, root] = process.argv.slice(1);
const store = require(path.join(scripts, 'lib/store.cjs'));
store.init(root, {event_id:'event-init',project_id:'project-exchange',project_understanding:{objective:'Test exchange observation.'}});
const state = store.status(root).project.state_meta;
const receipt = store.record(root, {event_id:'event-close',expected_project_id:state.project_id,
 expected_last_event_id:state.last_event_id,type:'exchange_prepared',payload:{
 protocol:'durable-exchanges-v1',changes:{evidence:[{evidence_id:'user-message',kind:'user_statement',
 source_ref:'chat:turn-1',summary:'Please explain the current state.'}]},
 interpretation:{interpretation_id:'interpret-turn',turn_id:'turn-one',incoming_refs:['user-message'],basis_refs:[],
 components:[{kind:'instruction',meaning:'Explain current state.',established:['Explanation requested.'],unresolved:[]}],
 next_action:{kind:'lead_only',scope:'Explain current state.',reason:'No specialist review required.'}},
 exchange:{exchange_id:'exchange-one',turn_id:'turn-one',interpretation_ref:'interpret-turn',basis_refs:[],completed_work_refs:[],
 reconciliation:{changes:[],limitations:[],unresolved:[],next_direction:'Complete explanation.'},renderer:'lead-markdown-v1',
 response:{status:'Résumé: test-only state.',questions:[],questions_none:'No questions.',next_steps:[],next_steps_none:'Complete.'}}}});
process.stdout.write(JSON.stringify(receipt));
"""
        run = subprocess.run([self.node, "-e", script,
                              str(self.work / ".claude/skills/causal-consultant/scripts"), str(project)],
                             text=True, encoding="utf-8", capture_output=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        receipt = json.loads(run.stdout)
        before = (project / "journal.jsonl").read_bytes()
        state = driver.read(self.attempt / "state.json")
        state["started_at"] = time.time()
        messages = (receipt["rendered_response"], receipt["rendered_response"] + "\nRewritten.", None)
        for number, message in enumerate(messages, 1):
            event = self.attempt / "events" / f"{number:03d}"
            event.mkdir()
            driver.write(event / "public.json", {"user": "Test request.", "assistant": message, "attachments": []})
            driver.observe_project(event, state, self.config)
            observed = driver.read(event / "exchange-observation.json")
            self.assertEqual(observed["status"], ("matched", "mismatch", "unobserved")[number - 1])
            self.assertEqual(observed["enforcement"], "observational_only")
            if number == 2:
                self.assertFalse(observed["new_since_previous_observation"])
            if number == 1:
                self.assertEqual(observed["expected_response_sha256"], receipt["response_sha256"])
                self.assertEqual(observed["renderer"], "lead-markdown-v1")
                self.assertIsNone(observed["user_questions"])
                context = driver.read(event / "project-context/stdout.txt")
                self.assertEqual(context["views"]["work"]["current_exchange_ref"], "exchange-one")
        self.assertEqual(before, (project / "journal.jsonl").read_bytes())
        self.assertEqual(driver.read(self.attempt / "events/001/project-status/stdout.txt")["project"]["deliveries"], [])

    def test_v3_observation_preserves_user_questions_and_pending_view_without_delivery(self):
        self.begin()
        project = self.work / "consultation"
        script = r"""
const path = require('path');
const [scripts, root] = process.argv.slice(1);
const store = require(path.join(scripts, 'lib/store.cjs'));
store.init(root, {event_id:'event-init',project_id:'project-questions',project_understanding:{objective:'Test question capture.'}});
const state = store.status(root).project.state_meta;
const receipt = store.record(root, {event_id:'event-close',expected_project_id:state.project_id,
 expected_last_event_id:state.last_event_id,type:'exchange_prepared',payload:{
 protocol:'durable-exchanges-v1',changes:{evidence:[{evidence_id:'user-message',kind:'user_statement',
 source_ref:'chat:turn-1',summary:'Why does assignment matter, and what will the effect estimate be?'}],questions:[
 {question_id:'question-why',origin:'user',statement:'Why does assignment matter?',status:'answered',reason:'Explained comparison.',basis_refs:['user-message']},
 {question_id:'question-effect',origin:'user',statement:'What will the effect estimate be?',status:'open',reason:'No analysis yet.',basis_refs:['user-message']},
 {question_id:'question-data',origin:'consultant',statement:'Can you share the data?',status:'open',basis_refs:['user-message']} ]},
 interpretation:{interpretation_id:'interpret-turn',turn_id:'turn-one',incoming_refs:['user-message'],basis_refs:[],
 components:[{kind:'question',meaning:'Explain assignment before work.',established:[],unresolved:[],user_question_ref:'question-why',answer_timing:'before_work'},
 {kind:'question',meaning:'Answer the effect question from eventual results.',established:[],unresolved:['No analysis yet.'],user_question_ref:'question-effect',answer_timing:'after_work'}],
 next_action:{kind:'lead_only',scope:'Explain assignment and retain the result question.',reason:'An explanation is needed first.'}},
 exchange:{exchange_id:'exchange-one',turn_id:'turn-one',interpretation_ref:'interpret-turn',basis_refs:[],completed_work_refs:[],
 reconciliation:{changes:['Explained assignment.'],limitations:['No analysis yet.'],unresolved:['Effect question remains open.'],next_direction:'Obtain the data.'},renderer:'lead-markdown-v3',
 response:{user_questions:[
 {question_ref:'question-why',text:'Why does assignment matter?',answer:'It determines which comparison can support the effect claim.',status:'answered',basis_refs:['user-message']},
 {question_ref:'question-effect',text:'What will the effect estimate be?',answer:'This remains pending until the data can be analyzed.',status:'pending',basis_refs:['user-message']}],
 status:'No analysis has been performed.',questions:[{question_ref:'question-data',text:'Can you share the data?',why:'The effect requires observations.',needed:'The study data file.'}],
 next_steps:[],next_steps_none:'Share the study data when available.'}}}});
process.stdout.write(JSON.stringify(receipt));
"""
        run = subprocess.run([self.node, "-e", script,
                              str(self.work / ".claude/skills/causal-consultant/scripts"), str(project)],
                             text=True, encoding="utf-8", capture_output=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        receipt = json.loads(run.stdout)
        before = (project / "journal.jsonl").read_bytes()
        state = driver.read(self.attempt / "state.json")
        state["started_at"] = time.time()
        event = self.attempt / "events/001"
        event.mkdir()
        driver.write(event / "public.json", {"user": "Test question request.",
                                             "assistant": receipt["rendered_response"], "attachments": []})
        driver.observe_project(event, state, self.config)
        observed = driver.read(event / "exchange-observation.json")
        self.assertEqual(observed["status"], "matched")
        self.assertEqual(observed["renderer"], "lead-markdown-v3")
        self.assertEqual([(item["question_ref"], item["status"]) for item in observed["user_questions"]],
                         [("question-why", "answered"), ("question-effect", "pending")])
        self.assertEqual(observed["pending_user_question_refs"], ["question-effect"])
        context = driver.read(event / "project-context/stdout.txt")
        self.assertEqual(context["views"]["work"]["pending_user_question_refs"], ["question-effect"])
        interpretation = next(item for item in context["views"]["work"]["interpretations"]
                              if item["interpretation_id"] == "interpret-turn")
        self.assertEqual([(item["user_question_ref"], item["answer_timing"])
                          for item in interpretation["components"] if item["kind"] == "question"],
                         [("question-why", "before_work"), ("question-effect", "after_work")])
        self.assertEqual(interpretation["next_action"]["kind"], "lead_only")
        self.assertEqual(before, (project / "journal.jsonl").read_bytes())
        self.assertEqual(driver.read(event / "project-status/stdout.txt")["project"]["deliveries"], [])

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

    def test_case_completion_contract_is_opt_in_and_validated(self):
        for contract in ("focused", "full_report"):
            manifest = driver.read(self.case / "case.json")
            manifest["completion_contract"] = contract
            driver.write(self.case / "case.json", manifest)
            self.assertEqual(driver.validate_case(self.case)["completion_contract"], contract)
        for contract in (None, True, "recap"):
            manifest["completion_contract"] = contract
            driver.write(self.case / "case.json", manifest)
            with self.assertRaisesRegex(ValueError, "completion contract"):
                driver.validate_case(self.case)

    def test_reportless_stop_finishes_incomplete_despite_reviewer_assertion(self):
        self.full_report_case()
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        stopped = driver.step(self.attempt, self.reply(message=None, stop=True, fact_ids=[], rule_ids=[]))
        self.assertEqual(stopped["status"], "awaiting_review")
        review = self.assessment()
        review["completion_check"] = {"satisfied": True, "reason": "Reviewer claims a report exists."}
        result = driver.finish(self.attempt, review)
        self.assertEqual(result["outcome"], "incomplete")
        self.assertFalse(result["completion_check"]["satisfied"])
        self.assertEqual(result["quality_rating"], "inconclusive")
        self.assertEqual(driver.read(self.attempt / "state.json")["status"], "finished")

    def test_reportless_useful_stop_cannot_bypass_full_report(self):
        self.full_report_case()
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        review = self.assessment()
        review.update(outcome="useful_stop", useful_stop_basis="Test-only permitted limited advice.")
        result = driver.finish(self.attempt, review)
        self.assertEqual(result["outcome"], "incomplete")
        self.assertFalse(result["completion_check"]["satisfied"])

    def test_six_consultant_turns_keep_session_and_complete_report_at_turn_cap(self):
        self.full_report_case()
        self.config["limits"]["consultant_turns"] = 6
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        for _ in range(4):
            self.assertEqual(driver.step(self.attempt, self.reply())["status"], "ready")
        self.saved_run()
        self.assertEqual(driver.step(self.attempt, self.reply(message="Please finish the saved report.",
                                                            fact_ids=[], rule_ids=[]))["status"], "ready")
        state = driver.read(self.attempt / "state.json")
        self.assertEqual(state["turns"], 6)
        transports = [driver.read(p) for p in sorted((self.attempt / "events").glob("*/transport/transport.json"))]
        self.assertEqual(len(transports), 6)
        self.assertEqual({t["session_id"] for t in transports}, {state["session_id"]})
        self.assertIn("--session-id", transports[0]["argv"])
        self.assertTrue(all("--resume" in t["argv"] for t in transports[1:]))
        driver.step(self.attempt, self.reply(message=None, stop=True, fact_ids=[], rule_ids=[]))
        result = driver.finish(self.attempt, self.assessment())
        self.assertEqual(result["outcome"], "objective_met")
        self.assertTrue(result["completion_check"]["satisfied"])
        self.assertEqual(result["completion_check"]["run_id"], "report-main")
        self.assertIn("work/consultation/runs/report-main/report.html", result["completion_check"]["evidence_refs"])
        self.assertFalse(result["resources"]["breaches"])

    def test_latest_verified_report_rejects_stale_or_missing_evidence(self):
        self.full_report_case()
        self.begin()
        self.saved_run()
        driver.step(self.attempt, self.reply(initial=True))
        self.assertTrue(self.completion_check()["satisfied"])
        output = self.work / "consultation/runs/report-main/report.html"
        verify_log = self.attempt / "events/001/project-verify/stdout.txt"
        snapshot_output = self.attempt / "events/001/work-snapshot/consultation/runs/report-main/report.html"
        for path, replacement in ((output, b"changed after verification"),
                                  (self.work / "data.csv", b"source changed after verification"),
                                  (verify_log, None), (snapshot_output, None)):
            original = path.read_bytes()
            with self.subTest(path=path):
                if replacement is None:
                    path.unlink()
                else:
                    path.write_bytes(replacement)
                self.assertFalse(self.completion_check()["satisfied"])
                path.write_bytes(original)
        stale = driver.read(verify_log)
        original = verify_log.read_bytes()
        stale["last_event_id"] = "event-stale"
        driver.write(verify_log, stale)
        self.assertFalse(self.completion_check()["satisfied"])
        verify_log.write_bytes(original)
        self.saved_run(run_id="report-new", status="in_progress")
        result = driver.finish(self.attempt, self.assessment())
        self.assertEqual(result["outcome"], "incomplete")
        self.assertFalse(result["completion_check"]["satisfied"])

    def test_empty_manifested_report_does_not_complete_full_report(self):
        self.full_report_case()
        self.begin()
        self.saved_run(content="")
        driver.step(self.attempt, self.reply(initial=True))
        self.assertTrue(driver.read(self.attempt / "events/001/project-verify/stdout.txt")["ok"])
        result = driver.finish(self.attempt, self.assessment())
        self.assertEqual(result["outcome"], "incomplete")
        self.assertFalse(result["completion_check"]["satisfied"])

    def test_report_named_audit_output_and_loose_file_do_not_count_as_report(self):
        self.full_report_case()
        self.begin()
        self.saved_run(kind="audit")
        (self.work / "consultation/report.html").write_text("An unmanifested report-looking file.", encoding="utf-8")
        driver.step(self.attempt, self.reply(initial=True))
        self.assertTrue(driver.read(self.attempt / "events/001/project-verify/stdout.txt")["ok"])
        result = driver.finish(self.attempt, self.assessment())
        self.assertEqual(result["outcome"], "incomplete")

    def test_older_completed_report_cannot_hide_later_unfinished_revision(self):
        self.full_report_case()
        for status in ("in_progress", "failed", "abandoned"):
            with self.subTest(status=status):
                self.attempt, self.work = self.root / (status + "-private"), self.root / (status + "-work")
                self.begin()
                self.saved_run()
                self.saved_run(run_id="report-revision", status=status)
                driver.step(self.attempt, self.reply(initial=True))
                result = driver.finish(self.attempt, self.assessment())
                self.assertEqual(result["outcome"], "incomplete")
                self.assertFalse(result["completion_check"]["satisfied"])

    def test_full_report_keeps_cap_and_execution_failure_outcomes(self):
        self.full_report_case()
        self.config["limits"]["consultant_turns"] = 1
        for scenario, expected in (("ok", "incomplete"), ("provider_error", "execution_error")):
            with self.subTest(scenario=scenario):
                self.attempt, self.work = self.root / (scenario + "-private"), self.root / (scenario + "-work")
                self.config["claude_command"][-1] = scenario
                self.begin()
                driver.step(self.attempt, self.reply(initial=True))
                if scenario == "ok":
                    driver.step(self.attempt, self.reply())
                result = driver.finish(self.attempt, self.assessment())
                self.assertEqual(result["outcome"], expected)

    def test_focused_completion_still_needs_no_report(self):
        self.begin()
        driver.step(self.attempt, self.reply(initial=True))
        result = driver.finish(self.attempt, self.assessment())
        self.assertEqual(result["outcome"], "objective_met")
        self.assertIsNone(result["completion_check"])

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
        for owner in ("simulator", "fixture", "harness", "environment"):
            invalid = copy.deepcopy(minor)
            invalid["findings"][0].update(owner=owner, severity="material")
            result = driver.assess(invalid, state, frozen, index)
            self.assertEqual(result["test_validity"], "invalid")
            self.assertEqual(result["quality_rating"], "inconclusive")
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
