# Schooling extract dictionary

One row is an individual in the 1976 wage extract. Blank means missing; indicator
fields use yes/no. Preserve the supplied values and distinguish blank cells from
imputed parental information. [Ecdat Schooling documentation](https://search.r-project.org/CRAN/refmans/Ecdat/html/Schooling.html) and
[Card's primary codebook and reading program](https://davidcard.berkeley.edu/data_sets/proximity.zip) are the sources.

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
