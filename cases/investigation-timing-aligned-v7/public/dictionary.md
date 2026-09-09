# Synthetic study dictionary

This is a wholly invented study, not a historical educational dataset.

Each row is one site on the fixed eligible roster; IDs are unique and stable. `grant_offer` is 1 for a program offer and 0 otherwise. All eligible sites have one complete primary outcome.

`entrants` is the number of full-time first-time entrants in the 2020 cohort, 100 at every site. `completion_2024_pct` is the percentage of that cohort completing a credential by 2024-09-01. The registrar verified the complete 2020 roster and primary outcome counts against its final register.

`baseline_completion_pct` is a separate prior cohort's four-year completion percentage, recorded before 2020. It is not the denominator or source of the 2020 cohort outcome. It has not been verified against its original register. No corrected baseline file is available.

The consortium program is a fixed package of extra advising sessions and extra required-course sections, funded at $1,000 per entering student in each of four academic years. `grant_offer` records whether the site was offered that package; all offered sites accepted it, and all other sites continued usual services. Grant spending does not replace other funding. The outcome unit is percentage points. The fixed target population is these 24 sites, equally weighted. There is no student movement between sites, interference, attrition or missing primary outcome in this synthetic pilot.

The export includes a grant-offer flag and a 2020-cohort outcome but does not encode the offer date or funded service years. A separate program calendar contains those dates. Do not infer dates from the order of columns.
