# Adaptive Pilot Blueprints

Status: specification only, 2026-09-07. These four portable blueprints are not
datasets, executable fixtures, captured conversations, results or qualification.
Construct, independently check and freeze each fixture before live execution.

## Scope and common contract

Source: causal-consultant's `architecture/evaluation/consulting-quality-scenarios.md`.
Mappings identify reused mechanisms, not equivalent difficulty or inherited passes.
Leave original CQ cases, frozen 15-case fixtures and historical evidence intact.

| New ID | Mechanism borrowed | Coverage deliberately not claimed |
|---|---|---|
| V7P01 | CQ03 and CQ03-E1: operational meaning and additional material change preparation | Complete original CQ03 fixture or its two communication editions |
| V7P02 | CQ04: design, estimand and independent numerical validation; direct-request negative control | CQ04's composed randomization and spillover reasoning |
| V7P03 | CQ01 and CQ01-E1: cheap source choice and useful stopping | All competing-investigation and resource conditions of CQ01 |
| V7P04 | CQ02: the consultant revises its own earlier decision after correction | Memory-only recovery without conversation history, or CQ06 long-history retrieval |

Freeze public materials, initial request, private ledger, response rules, hashes,
independent oracles and tolerances. Separate study truth from what the user knows,
believes or can obtain at each stage. Keep private facts and reviewer keys outside
consultant-readable storage; an instruction not to read them is not a boundary.

Default replies are one short factual sentence, following the
[reply policy](user-simulator.md). Answer semantically equivalent or combined
questions without naming the expected specialist, method or scoring issue.
Prioritize the consequential question and closely related facts; record other
unanswered questions and disclosed fact IDs privately. An unlisted fact is unknown
unless a frozen acquisition rule covers it. Do not reveal a hidden file merely
because the consultant has stalled.

Distinguish an ambiguous reply from an explicit unknown, unavailable source or
declined action. Clarifying the former may help; repeatedly probing the latter
does not create evidence. User expertise changes vocabulary, not scientific facts.
Optional register variants need their own IDs and frozen fact-equivalence checks.

Observe actual sequential turns and at most one substantive specialist review per
assistant turn; synthesis or clarification can require none. Freeze candidate,
transport/configuration, caps and observability before launch. Count recoverable
all-agent usage, tools, retries and user turns. Evaluate completion against the
objective, not fixed turns. A resource stop is not automatically useful completion.

## V7P01: What event does this date describe?

**Public objective and starting material.** Audit whether enrollment and visit
records can support a person-level table of eligibility, first completed visit
and observed follow-up. Then prepare that table when the necessary rules are
clear. Provide a cohort roster, a booking extract, a short dictionary and a
documented person key. The initial request authorizes the audit, not effect
estimation; the user authorizes preparation after the audit's consequential
questions are resolved. The dictionary calls `start_date` the service start.

**Private truth and user knowledge.** `start_date` is when a booking was created,
not when service occurred. The operations researcher knows this process but
initially uses the same informal word "start." A separate appointment-event
export is available on request. It contains actual service timestamps, cancelled
and unattended appointments, and status revisions keyed by appointment ID.
Its coverage starts after some cohort members enrolled. The user knows the
coverage dates and documented rule for retaining the latest status revision;
they do not know an unrecorded visit date or certify a causal assumption.

**Semantic response triggers.** A general meaning question gets the truthful
but ambiguous reply "That is when they start." A question about the event or
action creating the entry gets the booking definition immediately, even if it
is the first question. A request for attendance, service-event or appointment
history records releases the event export and its dictionary, without prescribing
a join or analysis. A request for its coverage or revision rule supplies those
facts unless already documented. Earlier service dates outside the available
coverage are unknown. Do not produce a missing record or invent no attendance.

**Progression and acceptable alternatives.** An actual audit identifies the
material ambiguity; the specialist handoff and lead's user-facing question need
not use identical words. The attributed answer changes the date interpretation,
and the newly requested source changes the preparation plan. A combined factual
question is acceptable. So is a supported partial table that explicitly preserves
unresolved histories. Once asked for supported preparation, execute it; do not
require a design label first or append an independent causal review in that turn.

**Completion and oracle.** Before running, freeze row-level expected retained
appointment revisions, matched and unmatched IDs, duplicate dispositions,
eligibility, first completed visit and observation-window flags. Include at least
one cancellation, later rebooking, unmatched event and left-censored history.
The author must define which absence can mean zero and which must remain unknown.
Check the actual derived rows and reconciliation counts, source hashes and
reproducible transformation against that truth. Completion includes the table
and its implications for feasible analyses, not merely receipt of the new file.
Accept different correct implementations. Treat booking as attendance, silent
row multiplication, false baseline labels or source overwrite as material errors.

## V7P02: An analysis that is ready now

**Public objective and starting material.** Explicitly request execution of a
simple synthetic randomized-study analysis: estimate the finite cohort's average
assignment effect, give design-appropriate uncertainty and explain its limits.
Supply a complete assignment protocol, realized allocation log, outcome table,
dictionary and locally staged authoritative design-based methods reference.
There are 12 eligible units, exactly six assigned to each arm by uniform complete
randomization, one complete outcome per unit, no interference, noncompliance,
attrition, clustering or missing design information. These are declared properties
of the synthetic experiment, not empirical claims inferred from balance tests.

**Private truth and user knowledge.** To construct the fixture, use potential
outcomes $Y_i(0)=2i$ and $Y_i(1)=2i+3$ for $i=1,\ldots,12$. Freeze one allocation
drawn under the declared scheme and expose only its observed outcomes. The user
knows the protocol and requested target, not the unobserved outcomes or reference
answers. The known finite-population effect is 3; the realized difference in
means need not equal 3. Do not grade that sampling variation as an error.

**Semantic response triggers.** Refer briefly to documented facts; count redundant
reconfirmation as friction. The user does not have hidden potential outcomes. If a defect
prevents execution, record a fixture/environment failure, not a successful pause.
Do not add new study complications mid-consultation.

**Progression and acceptable alternatives.** The clear request should reach one
meaningful specialist analysis in the first assistant turn without an approval
ceremony. A design-based estimate with conservative Neyman uncertainty is valid;
an exact sharp-null randomization test may supplement it, but is not by itself
an interval for the average effect. An approximate interval must be labelled as
such for this small sample. Other justified estimators or uncertainty procedures
are acceptable with a matching independently checked reference. Do not require
one package, confuse treatment receipt with assignment, or assume generalization
beyond the finite cohort.

**Completion and numeric oracle.** The fixture author independently computes
the realized difference in means and $s_1^2/6+s_0^2/6$, the conventional conservative
Neyman variance estimate. Enumerate all $\binom{12}{6}=924$ allocations to check
the design and any reported exact sharp-null test, freezing its statistic and
tail convention. A constant-effect inversion needs its additional hypothesis
stated. Check submitted code, numeric outputs and uncertainty interpretation,
using prespecified tolerances and an oracle not derived from consultant output.
Completion is the requested reproducible estimate and uncertainty explanation.
If the user then requests a plain-language recap, use the existing result without
another specialist or an unnecessary rerun. Record this synthesis separately.

## V7P03: Useful advice when assignment cannot be recovered

**Public objective and starting material.** Advise whether an existing service
rollout can support a causal effect estimate and what is useful to do now.
Provide a small panel, outcome/timing dictionaries and administrative-file inventory.
The user cannot collect new data this month and delegates one bounded investigation.
One apparent coverage gap has a cheap local answer.

**Private truth and user knowledge.** The researcher knows that the extract
contains applying sites, not every eligible site, and can immediately provide
the listed file resolving the coverage gap. Historic scheduling records are
lost; surviving staff cannot explain assignment, and further contact is declined.
Comparable papers cannot recover this local fact. The ledger makes no claim that
unexplained assignment is necessarily random or necessarily confounded.

**Semantic response triggers.** Questions about extraction/population receive
the application-only fact. Requests for the relevant coverage file receive it.
Questions about assignment records or staff availability receive the declared
unknown, loss and contact boundary. Once limitations are established, the user
asks for advice using what exists. Requests outside the inventory remain unknown
or unavailable; no new archive or paper is invented to rescue identification.

**Progression, completion and oracle.** Accept multiple proportionate first
investigations. A short knowledgeable-user question can beat another data check
when the issue is operational meaning. Freeze coverage/denominator truth and any
descriptive calculation used for review; there is no numerical causal-effect
oracle based on an undisclosed assignment mechanism. Completion is actionable
advice distinguishing established facts, conditional identifying assumptions and
unsupported claims. It may recommend descriptive work, a conditional design with
specific limitations, an agreed narrower target or future evidence collection.
It must not silently replace the original target, equate good pretrends with
verified assignment, withhold all advice, or keep requesting declined sources.
Stopping after giving useful limited advice can be a success.

## V7P04: Correct the consultant's own earlier decision

**Public objective and starting material.** Assess an intervention offer's
effect using cohort-labelled data, a dated allocation manual and the user's
initial account that the manual applies. These credibly support a provisional
randomized-offer interpretation. The initial request authorizes a readiness or
design review, not automatic estimation.

**Private truth and staged user knowledge.** The manual actually describes
another cohort. The researcher initially believes it applies, without certainty
beyond the supplied evidence. Later a corrected administrative memo establishes
the mismatch: the analysis cohort's exposure records chosen attendance, and its
offer assignment cannot be recovered. Baseline variables and outcomes remain
usable. Before receiving that memo, the user cannot truthfully certify its facts.

**Semantic triggers and resume.** Wait for the consultant's actual first review
and durable recommendation, including a conditional one. Close the client and
resume the exact returned session in the same project, with identities recorded.
The user supplies the new memo and correction, asks what can now be learned, and
chooses or delegates a justified bounded follow-up. Do not inject a hidden summary
of prior conversation. If the mismatch is found earlier, credit the reasoning but
mark the correction objective unexercised. Never force a false first decision.

**Completion and oracle.** Freeze the two cohort identities, variable meanings,
source chronology and correction's dependency consequences. Check that the new
advice and current records retract or qualify every affected earlier assignment
claim and strategy, while retaining unaffected facts and historical reviews.
The original offer target must remain distinct from attendance or descriptive
alternatives; changing the target needs user direction. A useful limited answer
can complete the objective, and one justified follow-up review is allowed in a
later turn. An event saying "corrected" is insufficient if current advice still
relies on the superseded premise. Rewriting history, asking the user to reconstruct
available prior reasoning or presenting attendance as randomized offer fails.
