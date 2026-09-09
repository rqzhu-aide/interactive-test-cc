"""Independent offline numerical self-check. Does not import the generator."""
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
