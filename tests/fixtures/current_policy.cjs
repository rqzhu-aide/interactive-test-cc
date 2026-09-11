"use strict";
// Synthetic saved-contract fixture. These records alone are NOT observed user
// consent; the Python observer tests compare them with actual public messages.
const path = require("node:path");
const fs = require("node:fs");
const crypto = require("node:crypto");
module.exports = function prepare(scripts, root, plan, suffix, offered = null, prepareOnly = false) {
  const store = require(path.join(scripts, "lib/store.cjs"));
  const policy = require(path.join(scripts, "lib/authorizations.cjs"));
  for (const input of plan.inputs) input.sha256 = crypto.createHash("sha256").update(fs.readFileSync(input.path)).digest("hex");
  const protocol = "durable-exchanges-v1";
  const state = () => store.readJournal(root).state;
  const record = (type, payload, name) => store.record(root, {event_id:"event-"+name,
    expected_project_id:state().state_meta.project_id,expected_last_event_id:state().state_meta.last_event_id,type,payload});
  function interpret(name, action, extra = {}, user = "Test-only source review request.") {
    const userRef="user-"+name;
    const value={interpretation_id:"interpretation-"+name,turn_id:"turn-"+name,incoming_refs:[userRef],
      basis_refs:[],components:[{kind:"instruction",meaning:user,established:[user],unresolved:[]}],next_action:action,...extra};
    record("reply_interpreted",{protocol,changes:{evidence:[{evidence_id:userRef,kind:"user_statement",source_ref:"conversation:"+userRef,
      source_excerpt:user,summary:user}]},interpretation:value},"interpret-"+name);
    return value;
  }
  function exchange(it, name, response, completed=[]) {
    const receipt=record("exchange_prepared",{protocol,exchange:{exchange_id:"exchange-"+name,turn_id:it.turn_id,
      interpretation_ref:it.interpretation_id,basis_refs:[],completed_work_refs:completed,renderer:"lead-markdown-v4",
      reconciliation:{changes:[],limitations:["Synthetic structural test only."],unresolved:[],next_direction:"The user chooses."},response}},"exchange-"+name);
    const delivery="delivery-"+name;
    record("exchange_delivery",{protocol,delivery:{delivery_id:delivery,exchange_ref:receipt.exchange_id,
      observation:"assistant_emission",source_ref:"conversation:assistant-"+name,
      response_sha256:state().exchanges.find(x=>x.exchange_id===receipt.exchange_id).response_sha256}},"delivery-"+name);
    return {...receipt,delivery_ref:delivery};
  }
  if(plan.kind==="audit"){
    const it=interpret("audit-"+suffix,{kind:"specialist",assignment:{specialist_id:"data_audit",operation:"review"},scope:"Inspect fixture sources.",reason:"Test-only audit."});
    return {...plan,interpretation_ref:it.interpretation_id,operations:["data_quality"]};
  }
  if(!offered){
    const name="review-"+suffix;
    const assignment={specialist_id:"data_audit",operation:"review"};
    const it=interpret(name,{kind:"specialist",assignment,scope:"Inspect the supplied source.",reason:"State the source limits before reporting."});
    record("checkpoint",{checkpoint:{checkpoint_id:"checkpoint-"+name,status:"assessing",primary_uncertainty:"Source interpretation",why_it_matters:"Keep the report bounded."}},"checkpoint-"+name);
    const review={review_id:"review-"+name,summary:"The source supports a test-only account.",assignment,question_addressed:"What does this fixture source support?",
      selection_basis:{checkpoint_id:"checkpoint-"+name,user_contribution_refs:it.incoming_refs},interpretation_ref:it.interpretation_id,
      work_performed:["Read the synthetic source bytes and inspect provenance."],findings:["A synthetic source is present."],limitations:["No causal identification is claimed."],evidence_refs:plan.evidence_refs};
    record("review_completed",{review},"completed-"+name);
    exchange(it,name,{status:"Source review is complete.",questions:[],questions_none:"No source questions remain in this fixture.",next_steps:[],next_steps_none:"Discuss findings or pause.",
      findings:{work_refs:[review.review_id],summary:"The synthetic source supports a limited account.",diagnostics:["Inspected source provenance."],limitations:["Test fixture only."]}},[review.review_id]);
    const proposal=interpret("proposal-"+suffix,{kind:"lead_only",scope:"Present the report scope.",reason:"A later choice is required."});
    const refs=policy.requiredBasisRefs(state(),[...plan.evidence_refs,review.review_id]);
    const reportAssignment={specialist_id:"report_writer",operation:"reporting"};
    const scope={scope_id:"scope-"+suffix,action:"report",assignment:reportAssignment,
      public_scope:{target:plan.purpose,population:"Population described by the supplied source",evidence:"The supplied source and its review",
        approach:"Synthesize the discussed source evidence",checks:[],outputs:plan.format+" report",claim_boundary:plan.claim_boundary},
      execution_plan:plan,basis_versions:refs.map(ref=>({ref,event_ref:state().history_index[ref].event_ref})),findings_refs:[review.review_id]};
    record("memory_updated",{changes:{action_scopes:[scope]}},"scope-"+suffix);
    const receipt=exchange(proposal,"proposal-"+suffix,{status:"Here is the proposed report scope.",questions:[],questions_none:"No additional information is needed to choose.",
      next_steps:[{option_id:"choose-"+suffix,kind:"action",label:"Save this report",actor:"consultant",scope:"Use the presented scope.",basis_refs:refs,
        assignment:reportAssignment,scope_ref:scope.scope_id,proposal:scope.public_scope,execution_plan:plan}],
      findings:{work_refs:[review.review_id],summary:"The source permits a limited account.",diagnostics:["Source provenance was reviewed."],limitations:[plan.claim_boundary]}});
    offered={scope,exchange_ref:receipt.exchange_id,option_id:"choose-"+suffix,delivery_ref:receipt.delivery_ref,rendered_response:receipt.rendered_response};
  }
  if(prepareOnly) return {offered};
  const user="I choose the proposed report scope exactly as presented.";
  const name="accept-"+suffix;
  const decisionId="decision-"+name;
  const selected=interpret(name,{kind:"specialist",scope:"Write the chosen report.",reason:"The user selects the report scope.",
    assignment:offered.scope.assignment,scope_ref:offered.scope.scope_id,authorization_ref:decisionId},{
    components:[{kind:"selection",meaning:user,established:[user],unresolved:[],exchange_ref:offered.exchange_ref,option_id:offered.option_id,delivery_ref:offered.delivery_ref}],
    action_decisions:[{decision_id:decisionId,scope_ref:offered.scope.scope_id,disposition:"accept",exchange_ref:offered.exchange_ref,
      option_id:offered.option_id,delivery_ref:offered.delivery_ref,user_refs:["user-"+name]}]},user);
  return {...plan,interpretation_ref:selected.interpretation_id,scope_ref:offered.scope.scope_id,authorization_ref:decisionId};
};
