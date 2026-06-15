# Tested Datasets

Registry of datasets tested with causal-consultant, including fit notes.

## v4.2.4 Batch (2026-06-15)

| Dataset | Domain | Variables | Fit | Notes |
|---------|--------|-----------|-----|-------|
| wage | Labor economics | lwage, educ, exper, demographics | ✅ Good | Classic Mincer equation data |
| college | Education | college attendance, wages, family background, test scores | ✅ Good | Binary treatment, rich covariates |
| diabetes | Health | 8 baseline measurements, binary Outcome | ❌ Mismatch | Pima Indians — no treatment indicator, no progression score. Assistant correctly identified limitation. |
| schooling | Education / IV | education, log wage, college proximity, family, IQ | ✅ Good | Classic Card IV dataset. Deep analysis sessions exceed 500s/turn. |
| star | Education / RCT | test scores, class type, demographics | ✅ Good | Project STAR — 3 treatment arms. Attrition present. |
| productivity | Industrial org | firm output, labor, capital, intermediate inputs | ✅ Good | Production function estimation. |
| carseats | Marketing | Sales, price, advertising, shelf location | Not tested | |
| caschool | Education | Test scores, student-teacher ratio, demographics | Not tested | |
| college_distance | Education | Distance to college, attendance, demographics | Not tested | |
| german_credit | Finance | Credit risk, demographic indicators | Not tested | No CSV as of 2026-06-15 |
| gss7402 | Sociology | Survey data, demographics, attitudes | Not tested | |
| labor_participation | Labor | Labor force participation, demographics | Not tested | |
| mroz_labor | Labor | Labor supply, wages, demographics | Not tested | |
| psid | Panel / Income | Panel income dynamics, demographics | Not tested | |
| restaurant_tips | Service | Tips, bill amount, party size, demographics | Not tested | |

## Pre-Flight Verification

Before starting any session with data, run a 5-second CSV peek:

```bash
python3 -c "
import csv
with open('$HOME/test-center/playground/data.csv') as f:
    print('Columns:', next(csv.reader(f)))
"
```

Verify the dataset has:
- A treatment/exposure variable matching the domain
- An outcome variable
- At least a few covariates

If mismatched (like Pima Indians for a treatment effect question), either:
- Switch datasets
- Pivot the conversation to a valid question the data CAN answer
- Note the mismatch in the summary and continue (the assistant's handling
  of the mismatch is itself informative)
