"""Independent descriptive checks, with no consultant output as input. Standard library only."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def describe(rows):
    n = len(rows)
    x = [float(row["Expend"]) / 1000 for row in rows]
    y = [float(row["Grad.Rate"]) for row in rows]
    mx, my = math.fsum(x) / n, math.fsum(y) / n
    xx = math.fsum((v - mx) ** 2 for v in x)
    yy = math.fsum((v - my) ** 2 for v in y)
    xy = math.fsum((a - mx) * (b - my) for a, b in zip(x, y))
    slope = xy / xx
    intercept = my - slope * mx
    residual = [b - intercept - slope * a for a, b in zip(x, y)]
    # HC3 sandwich slope component with intercept, using centered x.
    hc3 = math.sqrt(math.fsum(((a - mx) * e / (1 - 1 / n - (a - mx) ** 2 / xx)) ** 2
                              for a, e in zip(x, residual)) / xx ** 2)
    return {"n": n, "mean_expend": mx * 1000, "mean_grad_rate": my,
            "ols_intercept": intercept, "ols_slope_pp_per_1000": slope,
            "ols_hc3_se_slope": hc3, "pearson_r": xy / math.sqrt(xx * yy),
            "ols_hc3_normal_95_interval": [slope - 1.959963984540054 * hc3, slope + 1.959963984540054 * hc3]}


def calculate():
    data = ROOT / "public/data.csv"
    with data.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        columns = len(reader.fieldnames)
    return {"data_sha256": hashlib.sha256(data.read_bytes()).hexdigest(), "rows": len(rows),
            "columns": columns, "unique_ids": len({row["rownames"] for row in rows}),
            "missing_cells": sum(value == "" for row in rows for value in row.values()),
            "suspect_outcomes": [{"institution": row["rownames"], "Grad.Rate": float(row["Grad.Rate"])}
                                 for row in rows if not 0 <= float(row["Grad.Rate"]) <= 100],
            "all": describe(rows),
            "valid_outcome": describe([row for row in rows if 0 <= float(row["Grad.Rate"]) <= 100])}


def check(actual, expected, path="oracle"):
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ValueError(path + ": fields differ")
        for key in expected:
            check(actual[key], expected[key], path + "." + key)
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ValueError(path + ": lengths differ")
        for i, (a, b) in enumerate(zip(actual, expected)):
            check(a, b, path + "." + str(i))
    elif isinstance(expected, float):
        if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-8):
            raise ValueError(path + ": numerical mismatch")
    elif actual != expected:
        raise ValueError(path + ": value mismatch")


if __name__ == "__main__":
    expected = json.loads((ROOT / "oracle.json").read_text(encoding="utf-8"))
    check(calculate(), expected)
    print(json.dumps({"ok": True, "rows": expected["rows"], "data_sha256": expected["data_sha256"]}))
