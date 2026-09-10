"""Standalone scientific fixture checks, independent of the fixture generator.

Executed from a frozen problem or a composed case. Standard library only; never
imports the generator or consultant. Private outputs are not actor materials.
"""
import csv
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def rows(name):
    with (ROOT / "public" / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def close(actual, expected, label="reference"):
    if isinstance(expected, dict):
        assert set(actual) == set(expected), (label, "fields", set(actual), set(expected))
        for key in expected:
            close(actual[key], expected[key], label + "." + key)
    elif isinstance(expected, list):
        assert len(actual) == len(expected), (label, "length")
        for index, (a, e) in enumerate(zip(actual, expected)):
            close(a, e, label + "." + str(index))
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-8), (label, actual, expected)
    else:
        assert actual == expected, (label, actual, expected)


def check_design():
    data = rows("centers.csv")
    planning = read_json("public/planning-inputs.json")
    assert {r["center_id"] for r in data} == {"C%02d" % i for i in range(1, 25)}
    assert all(int(r["planned_eligible_learners"]) == 40 for r in data)
    assert all(int(r["historical_mean_score"]) == 48 + (7 * int(r["center_id"][1:]) % 13) for r in data)
    retained = planning["learners_per_center"] * (1 - planning["anticipated_attrition_fraction"])
    effects = {str(icc): 1 + (retained - 1) * icc for icc in planning["icc_assumptions"]}
    z = statistics.NormalDist().inv_cdf(1 - planning["two_sided_alpha"] / 2) + statistics.NormalDist().inv_cdf(planning["power_target"])
    # Two equally sized arms; independently reconstruct the normal approximation.
    effective_arm_size = planning["centers_offered"] * retained / effects["0.05"]
    mde = z * planning["outcome_sd_assumption"] * math.sqrt(2 / effective_arm_size)
    return {"centers": len(data), "eligible_learners": sum(int(r["planned_eligible_learners"]) for r in data),
        "centers_per_region": dict(Counter(r["region"] for r in data)), "retained_per_center_assumption": retained,
        "retained_total_assumption": retained * len(data), "design_effects_at_retained_size": effects,
        "normal_approx_mde_at_icc_005": mde}


def check_did():
    data, roster = rows("panel.csv"), rows("site-roster.csv")
    target = {r["site_id"]: r for r in roster}
    assert len(target) == len(roster) == 120
    assert set(target) == {"S%03d" % i for i in range(1, 121)}
    by_site = {key: {} for key in target}
    for r in data:
        sid, year = r["site_id"], int(r["year"])
        assert year not in by_site[sid], "duplicate site-year"
        assert r["readiness_high"] == target[sid]["readiness_high"]
        assert r["adopted_2025"] == target[sid]["adopted_2025"]
        score = float(r["mean_skill_score"])
        assert 0 <= score <= 100
        by_site[sid][year] = score
    assert all(set(ys) == {2022, 2023, 2024, 2025, 2026} for ys in by_site.values())
    changes = {sid: (ys[2025] + ys[2026]) / 2 - ys[2024] for sid, ys in by_site.items()}
    strata = {}
    for x in ("0", "1"):
        ids = [[sid for sid, r in target.items() if r["readiness_high"] == x and r["adopted_2025"] == str(d)] for d in (0, 1)]
        groups = [[changes[sid] for sid in group] for group in ids]
        placebo = [[by_site[sid][2024] - by_site[sid][2023] for sid in group] for group in ids]
        strata[x] = {"control_n": len(ids[0]), "adopter_n": len(ids[1]),
            "control_change": statistics.mean(groups[0]), "adopter_change": statistics.mean(groups[1]),
            "did": statistics.mean(groups[1]) - statistics.mean(groups[0]),
            "variance": statistics.variance(groups[0]) / len(groups[0]) + statistics.variance(groups[1]) / len(groups[1]),
            "preperiod_placebo": statistics.mean(placebo[1]) - statistics.mean(placebo[0])}
    n_adopt = sum(int(r["adopted_2025"]) for r in roster)
    target_weights = {x: sum(r["readiness_high"] == x for r in roster) / len(roster) for x in strata}
    adopter_weights = {x: sum(r["readiness_high"] == x and r["adopted_2025"] == "1" for r in roster) / n_adopt for x in strata}
    assert target_weights == {"0": 0.5, "1": 0.5}
    assert adopter_weights == {"0": 0.25, "1": 0.75}
    return {"sites": len(roster), "rows": len(data), "adopters": n_adopt,
        "years": sorted({int(r["year"]) for r in data}), "strata": strata,
        "standardized_ate_reference": sum(target_weights[x] * strata[x]["did"] for x in strata),
        "standardized_ate_reference_variance": sum(target_weights[x] ** 2 * strata[x]["variance"] for x in strata),
        "att_reference": sum(adopter_weights[x] * strata[x]["did"] for x in strata),
        "att_reference_variance": sum(adopter_weights[x] ** 2 * strata[x]["variance"] for x in strata),
        "unadjusted_did": statistics.mean(changes[sid] for sid in target if target[sid]["adopted_2025"] == "1") - statistics.mean(changes[sid] for sid in target if target[sid]["adopted_2025"] == "0")}


def check_cate():
    partitions = {split: rows(split + ".csv") for split in ("development", "evaluation")}
    ids = {split: {r["learner_id"] for r in data} for split, data in partitions.items()}
    assert not (ids["development"] & ids["evaluation"])
    assert ids["development"] | ids["evaluation"] == {"L%04d" % i for i in range(1, 2401)}
    output = {"total_learners": 2400, "partitions": {}}
    tau_cells, selected_tau = [], []
    for h in (0, 1):
        for b in (0, 1):
            for s in (-0.5, 0.5):
                tau = -1 + 4 * h + 2 * b + s
                tau_cells.append(tau)
                if h == 1 and (b == 1 or s == 0.5):
                    selected_tau.append(tau)
    assert sorted(selected_tau) == sorted(tau_cells)[-3:]
    output["generating_ate"] = statistics.mean(tau_cells)
    output["benchmark_policy_target_fraction"] = len(selected_tau) / len(tau_cells)
    output["benchmark_policy_generating_net_gain"] = sum(t - 2 for t in selected_tau) / len(tau_cells)
    for split, data in partitions.items():
        assert len(ids[split]) == len(data)
        cells = {}
        scores, score_cells, selected = [], {}, 0
        for r in data:
            assert set(r) == {"learner_id", "readiness_high", "barrier_flag", "baseline_band", "offer", "skill_gain", "engagement_week4"}
            assert r["offer"] in ("0", "1") and r["readiness_high"] in ("0", "1") and r["barrier_flag"] in ("0", "1")
            assert r["baseline_band"] in ("-0.5", "0.5")
            assert 0 <= float(r["engagement_week4"]) <= 10
            key = ",".join((r["readiness_high"], r["barrier_flag"], r["baseline_band"]))
            cells.setdefault(key, [[], []])[int(r["offer"])].append(float(r["skill_gain"]))
            pi = r["readiness_high"] == "1" and (r["barrier_flag"] == "1" or r["baseline_band"] == "0.5")
            selected += pi
            # Known assignment probability gives a fixed-rule IPW contrast.
            y, w = float(r["skill_gain"]), int(r["offer"])
            score = float(pi) * (w * y / 0.5 - (1 - w) * y / 0.5 - 2)
            scores.append(score)
            score_cells.setdefault(key, []).append(score)
        assert len(cells) == 8
        result_cells = {}
        for key, groups in cells.items():
            assert sum(map(len, groups)) == (225 if split == "development" else 75)
            assert all(len(g) > 1 for g in groups), "within-cell offer overlap"
            result_cells[key] = {"n": sum(map(len, groups)), "control_n": len(groups[0]), "offer_n": len(groups[1]),
                "control_mean": statistics.mean(groups[0]), "offer_mean": statistics.mean(groups[1]),
                "difference": statistics.mean(groups[1]) - statistics.mean(groups[0])}
        assert selected / len(data) == 0.375
        output["partitions"][split] = {"n": len(data), "offer_n": sum(int(r["offer"]) for r in data), "cells": result_cells,
            "fixed_benchmark_ipw_net_gain": statistics.mean(scores),
            "fixed_benchmark_stratified_score_se": math.sqrt(sum((1 / len(score_cells)) ** 2 * statistics.variance(g) / len(g) for g in score_cells.values())),
            "fixed_benchmark_iid_score_se": statistics.stdev(scores) / math.sqrt(len(scores))}
    return output


def check_edge():
    data, roster = rows("extract.csv"), rows("participant-roster.csv")
    ids = {r["participant_id"] for r in roster}
    assert ids == {"P%03d" % i for i in range(1, 121)} and len(roster) == 120
    unique, duplicates = {}, []
    for r in data:
        sid = r["participant_id"]
        assert sid in ids
        if sid in unique:
            assert unique[sid] == r, "conflicting duplicate cannot be silently discarded"
            duplicates.append(sid)
        else:
            unique[sid] = r
    assert set(unique) == ids
    clean = list(unique.values())
    assert all(r["program_received"] == "1" for r in clean)
    assert all(r["recorded_program_start"] < r["outcome_window_end"] for r in clean)
    assert all(r["completed_12weeks"] in ("", "0", "1") for r in clean)
    assert all(r["baseline_score"] == "" or 0 <= float(r["baseline_score"]) <= 100 for r in clean)
    baseline_missing = sum(r["baseline_score"] == "" for r in clean)
    outcome_missing = sum(r["completed_12weeks"] == "" for r in clean)
    successes = sum(r["completed_12weeks"] == "1" for r in clean)
    failures = sum(r["completed_12weeks"] == "0" for r in clean)
    n = len(clean)
    return {"export_rows": len(data), "unique_people": n, "duplicate_rows": len(duplicates),
        "duplicate_ids": sorted(duplicates), "baseline_missing": baseline_missing,
        "baseline_missing_fraction": baseline_missing / n, "outcome_missing": outcome_missing,
        "outcome_missing_fraction": outcome_missing / n, "observed_outcomes": successes + failures,
        "observed_successes": successes, "observed_failures": failures,
        "observed_success_fraction": successes / (successes + failures),
        "cohort_success_bounds": [successes / n, (successes + outcome_missing) / n],
        "untreated_people": sum(r["program_received"] == "0" for r in clean)}


def main():
    problem = read_json("problem.json")
    oracle = read_json("oracle.json")
    identity = problem["problem_id"]
    assert oracle["problem_id"] == identity
    for name, expected_hash in problem["files"].items():
        actual_hash = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (name, "frozen bytes changed")
    functions = {"study-design": check_design, "observational-did": check_did,
                 "cate-policy": check_cate, "data-quality-edge": check_edge}
    actual = functions[identity]()
    close(actual, oracle["expected"])
    print(json.dumps({"ok": True, "problem_id": identity, "checks": "independent source arithmetic, scientific invariants and frozen bytes", "files": len(problem["files"])}))


if __name__ == "__main__":
    main()
