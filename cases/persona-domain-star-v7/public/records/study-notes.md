# Study and extract notes

This is an analyst-prepared source summary, checked 2026-09-09, not an original
administrative memo. [Krueger (1999), QJE 114(2), pp. 498, 501-502](https://hceconomics.uchicago.edu/sites/default/files/events/Krueger_1999_QJE_v114_n2.pdf)
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
preserved. The educational-data source is [Ecdat](https://search.r-project.org/CRAN/refmans/Ecdat/html/Star.html); this extract is not
the complete original STAR archive. No matching protocol to every excluded
original-study record has been independently recovered.
