# Standard Tests

Two standard configurations: Setting A (default, 13 turns) and Setting B (deep, 12 turns).

---

## Setting A (13 turns) — Default

The primary benchmark. Precheck gates on analysis (turns 8, 10), report (turn 12), and PPT summary (turn 13). Reports output HTML by default.

### Turn Table

| Turn | What you say |
|------|-------------|
| 1 | Load skill, domain opening |
| 2 | Deeper domain question |
| 3 | **"Here is the data — data.csv, take a look"** |
| 4 | Follow up on data exploration |
| 5 | Causal or method question based on data |
| 6 | Probe a specific finding or edge case |
| 7 | **Ask for analysis** |
| 8 | Confirm analysis (precheck gate) |
| 9 | **Ask for additional analysis** |
| 10 | Confirm additional analysis (precheck gate) |
| 11 | **Ask for report** (HTML by default) |
| 12 | Confirm report (precheck gate) |
| 13 | **Ask for a 3-slide PPT summary** |

### Prompts

#### Turn 1 — Intake
> Use the causal-consultant skill. I'm studying what drives college graduation rates. I have data on 777 US colleges — admissions, selectivity, spending, faculty stats. I want to identify the causal factors that most strongly predict graduation outcomes so we can make policy recommendations.

#### Turn 2 — Deeper Domain
> The policy angle is important — my stakeholders are state education boards who set funding. What's the right framework for thinking about causal effects when the goal is actionable policy? I don't want just correlations.

#### Turn 3 — Data Intro
> Here is the data — data.csv. Take a look. I want to understand what we're working with before we dive into analysis.

#### Turn 4 — Follow Up
> What patterns stand out to you? Anything surprising in the distributions or correlations?

#### Turn 5 — Causal Question
> OK, let's get into it. What do you think is the most important causal factor for graduation rates? Based on what you see in the data, what should we analyze first?

#### Turn 6 — Edge Case
> Interesting. What about schools with very high or very low values — are there threshold effects? Does the relationship look different at the extremes?

#### Turn 7 — Analysis Request
> Let's run the analysis. Start with the key causal factor you identified.

#### Turn 8 — Confirm
> Makes sense. Walk me through what this means — what did we actually find, and how confident should we be?

#### Turn 9 — Additional Analysis
> Now let's look at another angle. What other causal factors should we examine? Run that analysis too.

#### Turn 10 — Confirm
> Good. How do these results compare to the first analysis? Do they reinforce or contradict each other?

#### Turn 11 — Report Request
> We have enough. Write up a full report — HTML format, include the key figures and tables.

#### Turn 12 — Confirm
> Review the report. Any caveats or limitations we should add? Is there anything we're overstating?

#### Turn 13 — PPT Summary
> One more thing — give me a 3-slide PPT summary of the key findings for my board presentation.

### Evaluation

Standard 2/3 shape marker check per turn ([> Framing], [+ Consultant Options], [? Next Steps]).

Report 5-field summary: Turns, Shape, Output, YAML, Tokens.

---

## Setting B (12 turns) — Deep

Extended deep analysis. Data ≥ turn 4. Report ≥ turn 8. HTML at turn 10. Unconventional quota: ≥3 turns in 8–12 (HTML turn 10 does NOT count).

### Turn Table

| Turn | Gate | Action |
|------|------|--------|
| 1 | No data, no report | Domain-aligned opening |
| 2 | No data, no report | Deepen domain conversation |
| 3 | No data, no report | Continue domain discussion |
| 4 | Data allowed | Natural data introduction |
| 5–7 | Data allowed | Discuss dataset, bridge to analysis |
| 8 | Report allowed | First analysis request |
| 9 | All open | Method comparison, interpretation |
| 10 | All open | **Must ask for HTML report** |
| 11 | All open | Unconventional angle |
| 12 | All open | Synthesis / next steps |

### Prompts

Ad-lib from the turn table. Key constraints: data intro at T4, first analysis at T8, HTML report at T10, ≥3 unconventional angles in T8–12.

### Evaluation

Same as Setting A. Unconventional quota is a bonus metric, not a hard gate.
