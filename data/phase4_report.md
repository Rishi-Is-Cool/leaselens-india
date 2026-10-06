# Phase 4 - explanation layer, cross-clause detection, grounding guardrail

Run on 9 Phase 1 test documents (92 clauses total). Reproduce with `python scripts/run_phase4.py` from `backend/`.

## Jurisdiction inference (a hint, not a selection mechanism - see PROGRESS.md)

Scanned each document's own clause text (never the title block) for city/state signals; scored against the known state each fixture represents. **9/9 correct.**

| Document | Known | Inferred | Unsupported hint | Ambiguous | Correct |
|---|---|---|---|---|---|
| 01_maharashtra_leave_license_mumbai.pdf | Maharashtra | Maharashtra | - | False | yes |
| 02_delhi_rent_agreement.pdf | Delhi | Delhi | - | False | yes |
| 03_karnataka_rental_agreement_bangalore.pdf | - | - | Karnataka | False | yes |
| 04_tamil_nadu_lease_agreement_chennai.pdf | - | - | Tamil Nadu | False | yes |
| 05_uttar_pradesh_lease_deed_lucknow.pdf | - | - | Uttar Pradesh | False | yes |
| 06_west_bengal_tenancy_agreement_kolkata.pdf | - | - | West Bengal | False | yes |
| 07_punjab_rent_deed_chandigarh.pdf | - | - | Punjab | False | yes |
| 08_rajasthan_leave_license_jaipur.pdf | - | - | Rajasthan | False | yes |
| 09_gujarat_rent_agreement.pdf | - | - | Gujarat | False | yes |

No user confirmation step exists yet for this hint - that is Phase 5/6 work.

## Grounding guardrail pass rate

**100.0%** (10/10 clauses that reached grounding check; 82 clause(s) failed before reaching it - counted separately below, not folded into the pass rate, since a pipeline error is a different failure mode than an ungrounded explanation).

| Document | Jurisdiction | Clauses | Grounded | Errors | Cross-clause found |
|---|---|---|---|---|---|
| 01_maharashtra_leave_license_mumbai.pdf | Maharashtra | 13 | 10/10 | 3 | 0 |
| 02_delhi_rent_agreement.pdf | Delhi | 12 | 0/0 | 12 | 0 |
| 03_karnataka_rental_agreement_bangalore.pdf | (unsupported) | 12 | 0/0 | 12 | 0 |
| 04_tamil_nadu_lease_agreement_chennai.pdf | (unsupported) | 7 | 0/0 | 7 | 0 |
| 05_uttar_pradesh_lease_deed_lucknow.pdf | (unsupported) | 12 | 0/0 | 12 | 0 |
| 06_west_bengal_tenancy_agreement_kolkata.pdf | (unsupported) | 10 | 0/0 | 10 | 0 |
| 07_punjab_rent_deed_chandigarh.pdf | (unsupported) | 8 | 0/0 | 8 | 0 |
| 08_rajasthan_leave_license_jaipur.pdf | (unsupported) | 10 | 0/0 | 10 | 0 |
| 09_gujarat_rent_agreement.pdf | (unsupported) | 8 | 0/0 | 8 | 0 |

## Grounding failures, with reasons

- **01_maharashtra_leave_license_mumbai.pdf / c010**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 198654, Reque
- **01_maharashtra_leave_license_mumbai.pdf / c012**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199676, Reque
- **01_maharashtra_leave_license_mumbai.pdf / c013**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199675, Reque
- **02_delhi_rent_agreement.pdf / c001**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199671, Reque
- **02_delhi_rent_agreement.pdf / c002**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199671, Reque
- **02_delhi_rent_agreement.pdf / c003**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199671, Reque
- **02_delhi_rent_agreement.pdf / c004**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199670, Reque
- **02_delhi_rent_agreement.pdf / c005**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199670, Reque
- **02_delhi_rent_agreement.pdf / c006**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199670, Reque
- **02_delhi_rent_agreement.pdf / c007**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199669, Reque
- **02_delhi_rent_agreement.pdf / c008**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199669, Reque
- **02_delhi_rent_agreement.pdf / c009**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199669, Reque
- **02_delhi_rent_agreement.pdf / c010**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199668, Reque
- **02_delhi_rent_agreement.pdf / c011**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199668, Reque
- **02_delhi_rent_agreement.pdf / c012**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199667, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c001**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199660, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c002**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199660, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c003**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199660, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c004**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199659, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c005**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199659, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c006**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199659, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c007**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199658, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c008**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199658, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c009**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199657, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c010**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199657, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c011**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199657, Reque
- **03_karnataka_rental_agreement_bangalore.pdf / c012**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199656, Reque
- **04_tamil_nadu_lease_agreement_chennai.pdf / c001**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199648, Reque
- **04_tamil_nadu_lease_agreement_chennai.pdf / c002**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199647, Reque
- **04_tamil_nadu_lease_agreement_chennai.pdf / c003**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199647, Reque
- **04_tamil_nadu_lease_agreement_chennai.pdf / c004**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199646, Reque
- **04_tamil_nadu_lease_agreement_chennai.pdf / c005**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199646, Reque
- **04_tamil_nadu_lease_agreement_chennai.pdf / c006**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199645, Reque
- **04_tamil_nadu_lease_agreement_chennai.pdf / c007**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199645, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c001**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199639, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c002**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199639, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c003**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199639, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c004**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199638, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c005**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199638, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c006**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199638, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c007**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199637, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c008**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199637, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c009**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199637, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c010**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199636, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c011**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199636, Reque
- **05_uttar_pradesh_lease_deed_lucknow.pdf / c012**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199636, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c001**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199631, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c002**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199631, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c003**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199630, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c004**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199630, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c005**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199630, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c006**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199630, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c007**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199629, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c008**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199629, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c009**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199629, Reque
- **06_west_bengal_tenancy_agreement_kolkata.pdf / c010**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199629, Reque
- **07_punjab_rent_deed_chandigarh.pdf / c001**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199625, Reque
- **07_punjab_rent_deed_chandigarh.pdf / c002**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199624, Reque
- **07_punjab_rent_deed_chandigarh.pdf / c003**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199624, Reque
- **07_punjab_rent_deed_chandigarh.pdf / c004**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199624, Reque
- **07_punjab_rent_deed_chandigarh.pdf / c005**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199623, Reque
- **07_punjab_rent_deed_chandigarh.pdf / c006**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199623, Reque
- **07_punjab_rent_deed_chandigarh.pdf / c007**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199623, Reque
- **07_punjab_rent_deed_chandigarh.pdf / c008**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199623, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c001**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199619, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c002**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199618, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c003**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199618, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c004**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199618, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c005**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199618, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c006**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199617, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c007**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199617, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c008**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199617, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c009**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199616, Reque
- **08_rajasthan_leave_license_jaipur.pdf / c010**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199616, Reque
- **09_gujarat_rent_agreement.pdf / c001**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199612, Reque
- **09_gujarat_rent_agreement.pdf / c002**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199612, Reque
- **09_gujarat_rent_agreement.pdf / c003**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199612, Reque
- **09_gujarat_rent_agreement.pdf / c004**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199612, Reque
- **09_gujarat_rent_agreement.pdf / c005**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199611, Reque
- **09_gujarat_rent_agreement.pdf / c006**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199611, Reque
- **09_gujarat_rent_agreement.pdf / c007**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199611, Reque
- **09_gujarat_rent_agreement.pdf / c008**: PIPELINE ERROR - explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_[redacted]` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199611, Reque

## Cross-clause connections found

(none found)

## Sample explanations (for manual review)

**01_maharashtra_leave_license_mumbai.pdf / c001** — risk: GREEN (confidence 0.98), topic: none, retrieved: none, grounded: True

> Clause: THIS LEAVE AND LICENSE AGREEMENT is made and executed at Mumbai on this 3rd day of March, 2026, BETWEEN Mr. Ramesh Kulkarni, residing at Flat No. 302, Sai Krupa CHS, S.V. Road, Andheri West, Mumbai - 400058 (hereinafter referred to as the “LICENSOR”) AND Ms. Priya Deshmukh, residing at 14, Green Par

- **Document says:** The clause identifies the agreement as a Leave and License Agreement executed in Mumbai on March 3, 2026, between Mr. Ramesh Kulkarni (Licensor) and Ms. Priya Deshmukh (Licensee), including their respective residential addresses.
- **Concern:** This is standard introductory language that clearly defines the parties and the nature of the agreement, presenting no specific risk or imbalance.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c002** — risk: GREEN (confidence 0.98), topic: none, retrieved: none, grounded: True

> Clause: WHEREAS the Licensor is the absolute owner of Flat No. 604, Om Sai Residency, CTS No. 412/A, Plot No. 9, Andheri West, Mumbai - 400058, admeasuring 620 sq. ft. carpet area (hereinafter referred to as the “SAID PREMISES”), and the Licensee has approached the Licensor to use and occupy the said premis

- **Document says:** The clause identifies the Licensor as the absolute owner of a specific flat in Mumbai and states that the Licensee has requested to occupy the premises on a leave and license basis, which the Licensor has agreed to grant subject to the terms in the document.
- **Concern:** This is standard introductory language that establishes the parties' roles and the nature of the occupancy arrangement without imposing unusual restrictions or liabilities.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c003** — risk: RED (confidence 0.80), topic: none, retrieved: none, grounded: True

> Clause: The Licensor hereby grants to the Licensee a purely personal, non-transferable license to use and occupy the said premises, and this Agreement does not create any tenancy, lease, or other interest in favour of the Licensee, nor any relationship of landlord and tenant between the parties.

- **Document says:** The document explicitly states that the arrangement is a 'purely personal, non-transferable license' and asserts that it does not create a tenancy, lease, or landlord-tenant relationship.
- **Concern:** This clause attempts to legally recharacterize the occupancy as a license rather than a lease, which may limit your statutory rights (such as protection from eviction or rent control) that typically apply to tenants. A court might view this as an attempt to bypass mandatory housing protections, especially if the arrangement involves exclusive possession for a fixed term in exchange for payment, which are hallmarks of a tenancy.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c004** — risk: GREEN (confidence 0.95), topic: none, retrieved: none, grounded: True

> Clause: This license shall be for a period of 11 (eleven) months commencing from 1st April 2026 and ending on 28th February 2027, and shall not be renewed or extended automatically.

- **Document says:** The agreement is a license for a fixed term of 11 months, starting on April 1, 2026, and ending on February 28, 2027, with no provision for automatic renewal or extension.
- **Concern:** This is standard, balanced language that clearly defines the duration of the tenancy and explicitly prevents automatic rollover, which helps avoid ambiguity regarding the end date.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c005** — risk: GREEN (confidence 0.90), topic: none, retrieved: none, grounded: True

> Clause: The Licensee shall pay to the Licensor a monthly license fee of Rs. 38,000/- (Rupees Thirty-Eight Thousand only), payable in advance on or before the 5th day of each English calendar month, by NEFT/RTGS to the Licensor's designated bank account.

- **Document says:** The tenant is required to pay a monthly fee of Rs. 38,000 in advance by the 5th of each month via NEFT or RTGS to a specific bank account.
- **Concern:** This is standard, balanced language for a commercial license agreement, specifying a clear payment amount, due date, and method without unusual penalties or ambiguities.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c006** — risk: GREEN (confidence 0.85), topic: security_deposit, retrieved: ['MH_SEC_001'], grounded: True

> Clause: The Licensee has paid to the Licensor an interest-free refundable security deposit of Rs. 2,00,000/- (Rupees Two Lakhs only), the receipt of which the Licensor hereby acknowledges, to be refunded within 15 days of vacating the said premises, after deducting any amounts lawfully due.

- **Document says:** The Licensee has paid an interest-free refundable security deposit of Rs. 2,00,000/-, which the Licensor acknowledges. The deposit is to be refunded within 15 days of vacating the premises, after deducting any amounts lawfully due.
- **Concern:** This is standard and balanced language for a security deposit, specifying a clear refund timeline and the condition for deductions.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c007** — risk: GREEN (confidence 0.95), topic: maintenance, retrieved: ['MH_MAINT_001', 'MH_MAINT_002', 'CENTRAL_MAINT_002', 'CENTRAL_MAINT_003'], grounded: True

> Clause: The society maintenance charges shall be borne by the Licensor, while electricity charges as per actual sub-metered consumption shall be borne by the Licensee.

- **Document says:** The Licensor is responsible for society maintenance charges, while the Licensee is responsible for electricity charges based on actual sub-metered consumption.
- **Concern:** This is standard and balanced language that clearly allocates routine utility and maintenance costs between the parties without imposing unusual burdens on the tenant.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c008** — risk: GREEN (confidence 0.95), topic: none, retrieved: none, grounded: True

> Clause: The Licensee shall use the said premises for residential purposes only and shall not use the same for any commercial, illegal, or immoral purpose, nor create any sub-license or permit any third party to occupy the said premises.

- **Document says:** The clause restricts the tenant to using the property solely for residential purposes, explicitly prohibiting commercial, illegal, or immoral uses, and forbids the creation of sub-licenses or allowing any third party to occupy the premises.
- **Concern:** This is standard and balanced language commonly found in residential leases to ensure the property is used as intended and to prevent unauthorized occupancy.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c009** — risk: GREEN (confidence 0.85), topic: registration, retrieved: ['MH_REG_001', 'CENTRAL_REG_002', 'CENTRAL_REG_001', 'CENTRAL_REG_003'], grounded: True

> Clause: This Agreement shall be registered by the Licensor with the office of the Sub-Registrar of Assurances under Section 55 of the Maharashtra Rent Control Act, 1999, and the cost of stamp duty and registration shall be shared equally between the parties unless otherwise agreed in writing.

- **Document says:** The agreement must be registered by the Licensor with the Sub-Registrar of Assurances under Section 55 of the Maharashtra Rent Control Act, 1999. The costs for stamp duty and registration are to be shared equally between the parties, unless a different arrangement is agreed upon in writing.
- **Concern:** This is standard and balanced language. It aligns with the statutory requirement for registration of such agreements in Maharashtra and proposes a fair, 50/50 split of the associated administrative costs, which is a common and reasonable commercial term.
- **Statute support:** [{'entry_id': 'MH_REG_001', 'how_it_applies': "Section 55(1) of the Maharashtra Rent Control Act, 1999, mandates that agreements for leave and licence or letting of premises must be in writing and registered. The clause explicitly references this section, confirming the document's compliance with the local statutory requirement for registration."}]

**01_maharashtra_leave_license_mumbai.pdf / c011** — risk: GREEN (confidence 0.95), topic: notice, retrieved: ['CENTRAL_EVICTION_003', 'MH_NOTICE_001'], grounded: True

> Clause: The Licensor or his authorised representative shall be entitled to inspect the said premises at reasonable times upon giving 24 hours' prior notice to the Licensee.

- **Document says:** The landlord (Licensor) or their representative has the right to enter and inspect the property at reasonable times, provided they give the tenant (Licensee) 24 hours' prior notice.
- **Concern:** This is standard and balanced language. It grants the landlord a reasonable right to inspect the property while protecting the tenant's privacy by requiring advance notice and limiting entry to reasonable times.
- **Statute support:** none
