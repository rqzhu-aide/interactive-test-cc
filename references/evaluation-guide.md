# Shared evaluation guide

Use this guide with the selected case reference after a registered run completes.

Start from the generated evaluation dossier. Treat passing checks for outer-session
and project continuity, controller closure, scope identity, manifest and receipt
structure, file hashes, and HTML references as mechanically established. Reopen
raw evidence only when the dossier reports a failure or a semantic question cannot
be resolved from its transcript and artifact excerpts. Do not grade the runtime
provider or fast-mode setting.

Internal router, worker, and team-lead phases may use fresh contexts. Their phase
capsules and `.statectl-tmp/phase-context.json` are temporary transport, not
qualitative evidence. Absence of internal trace evidence means phase isolation was
not observed, not that it failed. Record a protocol issue only when direct evidence
establishes one. Treat transport-reported agent turns, tokens, API time, and cost as
descriptive efficiency telemetry rather than correctness criteria or user turns.

For HTML, the dossier supplies readable visible text while the runner checks
links and file integrity. Open the saved HTML in a renderer only when layout,
figure legibility, or another visual promise is part of the approved scope.

Judge the consultant on whether its workflow gives the user trustworthy evidence
for the stated decision. Separate three kinds of findings:

- A **fundamental failure** makes later registered work meaningless or unsafe:
  session or project identity is lost, state cannot be trusted, an approval is
  applied to the wrong scope, required evidence disappears or changes, or work
  is represented as completed when only an unapproved or infeasible attempt
  exists.
- A **material workflow failure** changes the evidence, claim, or decision:
  a design or support route conflicts with a fixed case requirement or the
  approved scope, a required scope item is omitted or materially substituted, an
  output does not support its stated claim, or a
  causal boundary is crossed. Continue the replay when its next prompt still has
  trustworthy prerequisites, but rate the completed case `fail`.
- A **minor issue** is visible but decision-equivalent, such as awkward wording,
  extra in-scope diagnostics, or a presentation defect that does not hide the
  action, evidence, uncertainty, claim boundary, or available choice. Record it,
  and rate the case `weak` when it warrants correction.

For every scoped artifact, compare the approved scope and frozen execution
contract with the actual code, settings, diagnostics, and rendered outputs. A
manifest or execution receipt is an index of claimed coverage, not proof. Check
the target and estimand, design and support method, analysis population and
support rule, required diagnostics and outputs, and claim boundary. Additional
work is allowed when it stays within route authority and the claim boundary; it
must not replace a required item silently.

Trace any identification condition that causal review calls necessary or
unresolved through the approved scope, execution evidence, report, and final
advice. Until evidence resolves it, later causal wording must retain it as a
condition on the claim rather than reduce it to a general caveat. Judge any
dilution by whether it changes the evidence, claim, or decision.

When a prompt or approved scope requests one priority, judge functional
cardinality. Multiple independent alternatives are a mismatch; inseparable
parts of one action are not. Rate the mismatch by its effect on the user's
choice or use of resources, not by wording such as the presence of `or`.

Treat a valid `infeasibility_evidence` artifact as evidence that the approved
plan could not responsibly be completed, not as a completed analysis or report.
It is not itself a workflow failure when it truthfully identifies the unmet
requirement and the later response uses that status correctly.

Do not grade whether a preferred estimator, package, graph, or numerical answer
would have been better. Grade scientific content only when it conflicts with a
fixed study fact, the approved contract, the evidence actually produced, or the
claim needed for the user's decision.

Apply the highest applicable rating:

- `fail`: a fundamental or material workflow failure occurs.
- `weak`: the workflow remains usable and the decision is not changed, but one
  or more minor issues are worth fixing.
- `pass`: all material checkpoints and decision boundaries hold, and no
  observed defect warrants correction.

Record only defects in the structured `findings` list. Use `minor`, `material`,
or `fundamental` as the severity. The finalizer derives `weak` from any minor
finding and `fail` from any material or fundamental finding; an empty list
derives `pass`.
