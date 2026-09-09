"""Standalone fixture self-check. No model outputs, generator import or packages."""
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
