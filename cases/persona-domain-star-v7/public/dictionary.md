# Kindergarten extract dictionary

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

[Ecdat Star documentation](https://search.r-project.org/CRAN/refmans/Ecdat/html/Star.html) supplies the field definitions. The original
study covered several grades; these variables describe kindergarten. There is no
original-assignment field, classroom ID, pupil roster for excluded records, peer
network, treatment-saturation assignment or longitudinal student link in this file.
No missing cells in this extract does not establish complete original-study follow-up.
The provenance and study notes listed in available-records.md can be supplied.
