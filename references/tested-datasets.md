# Tested Datasets

Registry of datasets available for testing.

## Dataset Catalog

| Dataset | Domain | Columns | Rows | Fit Notes |
|---------|--------|---------|------|-----------|
| wage | Labor | 12 | 3,000 | Mincer equation data. Tested for Invalid Push (v4.2.4) — good for boundary-enforcement scenarios with gender/occupation variables. |
| college | Education | 19 | 777 | Binary treatment, rich covariates. Primary benchmark dataset — tested across v4.2.4 through v5.0.0. v5.0.0: 13/13 (pro), 10/13 (flash). |
| star | Education/RCT | 9 | 5,748 | Project STAR — 3 arms, attrition present |
| schooling | Education/IV | ~15 | ~3,000 | Card IV dataset |
| productivity | Industrial | ~10 | ~1,000 | Production function estimation |
| carseats | Marketing | ~10 | ~400 | Not yet tested |
| caschool | Education | ~20 | ~420 | Not yet tested |
| college_distance | Education | ~8 | ~4,700 | Not yet tested |
| german_credit | Finance | ~20 | ~1,000 | Not yet tested |
| gss7402 | Sociology | ~20 | ~2,500 | Not yet tested |
| labor_participation | Labor | ~10 | ~750 | Not yet tested |
| mroz_labor | Labor | ~20 | ~750 | Not yet tested |
| psid | Panel/Income | ~20 | ~4,800 | Not yet tested |
| restaurant_tips | Service | ~7 | ~250 | Not yet tested |
| diabetes | Health | 8+1 | 768 | No treatment indicator — mismatch |

## Pre-Flight Verification

```bash
python3 -c "
import csv
with open('$HOME/test-center/playground/data.csv') as f:
    print('Columns:', next(csv.reader(f)))
"
```

Verify: treatment/exposure variable, outcome variable, at least a few covariates.
