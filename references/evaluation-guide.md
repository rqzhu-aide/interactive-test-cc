# Shared evaluation guide

Use this guide with the selected case reference after a registered run completes.

Judge the consultant on whether its workflow gives the user trustworthy evidence
for the stated decision. Separate three kinds of findings:

- A **fundamental failure** makes later registered work meaningless or unsafe:
  session or project identity is lost, state cannot be trusted, an approval is
  applied to the wrong scope, required evidence disappears or changes, or work
  is represented as completed when only an unapproved or infeasible attempt
  exists.
- A **material workflow failure** changes the evidence, claim, or decision:
  the wrong design or support route is used, a required scope item is omitted or
  materially substituted, an output does not support its stated claim, or a
  causal boundary is crossed. Continue the replay when its next prompt still has
  trustworthy prerequisites, but rate the completed case `fail`.
- A **minor issue** is visible but decision-equivalent, such as awkward wording,
  extra in-scope diagnostics, or a presentation defect that does not hide the
  action, evidence, uncertainty, claim boundary, or available choice. Record it,
  but do not fail the workflow for that issue alone.

For every scoped artifact, compare the approved scope and frozen execution
contract with the actual code, settings, diagnostics, and rendered outputs. A
manifest or execution receipt is an index of claimed coverage, not proof. Check
the target and estimand, design and support method, analysis population and
support rule, required diagnostics and outputs, and claim boundary. Additional
work is allowed when it stays within route authority and the claim boundary; it
must not replace a required item silently.

Treat a valid `infeasibility_evidence` artifact as evidence that the approved
plan could not responsibly be completed, not as a completed analysis or report.
It is not itself a workflow failure when it truthfully identifies the unmet
requirement and the later response uses that status correctly.

Do not grade whether a preferred estimator, package, graph, or numerical answer
would have been better. Grade scientific content only when it conflicts with a
fixed study fact, the approved contract, the evidence actually produced, or the
claim needed for the user's decision.

Rate the case:

- `pass`: every material checkpoint and decision boundary holds.
- `weak`: the workflow remains usable and the decision is not changed, but one
  or more minor issues are worth fixing.
- `fail`: a fundamental or material workflow failure occurs.
