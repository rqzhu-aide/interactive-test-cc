# Interpretation and uncertainty notes

These are consultation reference notes, not evidence that this instrument is
valid. Card (1995) proposes college proximity as an instrument for schooling;
the original [data and codebook](https://davidcard.berkeley.edu/data_sets/proximity.zip) establish provenance, not exclusion.

An IV analysis needs a credible relevance argument and a defense of instrument
exogeneity and exclusion relative to a specified target and conditioning set.
Local labor markets, family location and access to other opportunities are
possible threats to assess, not established mechanisms in these records.
Balance or a large first-stage statistic cannot prove validity. With continuous
schooling, a binary-treatment complier ATE interpretation needs care; under
appropriate monotonic-response assumptions an IV ratio can weight schooling
increments differently from an overall average return. Those assumptions are not
facts the user can certify.

[Andrews, Stock and Sun (2019), Annual Review of Economics 11:727-753](https://lsun20.github.io/WIRev_092218-%20corrected.pdf)
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
