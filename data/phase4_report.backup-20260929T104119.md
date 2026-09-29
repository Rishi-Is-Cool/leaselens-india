# Phase 4 - explanation layer, cross-clause detection, grounding guardrail

Run on 1 Phase 1 test documents (13 clauses total). Reproduce with `python scripts/run_phase4.py` from `backend/`.

## Jurisdiction inference (a hint, not a selection mechanism - see PROGRESS.md)

Scanned each document's own clause text (never the title block) for city/state signals; scored against the known state each fixture represents. **1/1 correct.**

| Document | Known | Inferred | Unsupported hint | Ambiguous | Correct |
|---|---|---|---|---|---|
| 01_maharashtra_leave_license_mumbai.pdf | Maharashtra | Maharashtra | - | False | yes |

No user confirmation step exists yet for this hint - that is Phase 5/6 work.

## Grounding guardrail pass rate

**100.0%** (13/13 clauses that reached grounding check; 0 clause(s) failed before reaching it - counted separately below, not folded into the pass rate, since a pipeline error is a different failure mode than an ungrounded explanation).

| Document | Jurisdiction | Clauses | Grounded | Errors | Cross-clause found |
|---|---|---|---|---|---|
| 01_maharashtra_leave_license_mumbai.pdf | Maharashtra | 13 | 13/13 | 0 | 2 |

## Grounding failures, with reasons

(none)

## Cross-clause connections found

**01_maharashtra_leave_license_mumbai.pdf**: `c004` <-> `c010` (termination_conditions_and_duration)

Clause A establishes a fixed 11-month term that does not renew automatically, while Clause B provides a general right to terminate with one month's notice. Understanding Clause A is crucial for interpreting Clause B because the one-month notice period in Clause B effectively allows either party to exit the agreement at any point, potentially shortening the fixed 11-month term established in Clause A. Additionally, the 'default' termination right in Clause B operates independently of the fixed term, meaning a tenant could be removed before the February 2027 end date specified in Clause A if they miss two payments.

**01_maharashtra_leave_license_mumbai.pdf**: `c006` <-> `c010` (termination_and_deposit_refund)

Clause B outlines the conditions under which the agreement can be terminated, including a specific scenario where the Licensor can terminate 'forthwith' for payment default. Clause A states the security deposit is refunded 'after deducting any amounts lawfully due.' Understanding Clause B is necessary to interpret Clause A because a termination for default under Clause B likely triggers the 'amounts lawfully due' (such as unpaid license fees) that can be deducted from the deposit in Clause A, whereas a standard notice termination might not involve such deductions.


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

**01_maharashtra_leave_license_mumbai.pdf / c010** — risk: YELLOW (confidence 0.70), topic: eviction, retrieved: ['CENTRAL_EVICTION_003', 'MH_EVICTION_001', 'CENTRAL_EVICTION_004', 'MH_LICENCE_001', 'MH_EVICTION_004', 'MH_EVICTION_002', 'MH_EVICTION_003', 'MH_EVICTION_005'], grounded: True

> Clause: Either party may terminate this Agreement by giving one month's prior written notice to the other party. In the event the Licensee defaults in payment of the license fee for two consecutive months, the Licensor shall be entitled to terminate this Agreement forthwith and re-enter the said premises.

- **Document says:** The agreement allows either party to terminate the arrangement by providing one month's prior written notice. Additionally, if the Licensee fails to pay the license fee for two consecutive months, the Licensor is entitled to terminate the agreement immediately ('forthwith') and re-enter the premises.
- **Concern:** The clause grants the Licensor the right to terminate immediately and re-enter upon two months of non-payment without specifying a mandatory notice period or a cure period for the Licensee to remedy the default. While the document labels this a 'licence', if the arrangement is legally treated as a tenancy, a court might view the immediate re-entry right as potentially inconsistent with statutory protections that typically require a landlord to serve a specific notice of demand and allow a period (such as 90 days) for the tenant to pay arrears before eviction proceedings can be initiated. The lack of a defined cure period for the payment default could be a point of contention.
- **Statute support:** [{'entry_id': 'MH_EVICTION_001', 'how_it_applies': "This statute outlines that a landlord generally cannot recover possession if the tenant pays or is ready to pay rent, and specifically requires that no suit for recovery on the ground of non-payment be instituted until 90 days after a written notice of demand has been served. This contrasts with the clause's provision for immediate termination and re-entry after two months of default, suggesting that if the relationship is deemed a tenancy, the clause's immediate re-entry mechanism may face legal hurdles."}]

**01_maharashtra_leave_license_mumbai.pdf / c011** — risk: GREEN (confidence 0.95), topic: notice, retrieved: ['CENTRAL_EVICTION_003', 'MH_NOTICE_001'], grounded: True

> Clause: The Licensor or his authorised representative shall be entitled to inspect the said premises at reasonable times upon giving 24 hours' prior notice to the Licensee.

- **Document says:** The landlord (Licensor) or their representative has the right to enter and inspect the property at reasonable times, provided they give the tenant (Licensee) 24 hours' prior notice.
- **Concern:** This is standard and balanced language. It grants the landlord a reasonable right to inspect the property while protecting the tenant's privacy by requiring advance notice and limiting entry to reasonable times.
- **Statute support:** none

**01_maharashtra_leave_license_mumbai.pdf / c012** — risk: GREEN (confidence 0.95), topic: none, retrieved: none, grounded: True

> Clause: This Agreement shall be governed by the laws applicable in the State of Maharashtra, and the courts at Mumbai alone shall have jurisdiction over any disputes arising herefrom.

- **Document says:** The agreement is governed by the laws of the State of Maharashtra, and any disputes must be handled exclusively by the courts in Mumbai.
- **Concern:** This is standard and balanced language for a lease in that region, as it clearly defines the governing law and the specific location for legal proceedings.
- **Statute support:** none
