"""Freeze two real-data persona cases. No network, legacy histories or model calls.

The prepared input bytes are preserved. Source reconciliation was performed
separately against public exports and Card's primary archive on 2026-09-09.
The generated independent checker imports neither this module nor a package.
"""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import NormalDist, fmean

ROOT = Path(__file__).resolve().parents[1]
VERSION, SUITE = "1.0.0", "7.0.4"
LIMITS = {"consultant_turns": 24, "active_seconds": 14400, "elapsed_seconds": 21600}
CASES = {
    "persona-domain-star-v7": ("star", "cooperative-domain-expert", "star-interference-saturation",
                               "242a74a923e70359ee66d8cf585f85b16137ee36c932f8f276149f7f319a3b73"),
    "persona-statistician-schooling-v7": ("schooling", "expert-statistician", "schooling-iv-late",
                                         "45b47f693b9f5f60f6b4c101aef86f71643bbe50d25bfa726f871642842a488e"),
}
URL_STAR = "https://search.r-project.org/CRAN/refmans/Ecdat/html/Star.html"
URL_SCHOOL = "https://search.r-project.org/CRAN/refmans/Ecdat/html/Schooling.html"
URL_KRUEGER = "https://hceconomics.uchicago.edu/sites/default/files/events/Krueger_1999_QJE_v114_n2.pdf"
URL_CARD = "https://davidcard.berkeley.edu/data_sets/proximity.zip"
URL_IV = "https://lsun20.github.io/WIRev_092218-%20corrected.pdf"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def fact(key, statement, source="user preference", certainty="known", when="initially known and when relevant"):
    return {"fact_id": key, "statement": statement, "source": source, "certainty": certainty,
            "available_when": when, "disclosure_condition": "Use only relevant elements and preserve the stated limits."}


def rule(key, condition, action, facts=(), sources=()):
    return {"rule_id": key, "condition": condition, "action": action,
            "fact_ids": list(facts), "source_ids": list(sources)}


def criterion(key, text):
    return {"id": key, "required": True, "rule": text}


def inverse2(a, b, c):
    determinant = a * c - b * b
    return [[c / determinant, -b / determinant], [-b / determinant, a / determinant]]


def star_reference(rows):
    # Aggregate within-school cross-products; checker instead centers individual rows.
    groups = {}
    for row in rows:
        groups.setdefault(row["schidkn"], []).append(row)
    answer = {}
    for outcome in ("tmathssk", "treadssk"):
        a = b = c = d = e = 0.0
        for group in groups.values():
            n = len(group)
            ns = sum(r["classk"] == "small.class" for r in group)
            na = sum(r["classk"] == "regular.with.aide" for r in group)
            total = sum(float(r[outcome]) for r in group)
            a += ns - ns * ns / n
            b -= ns * na / n
            c += na - na * na / n
            d += sum(float(r[outcome]) for r in group if r["classk"] == "small.class") - ns * total / n
            e += sum(float(r[outcome]) for r in group if r["classk"] == "regular.with.aide") - na * total / n
        bread = inverse2(a, b, c)
        beta = [bread[0][0] * d + bread[0][1] * e, bread[1][0] * d + bread[1][1] * e]
        scores = []
        for group in groups.values():
            xbar = [fmean(r["classk"] == kind for r in group) for kind in ("small.class", "regular.with.aide")]
            intercept = fmean(float(r[outcome]) for r in group) - sum(xbar[j] * beta[j] for j in range(2))
            score = [0.0, 0.0]
            for row in group:
                x = [float(row["classk"] == k) for k in ("small.class", "regular.with.aide")]
                residual = float(row[outcome]) - intercept - sum(x[j] * beta[j] for j in range(2))
                for j in range(2):
                    score[j] += (x[j] - xbar[j]) * residual
            scores.append(score)
        n, g = len(rows), len(groups)
        multiplier = g / (g - 1) * (n - 1) / (n - g - 2)
        se = [math.sqrt(multiplier * sum(sum(bread[j][k] * score[k] for k in range(2)) ** 2
                                         for score in scores)) for j in range(2)]
        critical = NormalDist().inv_cdf(.975)
        answer[outcome] = {"small_minus_regular": beta[0], "aide_minus_regular": beta[1],
                           "school_cluster_CR1_se": se,
                           "asymptotic_normal_95_intervals": [[v - critical * s, v + critical * s] for v, s in zip(beta, se)],
                           "group_means": {kind: fmean(float(r[outcome]) for r in rows if r["classk"] == kind)
                                           for kind in ("regular", "small.class", "regular.with.aide")}}
    return {"n": len(rows), "schools": len(groups),
            "arm_counts": {kind: sum(r["classk"] == kind for r in rows)
                           for kind in ("regular", "small.class", "regular.with.aide")}, "outcomes": answer}


def school_reference(rows):
    n = len(rows)
    y = [float(r["lwage76"]) for r in rows]
    x = [float(r["ed76"]) for r in rows]
    z = [float(r["nearc4"] == "yes") for r in rows]
    def slope(a, b):
        centered = [v - fmean(a) for v in a]
        denominator = sum(v * v for v in centered)
        estimate = sum(v * w for v, w in zip(centered, b)) / denominator
        intercept = fmean(b) - estimate * fmean(a)
        se = math.sqrt(n / (n - 2) * sum(v * v * (w - intercept - estimate * t) ** 2
                                       for v, w, t in zip(centered, b, a))) / denominator
        return estimate, se
    ols, ols_se = slope(x, y)
    first, first_se = slope(z, x)
    reduced, reduced_se = slope(z, y)
    wald = reduced / first
    residual = [a - wald * b for a, b in zip(y, x)]
    wald_se = slope(z, residual)[1] / abs(first)
    # HC1 covariance of the two reduced-form coefficients from separate regressions.
    zm = fmean(z)
    zz = sum((v - zm) ** 2 for v in z)
    uy = [a - fmean(y) - reduced * (c - zm) for a, c in zip(y, z)]
    ux = [a - fmean(x) - first * (c - zm) for a, c in zip(x, z)]
    cov = n / (n - 2) * sum((c - zm) ** 2 * a * b for a, b, c in zip(uy, ux, z)) / zz ** 2
    q = NormalDist().inv_cdf(.975) ** 2
    polynomial = [first ** 2 - q * first_se ** 2,
                  -2 * reduced * first + 2 * q * cov,
                  reduced ** 2 - q * reduced_se ** 2]
    aa, bb, cc = polynomial
    discriminant = bb ** 2 - 4 * aa * cc
    assert aa > 0 and discriminant > 0, "Revisit general AR set representation for changed input"
    bounds = sorted([(-bb - math.sqrt(discriminant)) / (2 * aa), (-bb + math.sqrt(discriminant)) / (2 * aa)])
    return {"n": n, "nearc4_yes": int(sum(z)), "OLS_unadjusted": {"slope": ols, "HC1_se": ols_se},
            "first_stage_unadjusted": {"slope": first, "HC1_se": first_se, "robust_t_squared": (first / first_se) ** 2},
            "reduced_form_unadjusted": {"slope": reduced, "HC1_se": reduced_se},
            "Wald_unadjusted": {"slope": wald, "HC1_se": wald_se},
            "AR_HC1_asymptotic_95": {"quadratic_le_zero": polynomial, "set_type": "bounded_interval", "bounds": bounds},
            "exp76_equals_age76_minus_ed76_minus_6": all(float(r["exp76"]) == float(r["age76"]) - float(r["ed76"]) - 6 for r in rows),
            "nomomed_equals_nodaded_rows": sum(r["nomomed"] == r["nodaded"] for r in rows)}


CHECKER = r'''"""Independent offline numerical self-check. Does not import the generator."""
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, NormalDist

ROOT = Path(__file__).resolve().parent


def equal(actual, expected, path='reference'):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path + ': keys'
        for key in expected:
            equal(actual[key], expected[key], path + '.' + key)
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path + ': length'
        for i, value in enumerate(expected):
            equal(actual[i], value, path + '.' + str(i))
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-8), path + ': value'
    else:
        assert actual == expected, path + ': value'


def star(rows):
    schools = sorted({r['schidkn'] for r in rows})
    kinds = ['small.class', 'regular.with.aide']
    results = {}
    for outcome in ['tmathssk', 'treadssk']:
        centered = []
        for school in schools:
            group = [r for r in rows if r['schidkn'] == school]
            mx = [mean(r['classk'] == k for r in group) for k in kinds]
            my = mean(float(r[outcome]) for r in group)
            centered += [(school, [int(r['classk'] == k) - mx[j] for j, k in enumerate(kinds)], float(r[outcome]) - my) for r in group]
        s11 = math.fsum(x[0] ** 2 for _, x, _ in centered)
        s12 = math.fsum(x[0] * x[1] for _, x, _ in centered)
        s22 = math.fsum(x[1] ** 2 for _, x, _ in centered)
        t1 = math.fsum(x[0] * y for _, x, y in centered)
        t2 = math.fsum(x[1] * y for _, x, y in centered)
        determinant = s11 * s22 - s12 ** 2
        beta = [(t1 * s22 - t2 * s12) / determinant, (t2 * s11 - t1 * s12) / determinant]
        variance = [0., 0.]
        for school in schools:
            errors = [(x, y - x[0] * beta[0] - x[1] * beta[1]) for s, x, y in centered if s == school]
            u1 = math.fsum(x[0] * e for x, e in errors)
            u2 = math.fsum(x[1] * e for x, e in errors)
            variance[0] += ((s22 * u1 - s12 * u2) / determinant) ** 2
            variance[1] += ((s11 * u2 - s12 * u1) / determinant) ** 2
        n, g = len(rows), len(schools)
        se = [math.sqrt(v * g / (g - 1) * (n - 1) / (n - g - 2)) for v in variance]
        q = NormalDist().inv_cdf(.975)
        results[outcome] = {'small_minus_regular': beta[0], 'aide_minus_regular': beta[1], 'school_cluster_CR1_se': se,
                           'asymptotic_normal_95_intervals': [[b - q*s, b + q*s] for b,s in zip(beta,se)],
                           'group_means': {k: mean(float(r[outcome]) for r in rows if r['classk'] == k)
                                           for k in ['regular','small.class','regular.with.aide']}}
    return {'n': len(rows), 'schools':len(schools), 'arm_counts':{k: sum(r['classk'] == k for r in rows)
            for k in ['regular','small.class','regular.with.aide']}, 'outcomes':results}


def schooling(rows):
    n = len(rows)
    groups = [[r for r in rows if r['nearc4'] == k] for k in ['no','yes']]
    def groupmean(key):
        return [mean(float(r[key]) for r in group) for group in groups]
    xmeans, ymeans = groupmean('ed76'), groupmean('lwage76')
    dx, dy = xmeans[1]-xmeans[0], ymeans[1]-ymeans[0]
    # HC1 coefficient variances from group residual sums, not generator's regression kernel.
    vxx = vyy = vxy = 0.
    for g, xm, ym in zip(groups, xmeans, ymeans):
        vxx += math.fsum((float(r['ed76'])-xm)**2 for r in g)/len(g)**2
        vyy += math.fsum((float(r['lwage76'])-ym)**2 for r in g)/len(g)**2
        vxy += math.fsum((float(r['ed76'])-xm)*(float(r['lwage76'])-ym) for r in g)/len(g)**2
    vxx, vyy, vxy = [v*n/(n-2) for v in [vxx,vyy,vxy]]
    xmean=mean(float(r['ed76']) for r in rows); ymean=mean(float(r['lwage76']) for r in rows)
    denominator=math.fsum((float(r['ed76'])-xmean)**2 for r in rows)
    ols=math.fsum((float(r['ed76'])-xmean)*(float(r['lwage76'])-ymean) for r in rows)/denominator
    ose=math.sqrt(n/(n-2)*math.fsum((float(r['ed76'])-xmean)**2*(float(r['lwage76'])-ymean-ols*(float(r['ed76'])-xmean))**2 for r in rows))/denominator
    iv=dy/dx
    ise=math.sqrt(vyy-2*iv*vxy+iv*iv*vxx)/abs(dx)
    q=NormalDist().inv_cdf(.975)**2
    a,b,c=dx*dx-q*vxx, -2*dx*dy+2*q*vxy, dy*dy-q*vyy
    d=b*b-4*a*c
    assert a>0 and d>0, 'changed confidence-set shape'
    bounds=sorted([(-b-math.sqrt(d))/(2*a),(-b+math.sqrt(d))/(2*a)])
    # Direct inversion check at boundaries and an interior/exterior point.
    for value in bounds:
        stat=(dy-value*dx)**2/(vyy-2*value*vxy+value*value*vxx)
        assert abs(stat-q)<1e-7, 'AR boundary'
    assert a*iv*iv+b*iv+c<0, 'AR includes point estimate'
    return {'n':n,'nearc4_yes':len(groups[1]),'OLS_unadjusted':{'slope':ols,'HC1_se':ose},
            'first_stage_unadjusted':{'slope':dx,'HC1_se':math.sqrt(vxx),'robust_t_squared':dx*dx/vxx},
            'reduced_form_unadjusted':{'slope':dy,'HC1_se':math.sqrt(vyy)},'Wald_unadjusted':{'slope':iv,'HC1_se':ise},
            'AR_HC1_asymptotic_95':{'quadratic_le_zero':[a,b,c],'set_type':'bounded_interval','bounds':bounds},
            'exp76_equals_age76_minus_ed76_minus_6':all(float(r['exp76'])==float(r['age76'])-float(r['ed76'])-6 for r in rows),
            'nomomed_equals_nodaded_rows':sum(r['nomomed']==r['nodaded'] for r in rows)}


def check():
    spec=json.loads((ROOT/'oracle.json').read_text(encoding='utf-8'))
    data=(ROOT/'public/data.csv').read_bytes()
    assert hashlib.sha256(data).hexdigest()==spec['data_sha256'], 'data identity'
    with (ROOT/'public/data.csv').open(encoding='utf-8', newline='') as stream:
        reader=csv.DictReader(stream); columns=reader.fieldnames; rows=list(reader)
    assert columns==spec['columns'], 'columns/order'
    assert all(None not in r for r in rows), 'malformed CSV'
    equal({k:sum(r[k]=='' for r in rows) for k in columns}, spec['missing_cells'], 'missingness')
    actual=star(rows) if spec['dataset']=='star' else schooling(rows)
    equal(actual,spec['reference'])
    print(json.dumps({'ok':True,'dataset':spec['dataset'],'rows':len(rows),'scope':'fixture numerics only; no live consultation'}))


if __name__=='__main__':
    check()
'''


REPORT = ("Deliver a complete saved local consultant report with reproducible supported calculations, the main answer, "
          "source and design reasoning, appropriate uncertainty, limitations, practical implications and a technical appendix. "
          "Prefer self-contained HTML; no publication. A bounded descriptive or explicitly conditional analysis can form a complete "
          "report. A chat recap or an analysis file does not finish the goal.")

STAR_DICTIONARY = f"""# Kindergarten extract dictionary

One row is a student record; data.csv preserves the prepared extract. Blank means missing.
The file has 5,748 rows and 8 columns. Scores use their original scaled-score units.

| Field | Meaning / observed encoding |
|---|---|
| tmathssk | Kindergarten mathematics scaled score |
| treadssk | Kindergarten reading scaled score |
| classk | Class type: regular, small.class, regular.with.aide |
| totexpk | Teacher's total experience, years |
| sex | boy or girl |
| freelunk | Free-lunch eligibility: no or yes |
| race | white, black or other |
| schidkn | Kindergarten school identifier; categorical, not a classroom identifier |

[Ecdat Star documentation]({URL_STAR}) supplies the field definitions. The original
study covered several grades; these variables describe kindergarten. There is no
original-assignment field, classroom ID, pupil roster for excluded records, peer
network, treatment-saturation assignment or longitudinal student link in this file.
No missing cells in this extract does not establish complete original-study follow-up.
The provenance and study notes listed in available-records.md can be supplied.
"""

STAR_NOTES = f"""# Study and extract notes

This is an analyst-prepared source summary, checked 2026-09-09, not an original
administrative memo. [Krueger (1999), QJE 114(2), pp. 498, 501-502]({URL_KRUEGER})
describes within-school randomization among small, regular and regular-with-aide
classes. The recorded class type described fall enrollment, not an original
randomization log. A separate audit covered 1,581 students from 18 schools and
found approximately 0.3% enrollment/assignment disagreement. That audit does not
certify every record here. Subsequent-grade switching and attrition do not turn
kindergarten variables into longitudinal exposure histories.

The study's experimental origin is meaningful evidence. An enrollment comparison
can be interpreted as an approximation to assignment only with its limitations
stated; there is no exact local ITT reconstruction. School adjustment respects
the documented within-school comparison. School clustering can allow dependence
within the observed schools under an independent-school sampling approximation;
it cannot recover missing classroom allocation or supply an exact randomization test.

Local extract verification: 5,748 records, 79 school IDs; class counts are 2,000
regular, 1,733 small and 2,015 regular-with-aide. All eight fields are populated.
The observed fraction in small classes is not a randomized saturation intervention.
There are no class sizes, classroom IDs, peer links or original assignment sheets
available during this consultation. Repeated requests cannot produce them.

The current [Rdatasets Star export](https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/Ecdat/Star.csv)
was compared cell by cell and in order with this file after dropping only its
rownames column. All cells agree. The prepared bytes, including line endings, are
preserved. The educational-data source is [Ecdat]({URL_STAR}); this extract is not
the complete original STAR archive. No matching protocol to every excluded
original-study record has been independently recovered.
"""

SCHOOL_DICTIONARY = f"""# Schooling extract dictionary

One row is an individual in the 1976 wage extract. Blank means missing; indicator
fields use yes/no. Preserve the supplied values and distinguish blank cells from
imputed parental information. [Ecdat Schooling documentation]({URL_SCHOOL}) and
[Card's primary codebook and reading program]({URL_CARD}) are the sources.

| Fields | Meaning |
|---|---|
| smsa66, smsa76 | Metropolitan-area residence in 1966 and 1976 |
| nearc2, nearc4 | Grew up near a two-year / four-year college |
| nearc4a, nearc4b | Four-year public / private college proximity |
| ed66, ed76 | Years of education recorded in 1966 and 1976 |
| age76 | Age in 1976 |
| daded, momed | Parental education, including imputed values |
| nodaded, nomomed | Documented as parental-education imputation flags; verify coding before use |
| momdad14, sinmom14, step14 | Family arrangement at age 14 |
| south66, south76 | Southern residence in 1966 and 1976 |
| lwage76 | Recorded log hourly wage; source describes outlier trimming |
| wage76 | Raw hourly wage, cents |
| famed | Parental education category, codes 1-9 |
| black | Recorded race indicator |
| enroll76, mar76 | Enrollment and married/spouse-present indicators in 1976 |
| kww, iqscore | Work-knowledge and normed IQ scores; do not assume pretreatment timing |
| libcrd14 | Home library-card indicator at age 14 |
| exp76 | Potential experience, computed as age76 - ed76 - 6 |

The file omits primary respondent IDs, survey weights and detailed 1966 region
indicators. Row position is a local reference, not a validated link to another
survey. Exposure is years of education, not a binary college-treatment variable.
The original archive/extract reconciliation and methods notes are available on request.
"""

SCHOOL_NOTES = f"""# Provenance and extract reconciliation

Prepared 2026-09-09 from [Ecdat's documentation]({URL_SCHOOL}) and
[David Card's own data archive]({URL_CARD}), linked from his
[data page](https://davidcard.berkeley.edu/data_sets.html). These are analyst notes,
not newly discovered survey records. Card (1995), *Using Geographic Variation in
College Proximity to Estimate the Return to Schooling*, studies NLS Young Men.

The primary archive contains 3,613 records. Restricting to its nonmissing lwage76
gives 3,010 records in the same order as this extract. All mapped supplied fields
agree within 0.00001 after indicator recoding and exp76 construction, except
nomomed. The extract's nomomed equals nodaded in all 3,010 rows and disagrees with
the primary maternal-imputation flag in 537 rows. The primary selected sample has
353 maternal imputations; the supplied flag says yes in 690 rows. Preserve the
original CSV. A row-level correction is not supplied or authorized by this note;
avoid relying on that flag or clearly delimit a sensitivity analysis. A statement
that no fields have imputation problems would be incorrect.

The local file has 949 blank iqscore values, 47 blank kww values, 7 blank mar76
values and 13 blank libcrd14 values. Other columns have no blank cells. Complete-case
analysis using every field changes the sample and does not resolve imputation.
The source's read1.sas constructs exp76=age76-ed76-6; this equality holds on every
local row. Experience and 1976 residence/enrollment/marital status are not simply
pre-schooling covariates. ed66 is earlier than 1976 but need not precede the
college-proximity exposure or be unaffected by it. Measurement dates for kww/IQ
are not established by this staged documentation.

The [Rdatasets export](https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/Ecdat/Schooling.csv)
matches every supplied cell after removing only rownames. Source survey weights,
detailed region indicators, respondent identifiers, missing outcomes, measurement
dates and row-level imputation repairs are not staged for this consultation.
No new source acquisition or staff contact is available. The bibliography permits
methodological reading; it does not authorize silently replacing or enriching
the frozen data. The returned coefficient is not a known true causal effect.
"""

IV_NOTES = f"""# Interpretation and uncertainty notes

These are consultation reference notes, not evidence that this instrument is
valid. Card (1995) proposes college proximity as an instrument for schooling;
the original [data and codebook]({URL_CARD}) establish provenance, not exclusion.

An IV analysis needs a credible relevance argument and a defense of instrument
exogeneity and exclusion relative to a specified target and conditioning set.
Local labor markets, family location and access to other opportunities are
possible threats to assess, not established mechanisms in these records.
Balance or a large first-stage statistic cannot prove validity. With continuous
schooling, a binary-treatment complier ATE interpretation needs care; under
appropriate monotonic-response assumptions an IV ratio can weight schooling
increments differently from an overall average return. Those assumptions are not
facts the user can certify.

[Andrews, Stock and Sun (2019), Annual Review of Economics 11:727-753]({URL_IV})
explain why weak instruments impair conventional IV inference and why the
variance assumptions matter. Anderson-Rubin-type inversion can provide
weak-identification-robust uncertainty for the specified IV moment model. It
does not repair an invalid instrument, and a heteroskedasticity-robust version
is generally asymptotic rather than a finite-sample exact test. A confidence set
may be very wide, unbounded or disconnected; do not truncate it to a convenient grid.

Useful options include a justified adjusted 2SLS analysis, first-stage and
reduced-form diagnostics, weak-IV-robust inference, explicit sensitivity to
exclusion or conditioning choices, or a limited descriptive analysis if assumptions
remain unsupported. Flexible nuisance models or orthogonal-score IV methods
require their own target, moment restrictions, sample-splitting and inference
argument. Model complexity, a method name or first-stage prediction accuracy
does not establish identification. Select proportionately; no single estimator
or package is required. State when a numerical result is conditional.
"""


def actor_packet(dataset, persona, sources):
    common = [
        fact("f-report", REPORT),
        fact("f-access", "Use the supplied extract and listed staged notes. No new participant records, private contacts, corrected dataset or source enrichment can be obtained in this consultation.", certainty="user constraint"),
        fact("f-boundary", "I can explain my goal and documentation I have read, not unseen outcomes or whether a causal identifying assumption is true.", certainty="knowledge boundary"),
    ]
    if dataset == "star":
        profile = {"domain_expertise": "Education evaluation and class-size policy; has read the staged study notes, did not administer STAR.",
                   "statistical_expertise": "Comfortable with adjusted comparisons and uncertainty; needs help with interference and assignment/enrollment distinctions.",
                   "cooperation": "Proactively correct relevant documented operational confusion, attach relevant notes, and answer factual questions without waiting for a password.",
                   "beliefs": [{"subject": "b-enrollment", "initial": "I have been informally calling classk the assigned class type.", "certainty": "provisional shorthand", "revision": "When the distinction from original assignment is explained, use enrollment terminology and accept a qualified experimental interpretation."}],
                   "learning_subjects": ["b-enrollment", "k-school-unit", "d-claim-scope"],
                   "goals": "Explain what smaller kindergarten classes appear to do for achievement and what the available extract can responsibly say to education policymakers."}
        facts = common + [
            fact("f-study", "The published experiment randomized within schools. The recorded class variable is fall enrollment. A separate small audit found little initial disagreement, but I cannot certify every row in this extract.", "s-study"),
            fact("f-clusters", "schidkn is a school ID. The extract has no classroom IDs, original assignment sheets, class-size totals, peer links or randomized saturation variable.", "s-dictionary and s-study"),
            fact("f-extract", "The file has 5,748 populated student records from 79 schools. I do not know the outcomes of excluded children or the exact original-to-extract selection history.", "s-study"),
            fact("f-target", "Use small versus regular kindergarten classes as the main comparison; keep the regular-with-aide arm visible rather than merging it without explanation. Mathematics is primary and reading is a secondary corroborating outcome. Do not promise an effect for current schools identical to these historical schools.", certainty="user preference"),
        ]
        specific = [rule("r-domain-correction", "The consultant conflates classroom with school, original assignment with enrollment, or treats observed school shares as an assigned saturation policy.", "Volunteer the relevant documented distinction and offer or attach study-notes.md if not previously supplied. Explain the operational fact, not an expert causal verdict. If the consultant already handles it correctly, acknowledge without repeating a challenge.", ["f-study", "f-clusters"], ["s-study"])]
    else:
        profile = {"domain_expertise": "Applied statistician with general labor-economics familiarity; not an original NLS investigator.",
                   "statistical_expertise": "Understands IV, regression and robust uncertainty. Interested in weak-IV inference and flexible nuisance adjustment, with finite expertise in this extract's provenance.",
                   "cooperation": "Engage with a concrete justification, discuss alternatives, and revise a preferred method or covariate set when the explanation identifies a real limitation.",
                   "beliefs": [{"subject": "b-covariates", "initial": "I initially expect the familiar experience and location controls to be reasonable starting candidates.", "certainty": "tentative method preference", "revision": "Revise after a concrete timing or deterministic-dependence explanation; do not keep demanding all columns as controls."},
                               {"subject": "b-flexible-iv", "initial": "Flexible IV nuisance models might improve adjustment.", "certainty": "proposal, not a conclusion", "revision": "Accept a simpler justified estimator or sensitivity analysis when flexibility offers no clear benefit or does not address identification."}],
                   "learning_subjects": ["b-covariates", "b-flexible-iv", "k-imputation", "d-claim-scope"],
                   "goals": "Assess what the college-proximity design can support about schooling and wages; pursue useful advanced inference when justified without equating sophistication with validity."}
        facts = common + [
            fact("f-target", "I want the wage change associated with an additional year of schooling, and an explicit explanation of the population and schooling increments an IV interpretation would cover. The 1976 sample should not automatically represent everyone today.", certainty="user preference"),
            fact("f-method", "I am interested in comparing a transparent IV baseline with justified weak-IV-robust inference or sensitivity, and possibly flexible nuisance adjustment if it materially helps. I do not require a particular estimator when its assumptions or costs are unsuitable.", certainty="method preference"),
            fact("f-source-availability", "I can send an existing extract/provenance note and a short methods note. I have not independently reconciled the archive or memorized its discrepancies.", "user source inventory"),
            fact("f-source-boundary", "I do not know the true return to education, latent ability, instrument validity, test measurement dates, or missing outcomes. I cannot supply respondent IDs, region variables, weights or row-level repairs absent from the staged files.", certainty="knowledge boundary"),
        ]
        specific = [
            rule("r-method-discussion", "The consultant proposes a method or asks how to balance rigor, flexibility and interpretability.", "Discuss the relevant tradeoff at an expert level using visible evidence. Ask for the target and assumptions behind an unclear advanced proposal. Accept a well-justified simpler route; do not demand multiple sophisticated procedures merely to lengthen the test.", ["f-method", "f-target"]),
            rule("r-method-revision", "A visible explanation or inspected note establishes a concrete problem with a preferred covariate, extract field or proposed method.", "Acknowledge what changes and revise that specific preference. A nominal claim that something is invalid is not proof, but do not require particular wording or repeated persuasion. Record an evidence-grounded belief/knowledge/decision update if one occurred. Do not invent a correction or certify causal validity.", ["f-method"]),
        ]
    rules = [
        rule("r-facts", "A relevant factual, broad or combined question is asked.", "Answer all closely related known facts proportionately to the persona. Distinguish prior knowledge from source availability and from what the consultant just explained; leave unrelated questions recorded as unanswered. Do not invent missing study history."),
        rule("r-source", "The consultant requests relevant provenance, study details, source reconciliation, methods support, or all available supporting documents.", "Release each relevant staged note immediately if not already supplied. An inventory-only question can receive its description; a broad request to inspect/use materials suffices for release. On repeated requests refer to the existing filename without duplicate attachment. The actor may read a delivered note and update its own understanding, but does not infer that the consultant inspected it.", sources=[s["source_id"] for s in sources if s["availability"] == "on_request"]),
        rule("r-unknown", "A question requires unavailable data, unknown historical facts or certification of identification.", "State the knowledge/access boundary and permit supported work to continue. Log an actually unspecified consequential fact as a fixture gap; declared unavailability is not a gap. Never create a new source to rescue or defeat the consultant.", ["f-access", "f-boundary"]),
        rule("r-action", "A bounded useful step fits the original report objective.", "Authorize it without choosing a specialist. A domain expert can explain operational context and a statistician can discuss methods within their declared competence. Neither reads the review key."),
        rule("r-learn", "A comprehensible visible explanation or an actually read source resolves a specific misunderstanding or makes the practical implication clear.", "Update that understanding and subsequent cooperation. Record subject, before, after and evidence in the appropriate optional update array. Do not reset the misconception or treat the explanation as new observational evidence. Plausible explanations can persuade a fallible user; the reviewer judges scientific correctness."),
        rule("r-no-progress", "There is no actionable question, useful proposal or deliverable.", "Restate the current goal or ask what the reasoning implies for the decision. Ask for clarification of the specific unclear point, not a generic demand for more rounds."),
    ] + specific + [
        rule("r-report", "Useful intermediate work exists or the consultant offers a recap/report, but the promised saved report is not delivered.", "Accept the useful work and request completion of the saved report, including any consequential attainable work still needed. Once the evidentiary boundary is established, accept honest limitations rather than restarting an exhausted inquiry.", ["f-report"]),
        rule("r-repair", "The delivered report has a visible missing promised component, unreadable file or contradiction with facts/results the user actually knows.", "Request the concrete repair. Do not manufacture a defect, use private state or apply a hidden reviewer checklist.", ["f-report"]),
        rule("r-stop", "The requested saved report is delivered with a usable artifact reference and no visible unresolved failure or promised correction remains.", "Stop. The independent reviewer verifies actual artifact integrity and science; user satisfaction alone does not certify either. Resource/environment stops remain incomplete when the report is absent.", ["f-report"]),
    ]
    return {"role": "Simulated user. Read only this packet, visible exchanges and explicitly accessible public documents. Never read world.json, reviewer.json, oracle.json, private provenance audits or consultant internal state. Respond semantically and adaptively, without fixed turn counts or secret phrases.",
            "persona_id": persona, "profile": profile, "goal": profile["goals"] + " " + REPORT,
            "fluency": profile["statistical_expertise"], "facts": facts, "sources": sources, "rules": rules,
            "unknown_policy": "Unspecified facts remain unknown. Public methodological browsing cannot add new respondent data to this frozen world.",
            "reply_record": {"message": "exact public text or null if stopping", "fact_ids": [], "rule_ids": [], "attachments": [], "unanswered_questions": [], "fixture_gaps": [], "stop": False,
                             "knowledge_updates": [], "belief_updates": [], "decision_updates": []},
            "update_contract": "Optional update arrays use exactly {subject,before,after,evidence}, all nonempty strings. Use a stable profile subject ID where applicable and a human-readable actual visible exchange/received-source reference. Record only real changes; no numerical trust score."}


def build(case_id):
    dataset, persona, source_dir, expected = CASES[case_id]
    data = (ROOT.parent / "test-data" / source_dir / "data.csv").read_bytes()
    if sha(data) != expected:
        raise ValueError("Prepared input changed; review/version the case before regeneration: " + dataset)
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
    is_star = dataset == "star"
    world_id = "ecdat-" + dataset + "-prepared-2026-09-09"
    sources = [
        {"id": "s-data", "file": "public/data.csv", "destination": "data.csv", "availability": "initial"},
        {"id": "s-dictionary", "file": "public/dictionary.md", "destination": "dictionary.md", "availability": "initial"},
        {"id": "s-inventory", "file": "public/available-records.md", "destination": "available-records.md", "availability": "initial"},
        {"id": "s-study", "file": "public/records/study-notes.md", "destination": "study-notes.md", "availability": "on_request"},
    ]
    if not is_star:
        sources.append({"id": "s-methods", "file": "public/records/methods-notes.md", "destination": "methods-notes.md", "availability": "on_request"})
    actor_sources = [{"source_id": s["id"], "file": s["destination"], "availability": s["availability"],
                      "release": "initially supplied" if s["availability"] == "initial" else "Immediately available on a semantically relevant request, or a documented domain-user correction; attach at most once."} for s in sources]
    actor = actor_packet(dataset, persona, actor_sources)
    if is_star:
        request = ("Use the causal-consultant skill. I work on education evaluation and have a kindergarten extract from Project STAR. "
                   "Please assess what it tells us about smaller classes and achievement for an education-policy audience. Mathematics is "
                   "the main outcome, with reading as a secondary check; compare small classes with ordinary regular classes and explain "
                   "what to do with the aide arm. I have been calling classk the assigned class, though I would appreciate your checking "
                   "that interpretation. I can provide study documentation and practical context. " + REPORT + "\n")
        specific = [
            criterion("c-design", "Use the documented experimental origin and within-school randomization. Distinguish observed enrollment from original assignment; the 18-school audit is informative but cannot establish perfect compliance for every extract record. Do not turn this limitation into a blanket claim that the experiment was observational or that useful analysis is impossible."),
            criterion("c-comparison", "Keep the three class types explicit. Use a justified within-school comparison, suitable dependence-aware uncertainty, correct score units and clear target; explain any pooling, adjustment or alternative estimator. School IDs are not classroom IDs. School-cluster asymptotics are not exact randomization inference."),
            criterion("c-no-invented-spillover", "Do not infer a randomized saturation design or peer-effect identification from observed school shares. The data lack classroom IDs, peer links and saturation assignments. Acknowledge unavailable exposure details without requiring inaccessible truth or fabricating sources."),
            criterion("c-domain-adaptation", "Use the cooperative user's documented operational corrections, explain the consequential assignment/enrollment or clustering distinction at the needed level, and let that learning reduce repeated questioning. Credit actual evidence uptake, not a scripted correction count."),
        ]
        notes, dictionary = STAR_NOTES, STAR_DICTIONARY
        reference = star_reference(rows)
        reference_scope = ("OLS of each kindergarten score on small and aide indicators plus unrestricted school intercepts, with regular as reference. "
                           "CR1 clusters on 79 schools; multiplier G/(G-1)*(N-1)/(N-G-2), asymptotic normal 95% intervals. These are reproducible "
                           "enrollment comparisons, not an exact ITT or verified policy/spillover effect. Causal interpretation depends on stated "
                           "experimental/compliance/selection assumptions. Alternative valid adjustment or uncertainty requires matching independent review.")
    else:
        request = ("Use the causal-consultant skill. I am an applied statistician preparing a report on schooling and wages using this "
                   "Card/Ecdat extract. Can college proximity support a credible IV estimate of the return to an additional year of schooling? "
                   "I would like a transparent baseline and a serious assessment of assumptions and uncertainty. Weak-IV-robust inference or "
                   "sensitivity may help; flexible IV nuisance models also interest me if they add something defensible. Familiar experience "
                   "and location controls are starting candidates, not a fixed specification. Please examine the extract before selecting them. "
                   "I have provenance and methods notes available. " + REPORT + "\n")
        specific = [
            criterion("c-design", "Separate first-stage relevance from exogeneity/exclusion and define the schooling/earnings target. No true effect is known. A causal statement is conditional on a defensible IV argument, not on balance, a first-stage statistic, a method label or the user's assent. Continuous schooling is not automatically a binary-treatment complier ATE."),
            criterion("c-data-and-timing", "Inspect actual missingness and distinguish imputation from blank cells. Establish exp76's deterministic dependence on schooling; do not automatically treat 1976 covariates or even ed66 as unaffected pre-instrument variables. Investigate the accessible imputation discrepancy if using parental flags, preserve original bytes and do not invent a row-level correction."),
            criterion("c-advanced-reasoning", "Engage substantively with the expert's proposal: justify a target and conditioning set, examine first stage/reduced form, and select appropriate weak-IV-robust inference, sensitivity, or a specific defensible alternative. Flexible nuisance methods require their own identification, cross-fitting and uncertainty argument. Rejecting sophistication categorically or running a menu of methods without purpose is insufficient; not every listed method is required."),
            criterion("c-inference", "Use uncertainty appropriate to the selected sample/moment model and variance assumptions. Ordinary second-stage OLS standard errors are not 2SLS uncertainty. Weak-IV-robust inference does not establish exclusion. If an inverted set is unbounded/disconnected preserve that shape; do not report grid endpoints as confidence limits. No numeric reference is a known causal truth."),
            criterion("c-statistician-adaptation", "Discuss methods at the user's actual level, address specific concerns, and permit reasoned changes in initial covariate/method preferences. Do not assume this expert knows inaccessible provenance or can certify causal assumptions. Judge observed explanatory progress, not compulsory teaching or a fixed number of challenges."),
        ]
        notes, dictionary = SCHOOL_NOTES, SCHOOL_DICTIONARY
        reference = school_reference(rows)
        reference_scope = ("All 3,010 rows: unadjusted OLS lwage76~1+ed76, first stage ed76~1+nearc4, reduced form lwage76~1+nearc4, "
                           "and their just-identified Wald ratio with HC1 (N/(N-2)) variance. The AR set inverts the heteroskedasticity-robust "
                           "coefficient test of nearc4 in (lwage76-beta*ed76)~1+nearc4, using the asymptotic chi-square(1) 0.95 threshold. "
                           "These are transparent numerical diagnostics conditional on the stated linear-IV moment assumptions, not an endorsed "
                           "unadjusted causal specification, exact original-paper replication or known true return. Adjusted 2SLS, flexible IV and "
                           "alternative valid inference are permitted but need independently matched review; this oracle does not qualify their numbers.")
    inventory = "# Available materials\n\nThe CSV and dictionary are supplied. study-notes.md is immediately available on request and covers study provenance, extract limits and source reconciliation.\n"
    if not is_star:
        inventory += "methods-notes.md is also available for the IV interpretation and uncertainty discussion.\n"
    inventory += "\nAsk for relevant supporting records in ordinary language; no special filename is needed. These are source summaries, not new participant records. No private contacts, additional respondent data, missing source IDs or row-level corrections are available in this consultation.\n"
    package = {"public/data.csv": data, "public/initial-message.txt": request.encode(), "public/dictionary.md": dictionary.encode(),
               "public/available-records.md": inventory.encode(), "public/records/study-notes.md": notes.encode(),
               "actor.json": encode(actor), "check_oracle.py": CHECKER.encode()}
    if not is_star:
        package["public/records/methods-notes.md"] = IV_NOTES.encode()
    oracle = {"dataset": dataset, "data_sha256": sha(data), "columns": list(rows[0]),
              "missing_cells": {k: sum(r[k] == "" for r in rows) for k in rows[0]},
              "reference": reference, "reference_scope": reference_scope,
              "tolerance": "Absolute 1e-8 for these exact unrounded specifications; half a final displayed unit for rounding. New valid methods need independent verification.",
              "causal_truth": None, "qualification": "Independent numerical fixture validation only; no live actor or consultant behavior qualified."}
    package["oracle.json"] = encode(oracle)
    world = {"world_id": world_id, "world_version": VERSION, "dataset": dataset, "kind": "real historical extract; no synthetic potential-outcome truth",
             "data_sha256": sha(data), "known": ["Exact shipped CSV, documented definitions and source notes", "Observed missingness and independently checked basic reference calculations"],
             "unknown": (["Row-level original assignment/compliance", "Complete original-to-extract selection history", "Classroom/peer structure and counterfactual saturation effects"] if is_star else
                         ["True return to schooling and instrument validity", "Latent ability and counterfactual wages", "Unstaged test measurement dates, respondent links and row-level imputation repair"]),
             "attainable": [s["id"] for s in sources],
             "unavailable": "The actor's access constraint is a fictional consultation constraint, not a claim that historical archives never existed. No additional source acquisition or data enrichment during this case.",
             "belief_boundary": "The persona, audience and preferences are fictional; published study facts and data are not rewritten. Actor beliefs and learning are not scientific truth.",
             "acquisition_rules": "Existing source notes can be supplied by semantically relevant requests; the domain expert can volunteer documented corrections. No new world facts emerge from round count, persuasion alone or an evaluator's preferred route.",
             "completion_contract": "full_report"}
    package["world.json"] = encode(world)
    criteria = [
        criterion("c-evidence", "Credit only disclosed facts or actually inspected source evidence and their effect on interpretation/action. The private world, actor ledger, oracle and source receipt alone cannot supply consultant knowledge. Accept equivalent questions and justified alternative paths."),
        criterion("c-integrity", "Preserve source bytes, save reproducible calculations and chosen analysis plans, identify sample/units/exclusions, and verify the current project. Do not substitute an easier dataset or silently add unstaged records."),
        criterion("c-proportionality", "Investigate consequential attainable uncertainties and act on resolved ones. Avoid repeated unknown-source requests, a method checklist or a fixed-round stopping script. A dataset/persona pairing is one context and does not identify a general persona effect."),
    ] + specific + [
        criterion("c-report", "Deliver an actual complete report in a completed verified separate report run, bound to the selected calculations, diagnostics and sources. Include main answer, reasoning, results and appropriate uncertainty, limitations, implications and reproducibility detail. A recap/CSV/offer alone is incomplete; honest conditional or descriptive conclusions can support a complete report."),
        criterion("c-report-validation", "Read back report claims against saved evidence and retain applicable rendering inspection/corrections. Artifact existence and actor satisfaction do not establish scientific quality. Record unperformed validation honestly."),
        criterion("c-actor-fidelity", "Separately review whether disclosures, learning and cooperation follow actual accessible evidence and the frozen persona. A fabricated actor fact or ungrounded change can invalidate the affected claim; it is not automatically a consultant defect."),
    ]
    package["reviewer.json"] = encode({"case_id": case_id, "case_version": VERSION, "suite_version": SUITE,
        "scientific_truth": "Real data have no supplied true causal effect. Use world.json, source notes and oracle scope; do not infer hidden histories.",
        "completion": REPORT, "criteria": criteria, "numeric_reference": reference_scope,
        "allowed_alternatives": "Scientifically justified estimators, conditioning sets, uncertainty methods and report structures are allowed. Independently check any non-reference method before crediting its numbers.",
        "required_observations": ["actual public conversation and disclosed sources", "actor knowledge/belief/decision changes and their evidence", "source inspection and actual tool traces", "analysis plans, code and outputs", "latest report manifest/artifact and project verification", "readback/rendering evidence", "all attempts, failures and resource stops"],
        "validity": "Fixture self-checks are not live behavior. A verified host, isolated roles and independent scientific review remain necessary. This single persona/world pairing cannot isolate persona effects.", "useful_stop": False})
    provenance = {"kind": "new standalone persona case using unchanged real prepared data", "checked_on": "2026-09-09",
        "generator": "interactive-test-cc/scripts/generate_persona_real_cases.py", "generator_sha256": sha(Path(__file__).read_bytes()),
        "prepared_source": "test-data/" + source_dir + "/data.csv", "prepared_sha256": sha(data),
        "upstream_export": "https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/Ecdat/" + ("Star" if is_star else "Schooling") + ".csv",
        "upstream_sha256": "2a029cf43fad58cfc477d8dd1ae431a370e01cf92ef608ede5f421e1c4b93be1" if is_star else "d2027e2bd26092b8456dd55605d84422d52d5443d308836167e706dd66daaba6",
        "reconciliation": "All cells/order match the 2026-09-09 public export after dropping its rownames column. Prepared bytes are preserved, not normalized or corrected.",
        "primary_sources": [URL_STAR, URL_KRUEGER] if is_star else [URL_SCHOOL, URL_CARD, "https://davidcard.berkeley.edu/data_sets.html", URL_IV],
        "historical_claim_limit": "No legacy actor history, invented saturation scheme, legacy prepared-data hash or presumed causal truth is inherited.",
        "audit_location": "audits/v7-personas-2026-09-09/source-reconciliation/reconciliation.json; authoring audit only, not a runtime dependency",
        "validation": "Separate generator/reference and standalone checker implementations; exact regeneration and mutated-data checks. Live behavior remains unqualified."}
    if not is_star:
        provenance["primary_reconciliation"] = {"archive_sha256": "0e9b2ad4182ea631ca3dd8a5fff6c1b0ab86b56c6a3fa868870f716e8d82691f", "original_rows": 3613, "nonmissing_logwage_rows": 3010,
            "match": "Same row order; mapped numeric fields within 1e-5, binary recoding and calculated experience. Sole discrepancy is nomomed, 537 rows.",
            "local_duplicate_flags": 3010, "primary_maternal_imputations": 353, "local_maternal_flag_yes": 690,
            "repair": "Source note is staged; original row-level archive/repair is not staged. Preserve CSV and treat the discrepancy explicitly."}
    package["provenance.json"] = encode(provenance)
    manifest = {"schema_version": 1, "case_id": case_id, "case_version": VERSION, "suite_version": SUITE,
        "edition": "adaptive-persona-complete-report", "author": "Codex real-data fixture construction, 2026-09-09",
        "world": "world.json", "world_id": world_id, "world_version": VERSION, "persona_id": persona,
        "target_consultant": "7.0.2", "completion_contract": "full_report", "run_limits": LIMITS,
        "initial_message": "public/initial-message.txt", "actor": "actor.json", "reviewer": "reviewer.json", "oracle_check": "check_oracle.py",
        "requirements": "Shared Python 3.10+ stdlib for fixture checks, shared Node and consultant 7.0.2. Use shared analysis tools and a report readback/rendering surface; no project-local environments. No live qualification is implied.",
        "sources": sources, "files": {k: sha(v) for k, v in sorted(package.items())}}
    package["case.json"] = encode(manifest)
    return package


def main():
    for case_id in CASES:
        package = build(case_id)
        directory = ROOT / "cases" / case_id
        present = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
        if present - package.keys():
            raise ValueError("Unexpected files in new case: " + case_id)
        for name, value in package.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value)
        print(case_id, sha(package["case.json"]))


if __name__ == "__main__":
    main()
