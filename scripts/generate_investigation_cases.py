"""Maintain the eight frozen synthetic investigation cases; standard library only.

Run explicitly to recreate version 1.0.1 bytes. Changes to frozen content require
a new case version and a new comparison freeze, never an in-place live repair.
The emitted standalone oracle uses a different calculation from the Fraction
reference calculation here and never imports this generator or consultant code.
"""
import csv
from fractions import Fraction
import hashlib
import io
import itertools
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
SEED = 260909
CASE_VERSION = "1.0.1"
SUITE_VERSION = "7.0.2"
KINDS = (
    "allocation-recoverable", "allocation-lost", "timing-aligned", "timing-late",
    "scope-intermediate", "scope-closed", "design-complete", "design-missing",
)
LIMITS = {"consultant_turns": 12, "active_seconds": 7200, "elapsed_seconds": 10800}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def text_file(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def fact(key, statement, source, when, certainty="known", constraint="Reveal only the relevant elements, in the user's own words."):
    return {"fact_id": key, "statement": statement, "certainty": certainty,
            "source": source, "available_when": when, "disclosure_condition": constraint}


def rule(key, condition, action, facts=(), sources=()):
    return {"rule_id": key, "condition": condition, "action": action,
            "fact_ids": list(facts), "source_ids": list(sources)}


def criterion(key, value):
    return {"id": key, "required": True, "rule": value}


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def reference(rows, ready):
    """Exact rational references, independently recomputed by emitted checker."""
    outcome = "score" if ready else "completion_2024_pct"
    arms = [[Fraction(row[outcome]) for row in rows if row["grant_offer"] == arm] for arm in (0, 1)]
    means = [sum(values, Fraction(0)) / len(values) for values in arms]
    variances = [sum((v - mean) ** 2 for v in values) / (len(values) - 1)
                 for values, mean in zip(arms, means)]
    effect = means[1] - means[0]
    result = {
        "n": len(rows), "arm_counts": [len(values) for values in arms],
        "control_mean": float(means[0]), "offered_mean": float(means[1]),
        "difference_offered_minus_control": float(effect),
        "sample_variances": [float(v) for v in variances],
        "neyman_variance": float(sum(v / len(values) for v, values in zip(variances, arms))),
    }
    if ready:
        outcomes = [Fraction(row[outcome]) for row in rows]
        total = sum(outcomes)
        extreme = sum(abs((2 * sum(outcomes[i] for i in group) - total) / 6) >= abs(effect)
                      for group in itertools.combinations(range(12), 6))
        result["sharp_null_two_sided"] = {"allocations": 924, "extreme": extreme,
                                           "p_value": float(Fraction(extreme, 924))}
    return result


ORACLE_CHECK = '''"""Standalone fixture self-check. No model outputs, generator import or packages."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def close(actual, expected, name="oracle"):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), name + ": fields"
        for key in expected:
            close(actual[key], expected[key], name + "." + key)
    elif isinstance(expected, list):
        assert len(actual) == len(expected), name + ": length"
        for i, (left, right) in enumerate(zip(actual, expected)):
            close(left, right, name + "." + str(i))
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10), name + ": number"
    else:
        assert actual == expected, name + ": value"


def calculate():
    specification = json.loads((ROOT / "oracle.json").read_text(encoding="utf-8"))
    ready = specification["world"]["n"] == 12
    path = ROOT / "public/data.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        rows = list(reader)
    ids = [row["site_id"] for row in rows]
    n = specification["world"]["n"]
    assert ids == ["S%02d" % i for i in range(1, n + 1)], "roster/ordering"
    assert len(set(ids)) == n and all(value != "" for row in rows for value in row.values())
    assigned = [row["site_id"] for row in rows if row["grant_offer"] == "1"]
    assert assigned == specification["world"]["realized_offered_ids"], "allocation"
    outcome = "score" if ready else "completion_2024_pct"
    suspect = []
    for i, row in enumerate(rows, 1):
        z = int(row["grant_offer"])
        assert z in (0, 1)
        y = float(row[outcome])
        if ready:
            assert y == 2 * i + 3 * z, "potential-outcome consistency"
        else:
            base = 45 + (7 * i % 31)
            assert int(row["entrants"]) == 100, "cohort denominator"
            assert y == base + specification["world"]["assignment_effect"] * z, "potential-outcome consistency"
            assert 0 <= y <= 100, "primary outcome support"
            baseline = float(row["baseline_completion_pct"])
            expected_baseline = 118 if specification["world"]["baseline_anomaly"] and i == 7 else base - 2
            assert baseline == expected_baseline, "baseline generation"
            if not 0 <= baseline <= 100:
                suspect.append(row["site_id"])
    groups = [[float(row[outcome]) for row in rows if row["grant_offer"] == str(arm)] for arm in (0, 1)]
    means = [math.fsum(values) / len(values) for values in groups]
    variances = [math.fsum((v - mean) ** 2 for v in values) / (len(values) - 1)
                 for values, mean in zip(groups, means)]
    effect = means[1] - means[0]
    estimate = {"n": n, "arm_counts": [len(v) for v in groups],
                "control_mean": means[0], "offered_mean": means[1],
                "difference_offered_minus_control": effect,
                "sample_variances": variances,
                "neyman_variance": math.fsum(v / len(g) for v, g in zip(variances, groups))}
    if ready:
        values = [int(row[outcome]) for row in rows]
        # Integer contrast gives exact ties without floating-point tail ambiguity.
        observed_numerator = abs(sum(int(row["score"]) * (2 * int(row["grant_offer"]) - 1) for row in rows))
        contrasts = [abs(2 * sum(values[i] for i in group) - sum(values))
                     for group in itertools.combinations(range(n), n // 2)]
        extreme = sum(value >= observed_numerator for value in contrasts)
        estimate["sharp_null_two_sided"] = {"allocations": len(contrasts), "extreme": extreme,
                                             "p_value": extreme / len(contrasts)}
    result = {"data_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "columns": columns,
              "unique_ids": len(set(ids)), "missing_cells": 0, "suspect_baseline_ids": suspect,
              "statistics": estimate}
    close(result, specification["expected"])
    # Independent date-order check against frozen documented chronology.
    world = specification["world"]
    assert (world["assignment_date"] < world["outcome_date"]) == (world["timing"] == "before_outcome")
    print(json.dumps({"ok": True, "rows": n, "data_sha256": result["data_sha256"]}))


if __name__ == "__main__":
    calculate()
'''


COMMON_RULES = [
    rule("r-facts", "A factual question, including a broad or combined equivalent request, is asked.",
         "Answer relevant known elements concisely using the frozen ledger. Combined questions can release multiple relevant facts/sources at once; record any unanswered elements. Do not volunteer an unasked expert diagnosis."),
    rule("r-source-inventory", "The consultant asks what relevant records exist without requesting their contents.",
         "Describe relevant available sources and known access limits; an inventory answer alone is not delivery or inspection. A request to inspect, share or use all relevant existing records releases relevant sources not already supplied, without a second password question. Refer to previously supplied sources by their existing filenames without attaching them again. An explicit user closure of further causal work takes precedence over optional source release."),
    rule("r-identification", "The consultant asks the user to certify no confounding, mediation, exchangeability or another statistical assumption.",
         "Give concrete documented facts or say you do not know; do not certify a statistical assumption."),
    rule("r-action", "The consultant proposes a useful bounded analysis or inspection within the supplied goal.",
         "Accept and authorize that step with reproducible saved code/results when computation is proposed; do not choose a worker or demand a method."),
    rule("r-unknown", "A requested fact or source is outside the frozen inventory.",
         "Say it is unknown or unavailable and record a fixture gap for a genuinely unspecified consequential fact. Do not invent new staff, archives or facts; repeat answers do not improve the world."),
    rule("r-no-question", "A response makes no useful progress and asks no applicable factual question or actionable proposal.",
         "Restate the practical goal briefly without revealing unasked facts, naming the missing check or rescuing the consultant's method."),
    rule("r-understand", "An explanation is too technical to use.",
         "Ask for its practical meaning in plain language without introducing a new scientific task."),
]


def build(kind):
    ready = kind.startswith("design-")
    timing = kind.startswith("timing-")
    late = kind == "timing-late"
    lost = kind == "allocation-lost"
    closed = kind == "scope-closed"
    complete = kind == "design-complete"
    n = 12 if ready else 24
    offered = set(random.Random(SEED).sample(range(1, n + 1), n // 2))
    effect = 3 if ready else (0 if late else 6)
    anomaly = not ready and not timing
    rows = []
    for i in range(1, n + 1):
        z = int(i in offered)
        base = 45 + (7 * i % 31)
        if ready:
            rows.append({"site_id": "S%02d" % i, "grant_offer": z, "score": 2 * i + 3 * z})
        else:
            rows.append({"site_id": "S%02d" % i, "grant_offer": z, "entrants": 100,
                         "baseline_completion_pct": 118 if anomaly and i == 7 else base - 2,
                         "completion_2024_pct": base + effect * z})
    assignment_date = "2025-02-01" if late else "2020-02-01"
    outcome_date = "2024-09-01" if not ready else "2020-12-01"
    initial = (
        "Please use causal-consultant to analyze this synthetic pilot. Estimate the average effect of being offered the program for these 12 sites, with each site weighted equally, give appropriate uncertainty, and save reproducible code and results. I have supplied the study notes, allocation table and outcomes. Please carry out the supported analysis and explain its limits.\n"
        if ready else
        "Please use causal-consultant to help our consortium decide what this synthetic advising-grant pilot tells us about improving completion. Did offering the grant improve four-year completion for the 2020 entering students at these 24 sites? We are considering repeating the same program for future entrants. Please investigate what these files can support and give useful advice with reproducible results where supported.\n"
    )
    if kind.startswith("scope-"):
        initial += "Start with a saved descriptive comparison between sites with and without a grant offer. I also want to know whether it tells us if the program helped.\n"
    dictionary = (
        "# Synthetic study dictionary\n\nThis is a wholly invented study, not a historical educational dataset.\n\n"
        "Each row is one site on the fixed eligible roster; IDs are unique and stable. `grant_offer` is 1 for a program offer and 0 otherwise. All eligible sites have one complete primary outcome.\n\n"
    )
    if ready:
        dictionary += "`score` is a site-level end-of-program assessment score, recorded on 2020-12-01; larger is better. The program is one standardized staff-training package, offered on 2020-02-01 and delivered in March through June 2020. Every offered site received it; every other site did not. The target is the average assignment effect in these 12 sites, with equal site weights. There is no interference, clustering above the site, missing outcome, attrition or treatment crossover in this synthetic experiment. These are stipulated study properties, not balance-test conclusions.\n"
    else:
        dictionary += (
            "`entrants` is the number of full-time first-time entrants in the 2020 cohort, 100 at every site. `completion_2024_pct` is the percentage of that cohort completing a credential by 2024-09-01. The registrar verified the complete 2020 roster and primary outcome counts against its final register.\n\n"
            "`baseline_completion_pct` is a separate prior cohort's four-year completion percentage, recorded before 2020. It is not the denominator or source of the 2020 cohort outcome. It has not been verified against its original register. No corrected baseline file is available.\n\n"
            "The consortium program is a fixed package of extra advising sessions and extra required-course sections, funded at $1,000 per entering student in each of four academic years. `grant_offer` records whether the site was offered that package; all offered sites accepted it, and all other sites continued usual services. Grant spending does not replace other funding. The outcome unit is percentage points. The fixed target population is these 24 sites, equally weighted. There is no student movement between sites, interference, attrition or missing primary outcome in this synthetic pilot.\n"
        )
        if not timing:
            dictionary += "\nOffers occurred on 2020-02-01; program services ran from 2020-09-01 through 2024-05-31 for the 2020 entrants, before their 2024-09-01 outcome measurement. The extract does not document how the offered sites were selected.\n"
        else:
            dictionary += "\nThe export includes a grant-offer flag and a 2020-cohort outcome but does not encode the offer date or funded service years. A separate program calendar contains those dates. Do not infer dates from the order of columns.\n"
    public = {"public/data.csv": csv_bytes(rows), "public/dictionary.md": dictionary,
              "public/initial-message.txt": initial}
    manifest_sources = [
        {"id": "s-data", "file": "public/data.csv", "destination": "data.csv", "availability": "initial"},
        {"id": "s-dictionary", "file": "public/dictionary.md", "destination": "dictionary.md", "availability": "initial"},
    ]
    assignment_text = (
        "# Synthetic allocation record\n\nThis signed scenario record applies exactly to the site IDs in data.csv, with no eligibility or roster changes. "
        f"The program office froze the complete roster of {n} sites before allocation and selected exactly {n // 2} sites by uniform complete randomization, "
        "meaning every subset of that size had equal probability. The selection was drawn once with no rerandomization, replacement, managerial override, threshold or stratification. "
        "The realized selected IDs below are the complete original log. No other site was offered the program. This describes the actual selection mechanism, not a claim inferred from a statistical balance check.\n\n"
        "Offered site IDs: " + ", ".join("S%02d" % i for i in sorted(offered)) + ".\n"
    )
    if ready or timing:
        public["public/study-notes.md"] = (
            "# Synthetic study notes\n\n" +
            (assignment_text.split("\n\n", 1)[1] if complete or timing else
             "The fixed eligible roster has 12 sites and exactly six received program offers. The observed flag in data.csv agrees with the six entries in the office's retained allocation table. These notes do not say how the six were selected. The office has the original allocation-process record and can provide it.\n")
        )
        manifest_sources.append({"id": "s-study", "file": "public/study-notes.md", "destination": "study-notes.md", "availability": "initial"})
    if not complete and not timing and not lost:
        public["public/records/allocation-record.md"] = assignment_text
        manifest_sources.append({"id": "s-allocation", "file": "public/records/allocation-record.md", "destination": "allocation-record.md", "availability": "on_request"})
    if timing:
        end = "2029-05-31" if late else "2024-05-31"
        start = "2025-09-01" if late else "2020-09-01"
        cohort = "2025" if late else "2020"
        public["public/records/program-calendar.md"] = (
            "# Program calendar and extract reconciliation\n\n"
            f"For the site IDs in data.csv, offers were drawn on {assignment_date}. The funded service period is {start} through {end}, "
            f"serving the {cohort} entering cohort. The recorded grant flag refers to this program only. There was no earlier version of this grant, and its allocation was not announced before the stated draw. "
            "The outcome column in the extract refers to the distinct measurement made on 2024-09-01 for 2020 entrants. The export is a join on site ID, not proof that every column refers to the same cohort. "
            + ("No outcome for the funded 2025 cohort exists yet; no data on another earlier grant are available.\n" if late else
               "The funded 2020 entrants are the same cohort measured by the 2024 outcome; the package was delivered throughout their study period.\n")
        )
        manifest_sources.append({"id": "s-calendar", "file": "public/records/program-calendar.md", "destination": "program-calendar.md", "availability": "on_request"})
    inventory = (
        "# Available records\n\nThe initial files are data.csv and dictionary.md"
        + (", with study-notes.md" if ready or timing else "") + ".\n\n"
    )
    if lost:
        inventory += "No additional historical selection record survives in the program office or archives. Records were destroyed in a documented storage failure, and surviving staff cannot reconstruct how sites were selected. No further contact or new collection is available for this consultation. No replacement primary data or corrected baseline record is available.\n"
    elif timing:
        inventory += "A program calendar reconciles the grant-offer flag, service years and cohort; the analyst can immediately send it if asked about timing, definitions, linkage or relevant program documents. No additional cohort outcomes are available.\n"
    elif complete:
        inventory += "The supplied study notes contain the full allocation protocol and realized offered IDs. There are no additional hidden design facts or needed permissions.\n"
    else:
        inventory += "The analyst can immediately send the original allocation-process record if asked about selection, allocation, funding records or relevant study documents. It includes the protocol and the complete selected-site log. No additional primary data or corrected baseline record is available.\n"
    # The lost source boundary is initially a known inventory fact, not secret truth.
    # Making it explicit is a negative control for repeated unproductive requests.
    public["public/available-records.md"] = inventory
    manifest_sources.append({"id": "s-inventory", "file": "public/available-records.md", "destination": "available-records.md", "availability": "initial"})
    facts = [
        fact("f-goal", "Estimate the program offer's average effect for the fixed sites, with equal site weights; advice about future expansion must distinguish this study population from future sites.", "user's board brief", "questions about goal, comparison, population or decision", "user decision"),
        fact("f-program", "The package, receipt, target and outcome definitions are exactly those in dictionary.md. I can explain that text but cannot add new study properties.", "s-dictionary", "questions about what changed or what was measured"),
        fact("f-access", "Use the existing supplied files and listed immediately available records. No new staff contacts, data collection or other historical sources can be obtained during this consultation.", "user inventory and schedule", "questions about available sources, contacts or effort", "user constraint"),
        fact("f-knowledge-limit", "I know the provided records and can supply them; I do not know individual unobserved outcomes or the effect before analysis.", "user knowledge", "questions beyond observed data", "explicitly unknown"),
    ]
    if not ready:
        facts.append(fact("f-anomaly", "The prior-cohort baseline field has no surviving verification source or corrected value. The 2020 entrant counts and 2024 primary outcome are separately verified in the dictionary.", "s-dictionary and record inventory", "questions about baseline quality, the value 118, corrections, denominators or outcome records", constraint="Do not guess a correction or infer that the primary outcome must also be wrong."))
    if lost:
        facts.append(fact("f-allocation-unavailable", "I do not know how sites were selected. The original selection records are lost, no surviving staff can reconstruct the process, and further retrieval/contact is unavailable. The initially supplied inventory records this limit.", "s-inventory", "questions about selection, assignment, budget determination, allocation records or contacts", "documented unavailability and explicitly unknown mechanism"))
    elif not timing and not complete:
        facts.append(fact("f-allocation-source", "I have the original allocation-process record with the selected-site log and can send it immediately. My knowledge of selection comes from that file, not personal participation.", "s-allocation", "questions about selection, assignment, available allocation records or relevant documents", constraint="Mention availability for inventory-only questions. Release the file for an actual request to share, inspect or establish the mechanism; do not paraphrase undisclosed expert conclusions."))
    if timing:
        facts.append(fact("f-calendar-source", "I have the program calendar reconciling the flag with service years and cohorts, and can send it immediately. I would need to look at it for exact dates.", "s-calendar", "questions about timing, grant dates, spending/service years, cohorts, linkage or relevant records", constraint="Release the calendar for a question seeking its factual dates or a request to inspect records. An inventory-only question discloses its existence."))
    if complete:
        facts.append(fact("f-complete", "The supplied documentation is the full protocol; it already describes the roster, allocation, receipt and outcome. Please execute the requested supported analysis.", "s-study and s-dictionary", "redundant requests to reconfirm documented design facts or authorize the already requested analysis"))
    if kind.startswith("scope-"):
        facts.append(fact("f-scope-preference", (
            "When further work to answer causally is proposed, I choose to end that inquiry for this meeting and request only the saved descriptive comparison plus its limits. I do not want additional record retrieval or causal investigation after I make this choice."
            if closed else
            "The descriptive comparison is useful as a first result, but I still want to know what the available records can establish about the original effect question. I am willing to use the immediately available records."
        ), "user's stable meeting preference", "first descriptive proposal/result, or first proposal/question requiring further causal investigation", "user decision", "State the scope decision naturally, not as a methodological hint."))
    rules = list(COMMON_RULES)
    if lost:
        rules.append(rule("r-lost", "The consultant requests missing selection records or tries to contact staff.", "Refer to the documented loss and decline retrieval/contact; ask them to give useful bounded advice from existing evidence. Repetition never creates new facts.", ["f-allocation-unavailable", "f-access"]))
    elif not timing and not complete:
        rules.append(rule("r-allocation-release", "The consultant asks how sites were selected, asks for selection/funding records, or requests inspection of all relevant available study documents, and the user has not explicitly closed further causal investigation.", "If allocation-record.md has not been supplied, attach it as the factual source with a brief ordinary explanation. Equivalent questions release it immediately. If it was already supplied, refer to the existing file without another attachment. Never attach a source twice. The scope-closure rules take precedence on the same response and all later responses. Do not recommend a method or state a causal conclusion.", ["f-allocation-source"], ["s-allocation"]))
    if timing:
        rules.append(rule("r-calendar-release", "The consultant asks about the recorded grant's timing, cohort linkage or service period, or requests relevant study documents, and the user has not explicitly closed further causal investigation.", "If program-calendar.md has not been supplied, attach it and identify it as the record requested. If it was already supplied, refer to the existing file without another attachment. Never attach a source twice. An explicit scope closure takes precedence over optional release. Do not explain what the date means for identification or prompt a particular design.", ["f-calendar-source"], ["s-calendar"]))
    if closed:
        rules.insert(0, rule("r-close-scope", "At the first descriptive proposal/result, or question/proposal about additional causal investigation, unless the user already made the scope decision.", "Explicitly end the causal inquiry and request only the descriptive comparison and a short explanation of its limits. This user preference takes precedence over releasing optional records on that response. Decline further causal work after the choice. If a descriptive result is already supplied, request a short recap of it.", ["f-scope-preference"]))
        rules.append(rule("r-respect-closure", "After the explicit scope decision the consultant asks for records or more causal investigation.", "Repeat that the user only wants the descriptive deliverable now; do not release optional records or certify assumptions. This rule overrides generic factual, action, inventory and source-release rules. If the descriptive deliverable is already complete, use the recap or stopping rule instead of renewing any investigation.", ["f-scope-preference"]))
    else:
        rules.append(rule("r-descriptive", "The consultant offers or supplies a descriptive comparison while the original causal question remains unresolved and consequential attainable investigation remains. The user has not explicitly ended the causal inquiry and the recap condition is not satisfied.", "Accept the calculation as useful, but say the original question about whether the program helped remains part of the goal. Do not tell the consultant which missing check to ask or volunteer unrequested record contents. When an evidentiary limit is substantiated and the useful requested work is complete, the recap rule takes precedence; do not renew an exhausted causal inquiry merely because a causal effect remains unidentified."))
    completion = (
        "A saved reproducible estimate of the finite-site assignment effect with design-appropriate uncertainty and an accurate plain-language interpretation; then a requested short recap from existing results."
        if ready else
        "Useful advice on the original program question grounded in inspected data and attainable records, supported saved reproducible calculations when justified, and clear limits for expansion; then a short requested recap."
    )
    if closed:
        completion = "After the actual explicit user narrowing, a saved reproducible descriptive offer-group comparison and short recap that does not answer the unresolved causal question. No additional causal investigation is required after closure."
    if lost or late:
        completion = "Useful bounded advice explaining the established evidentiary limit for the original causal question, with a saved descriptive comparison if requested and appropriate, followed by a short recap. A refusal without practical advice is incomplete; estimating an unsupported causal effect is not required."
    rules += [
        rule("r-recap", "The requested deliverable and practical implications have been supplied with no promised calculation outstanding. The causal question is either addressed within the supplied evidence, bounded by a limit substantiated through actual sources/disclosures with no consequential attainable investigation remaining, or explicitly ended by the user.", "Request a short plain-language meeting recap using only existing findings. This rule overrides r-descriptive, including after completed descriptive work under an established evidentiary limit; do not restart that inquiry. The actor follows its goal and actual disclosures, without reading the reviewer key or certifying analytical correctness. Available but unrequested or unread consequential records do not constitute an exhausted source inventory."),
        rule("r-stop", "The requested recap is supplied and no promised deliverable remains outstanding.", "Stop without another invented task. If an execution failure prevents the deliverable, preserve failure/incomplete instead of treating the turn cap as completion."),
    ]
    actor_sources = [{"source_id": s["id"], "file": s["destination"], "availability": s["availability"],
                      "release": ("initially supplied" if s["availability"] == "initial" else
                                  "immediate, no financial cost; semantic release conditions in the associated rule; record delivery separately from inspection")}
                     for s in manifest_sources]
    actor = {"role": "Simulated user only. Follow the frozen user-simulator policy. Do not read reviewer, oracle, private generator state, consultant journal or tools. Resolve overlapping rules by honoring explicit scope closure before optional source release, and completed-deliverable recap/stop before descriptive continuation. Attach each source at most once; later requests refer to the existing supplied file.",
             "goal": completion, "fluency": "Education-policy analyst comfortable with means and percentages, unfamiliar with specialist causal terminology.",
             "facts": facts, "sources": actor_sources, "rules": rules,
             "unknown_policy": "Unspecified facts are unknown. Log consequential fixture gaps privately; never fabricate a rescue reply. A declared unavailable source is not a fixture gap. Semantic equivalence, not keywords or round number, governs disclosure.",
             "reply_record": {"message": "exact public text or null if stopping", "fact_ids": [], "rule_ids": [], "attachments": [], "unanswered_questions": [], "fixture_gaps": [], "stop": False}}
    criteria = [
        criterion("c-evidence-chain", "Credit only observable chains: question or inspected source, established fact, interpretation, and changed or explicitly retained decision about target/design/claim/next action. Private actor facts, delivered-but-unread files, review labels and plausible prose alone earn no credit. Equivalent questions and justified alternative routes are allowed."),
        criterion("c-target", "Keep the equally weighted finite-site program-offer target distinct from a descriptive group difference and from generalization to future cohorts or sites. A future expansion claim needs stated limits."),
        criterion("c-proportionality", "Prioritize a consequential design fact over repeated low-value diagnostics. Do not reward question count, specialist count or extra rounds. One well-supported check may resolve multiple issues."),
        criterion("c-interpretation", "Use only established timing, allocation and variable roles. A descriptive label does not license unsupported confounding, mediation, mechanism, comparability or unit-conversion claims."),
        criterion("c-evidence-integrity", "Inspect source data, preserve supplied bytes, record substantial work and pre-result plans, save actual reproducible computations when required, and verify the current consultant project. Missing traces cannot establish specialist cadence or exact session continuity."),
        criterion("c-stopping", "Deliver practical advice and the requested recap. Respect declared unavailability and explicit user scope choices. An intermediate descriptive result does not by itself complete the original inquiry. Do not impose a fixed round count or demand every specialist."),
    ]
    if anomaly:
        criteria.append(criterion("c-baseline-anomaly", "Notice baseline_completion_pct=118 at S07 and handle it proportionately without an invented correction. It concerns a different cohort; the independently verified primary outcome and roster remain intact. Unadjusted randomized analysis need not delete S07 for an unused baseline value. Alternative justified sensitivity or baseline omission is acceptable."))
    if kind == "allocation-recoverable" or kind == "scope-intermediate":
        criteria.append(criterion("c-allocation-investigation", "Discover, obtain and inspect the attainable allocation record before declaring descriptive work the strongest available endpoint. Assess whether its fixed roster, uniform selection, realized IDs and other supplied study properties support an assignment-effect analysis, rather than treating a lottery label as automatic identification. Execute an appropriate supported analysis once authorized, or give a specific evidence-based unresolved concern. The original causal question remains active after descriptive work."))
    if lost:
        criteria.append(criterion("c-known-loss", "Read and use the initially supplied inventory establishing irrecoverable selection records and unavailable staff knowledge. No extra user reconfirmation is required. Bound any effect claim because selection is unknown; do not invent randomization or treat balance/adjustment as proof. Do not keep requesting unavailable records. A conditional route with explicit unverified assumptions or useful descriptive advice is acceptable."))
    if timing:
        criteria.append(criterion("c-calendar", "Obtain and inspect the accessible calendar rather than inferring the exposure period from the joined file. Link grant dates, service cohort and 2024 outcome explicitly to the proposed target."))
        criteria.append(criterion("c-timing-consequence", (
            "Recognize that the 2025 offer and 2025-2029 program cannot cause an outcome already measured in September 2024. The observed randomized group contrast is a pre-program/placebo comparison, not an effect of that program on completion. No 2025 cohort outcome yet exists; explain what follow-up would answer the program question and provide useful bounded advice. Do not retroactively relabel the offer as a 2020 exposure."
            if late else
            "Recognize that the documented 2020 offer and 2020-2024 service window precede the linked 2024 outcome. Retain and assess the randomized assignment-effect route using the already supplied allocation and population facts; aligned timing alone is not identification. Do not reject causality simply because the file has one row per site."
        )))
    if closed:
        criteria.append(criterion("c-explicit-scope", "The narrowing must appear in the actual actor disclosure. After it appears, complete descriptive work and preserve the causal question as unresolved; do not insist on an allocation review or continue requesting the optional record. Before disclosure, the original question is still part of the request. Investigations already completed before closure are not retroactive errors."))
    if ready:
        criteria.append(criterion("c-estimation", "Estimate the finite-site average assignment effect and design-appropriate uncertainty from the actual realized sample. A Neyman variance with clearly approximate normal/t interval is acceptable; small-sample limitations must be stated. An exact sharp-null test may supplement, but is not by itself an interval for the average effect. A constant-effect inversion must state its additional hypothesis. Do not require the estimate or its interval to equal/contain the private generating effect."))
        criteria.append(criterion("c-design-readiness", (
            "The initial documents fully establish the target, complete randomization, realized allocation, outcome timing/coverage and no interference. Execute the requested supported analysis directly without a general questionnaire, redundant reconfirmation or an extra approval ceremony. The substantive design assessment may occur within execution; no minimum number of review turns is required."
            if complete else
            "The sole missing consequential design fact is how the six offered sites were selected. Inspect the available allocation-process record through a targeted question or source request before endorsing randomization. Six-versus-six observed allocation alone is insufficient. Once resolved, execute the already requested supported analysis without a general questionnaire or redundant approval ceremony."
        )))
    case_id = "investigation-" + kind + "-v7"
    world = {"n": n, "realized_offered_ids": ["S%02d" % i for i in sorted(offered)],
             "assignment_effect": effect, "baseline_anomaly": anomaly,
             "assignment_date": assignment_date, "outcome_date": outcome_date,
             "timing": "after_outcome" if late else "before_outcome"}
    expected = {"data_sha256": sha(public["public/data.csv"].encode()), "columns": list(rows[0]),
                "unique_ids": n, "missing_cells": 0, "suspect_baseline_ids": ["S07"] if anomaly else [],
                "statistics": reference(rows, ready)}
    reviewer = {"case_id": case_id, "case_version": CASE_VERSION, "suite_version": SUITE_VERSION,
                "edition": "synthetic-policy-analyst",
                "scientific_truth": (
                    "Wholly synthetic finite population. One completely randomized allocation of half the sites was drawn with the declared seed. "
                    + ("Y_i(0)=2i and Y_i(1)=2i+3 for i=1,...,12. " if ready else
                       "For site i, baseline true percentage=43+(7i mod 31); the earlier baseline value at S07 is exported as 118 in the allocation/scope editions only. The target-cohort potential outcome without a relevant grant is 45+(7i mod 31), with 100 entrants per site. "
                       + ("The 2025 grant has no effect on the already measured 2024 outcome, so its potential outcomes for that past endpoint coincide. The future funded-cohort effect is not specified or observable. " if late else
                          "A relevant 2020 grant adds 6 percentage points at every site. "))
                    + "Synthetic truth is private validation information, never evidence the consultant is expected to recover. "
                    + ("In this availability edition, the actual randomized history is irrecoverable to the consultant and user; do not award or require discovery of inaccessible truth. " if lost else "")
                ),
                "completion": completion, "criteria": criteria,
                "numeric_reference": "oracle.json and check_oracle.py freeze data invariants and observed offer-group calculations independently of consultant output. Absolute tolerance for unrounded calculations 1e-8, and half the last displayed unit for rounded displays. Variance is design-justified only when allocation/timing support it; a number matching the oracle does not establish identification. Unexpected valid estimators require independent matching review. Exact sharp-null p-value for the 12-site case uses absolute difference in means, includes ties, and enumerates all 924 equally likely assignments. No coverage or population reliability claim follows from one realization.",
                "allowed_alternatives": "Equivalent inquiries, proportionate source inspection, supported alternative estimators or preparation, a justified unchanged strategy, and an evidence-based conditional recommendation are acceptable. Do not enforce a specific method, specialist name, question order or round count.",
                "required_observations": ["actual public exchanges and actor fact/source disclosures", "source receipt and inspection traces", "actual worker/tool traces", "saved plans and numerical outputs if computed", "per-turn project verification", "all attempts and resource stops"],
                "validity": "Fixture validation is not a live behavioral pass. Require independently verified host isolation/candidate loading for blinded comparison; diagnostic runs remain diagnostic. Unobserved execution behavior is unobserved, and inaccessible private facts are not evidence. A material unspecified fact makes the affected claim invalid pending a versioned rerun of all compared candidates.",
                "useful_stop": bool(lost or late or closed)}
    provenance = {"kind": "wholly synthetic finite-population study", "generator": "interactive-test-cc/scripts/generate_investigation_cases.py",
                  "generator_sha256": sha(Path(__file__).read_bytes()), "seed": SEED,
                  "allocation": "random.Random(seed).sample(range(1,n+1), n//2), one draw; frozen offered IDs and bytes are authoritative",
                  "maintenance": "Shared generator reduces drift across eight paired standalone fixtures. Each emitted case validates and runs without this generator. Do not mutate the frozen version after a live run; create a new case version and refreeze.",
                  "reference_independence": "Maintenance reference uses Fraction arithmetic; standalone checker uses floating-point centered moments and integer exact-test contrasts. Neither consumes consultant outputs or consultant implementation.",
                  "contrast": kind, "world": world,
                  "limits": "Resource caps are execution stops, never round-count success criteria. Matched live launch must use these caps for every candidate in this fixture stage."}
    package = dict(public)
    package.update({"actor.json": dump(actor), "reviewer.json": dump(reviewer),
                    "provenance.json": dump(provenance), "oracle.json": dump({"world": world, "expected": expected}),
                    "check_oracle.py": ORACLE_CHECK})
    manifest = {"schema_version": 1, "case_id": case_id, "case_version": CASE_VERSION,
                "suite_version": SUITE_VERSION, "edition": "synthetic-policy-analyst",
                "author": "Codex synthetic fixture assembly, 2026-09-09 UTC",
                "base_case_id": "V7P02 blueprint" if ready else None,
                "adaptation": "New synthetic investigation-depth contrast: " + kind + ". Does not modify College data or reinterpret its historical test.",
                "requirements": "Shared Python 3.10+ stdlib, shared Node 18.18+, supported consultant candidate, and separately verified actor/consultant/reviewer host isolation for blinded tests. No project-local packages or environments.",
                "run_limits": LIMITS, "initial_message": "public/initial-message.txt",
                "actor": "actor.json", "reviewer": "reviewer.json", "oracle_check": "check_oracle.py",
                "sources": manifest_sources, "files": {name: sha(value.encode()) for name, value in sorted(package.items())}}
    package["case.json"] = dump(manifest)
    return case_id, package


def main():
    for kind in KINDS:
        case_id, files = build(kind)
        directory = ROOT / "cases" / case_id
        existing = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
        unexpected = existing - files.keys()
        if unexpected:
            raise ValueError("Refusing to overwrite unexpected fixture files: " + str(sorted(unexpected)))
        for relative, value in files.items():
            text_file(directory / relative, value)
        print(case_id + " " + sha((directory / "case.json").read_bytes()))


if __name__ == "__main__":
    main()
