# Provenance and extract reconciliation

Prepared 2026-09-09 from [Ecdat's documentation](https://search.r-project.org/CRAN/refmans/Ecdat/html/Schooling.html) and
[David Card's own data archive](https://davidcard.berkeley.edu/data_sets/proximity.zip), linked from his
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
