"""Generate data/synthetic_indian_clauses.csv: hand-authored Indian-register lease clauses
to shore up the trained classifier's `approach="trained"` fallback path.

Why this exists: the reviewed 31-clause Indian eval set showed the trained classifier
missing 2 of 4 hand-authored RED clauses - specifically the two with no alarm-word
phrasing (deposit forfeiture, unilateral rent increase). This generates training material
covering that exact failure mode: clauses that read as ordinary terms on the surface but
are substantively one-sided, across 5 states' terminology and 8 common lease topics.

Labels are PROPOSALS for the project owner to review before anything is trained on them,
the same discipline used for data/indian_eval_set.csv. This script only writes
data/synthetic_indian_clauses.csv - it does not touch the training set, the US test set,
or the Indian eval set.

    python scripts/generate_synthetic_indian_clauses.py
"""

from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "synthetic_indian_clauses.csv"

# Actor terms and document style per state, matching how each state's instrument is
# actually styled (Maharashtra leave & license uses Licensor/Licensee, not Landlord/Tenant).
STATES = [
    {"state": "Maharashtra", "document_style": "Leave and License Agreement", "l1": "Licensor", "l2": "Licensee", "premises": "the Licensed Premises"},
    {"state": "Delhi", "document_style": "Rent Agreement", "l1": "Landlord", "l2": "Tenant", "premises": "the premises"},
    {"state": "Karnataka", "document_style": "Rental Agreement", "l1": "Owner", "l2": "Tenant", "premises": "the rented premises"},
    {"state": "Tamil Nadu", "document_style": "Lease Deed", "l1": "Lessor", "l2": "Lessee", "premises": "the demised premises"},
    {"state": "West Bengal", "document_style": "Deed of Lease", "l1": "Lessor", "l2": "Lessee", "premises": "the said property"},
]

# Each topic: green, yellow, red_obvious, red_subtle bodies with {l1}/{l2} placeholders,
# plus a short reasoning template for each. "Subtle" RED clauses are phrased as ordinary
# administrative or procedural terms and deliberately carry no alarm words ("without
# notice", "sole discretion", "any circumstances") - the real 2-of-4 miss pattern.
TOPICS: dict[str, dict] = {
    "security_deposit": {
        "green": (
            'The {l2} shall pay to the {l1} a sum of Rs. 60,000 as security deposit, which shall be interest-free and refundable in full to the {l2} within fifteen days of vacating {premises}, less any deductions for damage beyond normal wear and tear.',
            'Standard refundable deposit with a bounded, reasonable deduction basis.',
        ),
        "yellow": (
            'The security deposit of Rs. 60,000 paid by the {l2} shall be refunded by the {l1} only after adjustment of any outstanding electricity, water, and maintenance dues in respect of {premises}, and the refund may be delayed until such accounts are finally settled by the concerned authorities.',
            "Refund is conditional and open-ended in timing, though the basis (settling genuine dues) is legitimate - worth a tenant's attention, not alarming.",
        ),
        "red_obvious": (
            'The security deposit paid by the {l2} in respect of {premises} shall stand forfeited in its entirety under any circumstances whatsoever, and the {l2} shall have no claim whatsoever to its refund, whether or not the {l2} is in breach of this Agreement.',
            'Explicit, unconditional forfeiture regardless of fault - carries obvious alarm-word phrasing ("under any circumstances", "no claim whatsoever").',
        ),
        "red_subtle": (
            "The security deposit shall be adjusted towards the last three months' rent and shall not otherwise be refunded in cash to the {l2}, and any repainting, deep-cleaning, and fumigation charges as assessed solely by the {l1} in respect of {premises} shall be deducted from the deposit before such adjustment.",
            'Reads as routine deposit-handling, but forecloses any cash refund and lets the landlord unilaterally set deduction amounts with no cap or dispute route - one-sided despite the administrative tone.',
        ),
        "green_v2": (
            "The security deposit shall be equivalent to two months' rent, and the {l1} shall provide the {l2} with an itemised statement of any deductions within seven days of the {l2} vacating {premises}.",
            'Reasonable deposit amount with a transparency obligation on the landlord.',
        ),
        "yellow_v2": (
            'The security deposit shall be refunded within one month of the {l2} vacating {premises}; delays beyond this period, if any, shall not carry any interest or penalty payable by the {l1}.',
            "No penalty for the landlord's own delay in refunding - a real but moderate imbalance, not a severe one.",
        ),
        "red_subtle_v2": (
            "The security deposit shall be treated as fully earned by the {l1} upon signing of this Agreement and adjusted against the {l2}'s obligations in respect of {premises} hereunder, and no request for part-refund shall be entertained at any stage during the subsistence of this Agreement.",
            'Quietly converts a refundable deposit into a non-refundable sum mid-tenancy, phrased matter-of-factly with no dramatic language.',
        ),
    },
    "notice_period": {
        "green": (
            "Either party desiring to terminate this Agreement in respect of {premises} shall give the other party two months' prior written notice, and the Agreement shall stand terminated upon expiry of such notice period.",
            'Symmetric, reasonable notice obligation on both parties.',
        ),
        "yellow": (
            "The {l2} shall give three months' written notice to the {l1} before vacating {premises}, whereas the {l1} may terminate this Agreement by giving one month's notice to the {l2}.",
            'Asymmetric notice periods favouring the landlord - worth flagging, not severe.',
        ),
        "red_obvious": (
            'The {l1} may terminate this Agreement and call upon the {l2} to vacate {premises} at any time without assigning any reason and without giving any notice whatsoever to the {l2}.',
            'Explicit no-notice, no-reason termination right - obvious alarm-word phrasing.',
        ),
        "red_subtle": (
            'Notice of termination by the {l2} shall be deemed effective only from the first day of the following calendar month in which it is received, and any partial month remaining after the {l2} vacates shall not be adjusted or refunded, regardless of when within the month notice was actually served.',
            "Buries an unfair proration rule inside an ordinary notice-timing clause - no alarm words, but can cost the tenant nearly a full month's rent unfairly.",
        ),
        "green_v2": (
            'A notice period of one month shall apply equally to both the {l1} and the {l2} for termination of this Agreement in respect of {premises}, to be served in writing.',
            'Equal, short, and written - a fair baseline notice clause.',
        ),
        "yellow_v2": (
            "The {l2} shall be required to give two months' notice before vacating {premises}, while the {l1} is not obligated to intimate the {l2} of a decision not to renew the Agreement beyond its stated term.",
            'One-sided renewal-notice obligation, but the underlying term is still fixed and known in advance - a moderate imbalance.',
        ),
        "red_subtle_v2": (
            "Notice served by the {l1} under this clause shall be deemed duly served if affixed to the main door of {premises}, and the {l2}'s actual receipt of such notice shall not be a condition for its validity or for the running of the notice period.",
            'Allows constructive notice with no requirement the tenant actually saw it - a genuine one-sided drafting trap with no dramatic wording.',
        ),
    },
    "maintenance_responsibility": {
        "green": (
            "Minor day-to-day repairs at {premises}, such as replacement of fuses and minor plumbing fixtures, shall be attended to by the {l2} at the {l2}'s own cost, while structural repairs and major maintenance shall be the responsibility of the {l1}.",
            'Standard, fair split between minor tenant upkeep and major landlord repairs.',
        ),
        "yellow": (
            'The {l2} shall bear the cost of all maintenance and repairs to {premises} during the term of this Agreement, including those arising from ordinary use, save for repairs necessitated by structural defects existing prior to occupation.',
            'Shifts most maintenance cost to the tenant beyond the usual minor-repairs norm, though a landlord carve-out for pre-existing defects remains.',
        ),
        "red_obvious": (
            'The {l2} shall be solely and entirely responsible for all repairs and maintenance of {premises}, including structural repairs, roof and plumbing, regardless of cause, and the {l1} shall bear no maintenance liability whatsoever under any circumstances.',
            'Shifts all structural liability to the tenant regardless of cause - obvious alarm-word phrasing.',
        ),
        "red_subtle": (
            "All maintenance requests raised by the {l2} shall first be assessed by the {l1}'s appointed contractor, and the {l2} shall bear the full cost of any work so assessed, whether or not the {l2} disputes the necessity or the charges quoted by such contractor.",
            "Sounds like a routine maintenance-request process, but leaves the tenant no recourse against the landlord's own hand-picked contractor's charges.",
        ),
        "green_v2": (
            'The {l1} shall keep {premises} in a habitable condition and shall be responsible for the repair of the roof, external walls, and drainage system throughout the term of the Agreement.',
            'Clear landlord obligation for structural habitability items.',
        ),
        "yellow_v2": (
            "The {l2} shall promptly notify the {l1} of any repairs required at {premises}, and the {l1} shall carry out such repairs within a reasonable time; the {l2} may not deduct repair costs from the rent without the {l1}'s prior written consent.",
            'Reasonable process overall, but the tenant has no self-help remedy if the landlord is slow - a moderate, common imbalance.',
        ),
        "red_subtle_v2": (
            "Any repair or maintenance carried out by the {l2} at {premises}, whether or not intimated to the {l1} in advance, shall be deemed to be for the {l2}'s own benefit, and no reimbursement or adjustment against rent shall be claimed by the {l2} on this account at any time.",
            "Forecloses reimbursement entirely, even for the landlord's own structural obligations, phrased as a routine disclaimer with no dramatic language.",
        ),
    },
    "subletting": {
        "green": (
            'The {l2} shall not sublet, assign, or part with possession of {premises}, in whole or in part, without the prior written consent of the {l1}, such consent not to be unreasonably withheld.',
            'Standard consent-based restriction with a reasonableness safeguard.',
        ),
        "yellow": (
            "The {l2} shall not sublet {premises} without the {l1}'s written permission, and any request for such permission may be granted or refused by the {l1} at its discretion.",
            "No reasonableness safeguard on the landlord's discretion - worth flagging.",
        ),
        "red_obvious": (
            'The {l2} shall have no right whatsoever to sublet, assign, or share possession of {premises} under any circumstances, and any such act, even if inadvertent, shall entitle the {l1} to terminate this Agreement forthwith and forfeit the entire security deposit without notice.',
            'Absolute prohibition plus an automatic, disproportionate forfeiture penalty even for an inadvertent breach - obvious alarm-word phrasing.',
        ),
        "red_subtle": (
            'Any person other than the {l2} named herein found residing at {premises}, including a relative or paying guest of the {l2}, shall be deemed an unauthorised sub-letting for all purposes of this Agreement, entitling the {l1} to treat the Agreement as terminated.',
            'Defines subletting broadly enough to capture ordinary family living arrangements, a significant hidden risk framed as a plain definition.',
        ),
    },
    "termination": {
        "green": (
            'This Agreement may be terminated in respect of {premises} by mutual written consent of both parties at any time, or automatically upon expiry of its term unless renewed by mutual agreement.',
            'Balanced termination grounds requiring mutual consent or natural expiry.',
        ),
        "yellow": (
            "The {l1} may terminate this Agreement in respect of {premises} prior to expiry of its term only on grounds of non-payment of rent for two consecutive months or a material breach by the {l2}, subject to thirty days' written notice to remedy such breach.",
            'Landlord-only early-termination right, but limited to real breaches with a cure period - a reasonable, common structure.',
        ),
        "red_obvious": (
            "The {l1} reserves the absolute right to terminate this Agreement and re-enter {premises} at any time during its term, at the {l1}'s sole discretion and without assigning any cause, notwithstanding anything else contained herein.",
            'Unrestricted termination and re-entry at sole discretion - obvious alarm-word phrasing.',
        ),
        "red_subtle": (
            "In the event the {l1} requires {premises} for the {l1}'s own use, occupation by a family member, or for any renovation or redevelopment purpose, the {l1} may call upon the {l2} to vacate within seven days, and this Agreement shall stand terminated upon issuance of such intimation.",
            'Dressed as a common "owner\'s use" clause, but the seven-day window and broad triggers make it a functionally no-notice eviction right.',
        ),
        "green_v2": (
            'Save as otherwise provided herein, this Agreement shall continue for its full term in respect of {premises} and may not be terminated by either party except in accordance with the notice provisions set out above.',
            "Anchors termination to the Agreement's own notice terms rather than an open-ended right.",
        ),
        "yellow_v2": (
            "The {l1} may terminate this Agreement upon sale of {premises} to a third party, subject to giving the {l2} two months' notice to vacate and a pro-rata refund of any advance rent paid.",
            'A real risk of early termination on sale, but paired with notice and a fair refund - a moderate, disclosed imbalance.',
        ),
        "red_subtle_v2": (
            'Non-payment of any amount due under this Agreement, including charges for amenities provided at {premises} that are not part of the rent, shall be treated as a fundamental breach entitling the {l1} to terminate this Agreement with immediate effect and without recourse to the notice period specified elsewhere in this Agreement.',
            "Quietly carves out an exception that swallows the Agreement's own notice protection, triggered by even minor ancillary non-payment.",
        ),
    },
    "rent_escalation": {
        "green": (
            'The rent payable under this Agreement in respect of {premises} shall stand enhanced by 5% per annum, computed on the rent payable in the immediately preceding year, and shall be communicated to the {l2} at least one month prior to the date of such enhancement.',
            'Fixed, modest, and disclosed rent escalation - a standard clause.',
        ),
        "yellow": (
            'The rent for {premises} shall be subject to an annual increase of up to 10%, the exact percentage to be intimated by the {l1} to the {l2} in writing at the start of each year of the tenancy.',
            'A wider, landlord-set escalation band year to year - worth flagging, but capped and disclosed.',
        ),
        "red_obvious": (
            "The {l1} may increase the rent payable under this Agreement in respect of {premises} at any time and by any amount, at the {l1}'s sole and absolute discretion, and the {l2} shall be bound to pay such increased rent from the date so specified, without any right of objection.",
            'No cap, no notice, and no tenant recourse on the core financial term - obvious alarm-word phrasing ("sole and absolute discretion").',
        ),
        "red_subtle": (
            'The rent shall be revised annually in line with prevailing market rates for comparable premises in the locality as determined by the {l1}, and such revised rent shall be payable by the {l2} in respect of {premises} from the month following such determination.',
            '"Market rate as determined by the landlord" has no independent benchmark or cap - effectively unlimited discretion dressed as a market-linked clause.',
        ),
        "green_v2": (
            'The rent escalation clause shall not apply to {premises} during the first year of this Agreement, and thereafter the rent shall increase by a fixed 7% each year for the remaining term.',
            'Predictable, fixed escalation with a first-year grace period.',
        ),
        "yellow_v2": (
            'Any increase in property tax, cess, or other statutory levy on {premises} during the term of this Agreement may be passed on to the {l2} as an addition to the rent, subject to the {l1} furnishing documentary proof of such levy.',
            'Passes a real cost through to the tenant, but only with documentary proof - a moderate, verifiable imbalance.',
        ),
        "red_subtle_v2": (
            "In addition to the annual rent increase specified above, the {l2} shall also bear any increase in the {l1}'s home loan interest, society charges, or other holding costs associated with {premises}, as certified solely by the {l1}.",
            'Extends rent increases to open-ended, landlord-certified "holding costs" with no independent verification - functionally unlimited despite the administrative framing.',
        ),
    },
    "inspection_rights": {
        "green": (
            "The {l1} or the {l1}'s authorised representative may, upon giving twenty-four hours' prior notice to the {l2}, inspect {premises} at reasonable times during the term of this Agreement.",
            'Standard inspection right with advance notice and a reasonableness limit.',
        ),
        "yellow": (
            'The {l1} may inspect {premises} periodically to ascertain its condition, and the {l2} shall provide access for such inspection upon reasonable request by the {l1}.',
            'Vaguer than a fixed notice period, but still framed around reasonableness.',
        ),
        "red_obvious": (
            "The {l1} or the {l1}'s representatives may enter and inspect {premises} at any time of day or night, without any prior notice to the {l2}, and the {l2} shall have no right to refuse or restrict such entry under any circumstances.",
            'No-notice entry at any hour with no tenant right to refuse - obvious alarm-word phrasing.',
        ),
        "red_subtle": (
            "The {l1} shall retain a duplicate set of keys to {premises} for the purpose of periodic inspection and shall not be required to intimate the {l2} prior to each such inspection, provided such visits are, in the {l1}'s own assessment, reasonable in frequency.",
            'Landlord holding keys and self-certifying "reasonableness" quietly removes the tenant\'s notice and privacy protection while reading as a routine access arrangement.',
        ),
    },
    "registration_stamp_duty": {
        "green": (
            'The stamp duty and registration charges applicable to this Agreement in respect of {premises} shall be shared equally between the {l1} and the {l2}.',
            'An even, standard split of a joint statutory obligation.',
        ),
        "yellow": (
            'The stamp duty and registration charges for this Agreement in respect of {premises} shall be borne by the {l2}, and the {l1} shall cooperate in completing the registration formalities in a timely manner.',
            'A common, one-sided but disclosed cost allocation with a cooperation duty on the landlord.',
        ),
        "red_obvious": (
            'All stamp duty, registration charges, and any penalty, fine, or interest arising from delayed or improper registration of this Agreement in respect of {premises}, howsoever caused, shall be borne entirely by the {l2}, and the {l1} shall bear no liability whatsoever in this regard, including where the delay is attributable to the {l1}.',
            "Shifts liability for the landlord's own delay onto the tenant, and says so explicitly - obvious alarm-word phrasing.",
        ),
        "red_subtle": (
            "The {l2} shall be responsible for effecting registration of this Agreement within the statutorily prescribed period, and any consequence of non-registration, including the Agreement's inadmissibility as evidence, shall be solely to the {l2}'s account notwithstanding that the {l1}'s execution or cooperation may not have been available within that period.",
            "Registration legally requires both parties, yet this shifts the entire downside of non-registration onto the tenant even when the landlord didn't cooperate - a real drafting trap with no dramatic wording.",
        ),
    },
}

# Topics that get a second, balancing round (green_v2/yellow_v2/red_subtle_v2): the ones
# most prone to the "looks ordinary but isn't" failure mode this generation targets.
EXTRA_TOPICS = {
    "security_deposit", "notice_period", "maintenance_responsibility",
    "termination", "rent_escalation",
}


def _fill(template: str, state: dict) -> str:
    return template.format(l1=state["l1"], l2=state["l2"], premises=state["premises"])


def main() -> None:
    rows = []
    for topic, variants in TOPICS.items():
        # Rotate which states get the obvious vs. subtle RED wording so the split isn't
        # always tied to the same states (5 states -> rotate by a per-topic offset).
        order = list(STATES)
        offset = list(TOPICS).index(topic) % len(STATES)
        order = order[offset:] + order[:offset]
        obvious_states, subtle_states = order[:3], order[3:]

        for state in STATES:
            for key, label in (("green", "GREEN"), ("yellow", "YELLOW")):
                text, reason = variants[key]
                rows.append((topic, state, label, _fill(text, state), reason, "base"))
        for state in obvious_states:
            text, reason = variants["red_obvious"]
            rows.append((topic, state, "RED", _fill(text, state), reason, "base-obvious"))
        for state in subtle_states:
            text, reason = variants["red_subtle"]
            rows.append((topic, state, "RED", _fill(text, state), reason, "base-subtle"))

        if topic in EXTRA_TOPICS:
            for state in STATES:
                for key, label in (("green_v2", "GREEN"), ("yellow_v2", "YELLOW"), ("red_subtle_v2", "RED")):
                    text, reason = variants[key]
                    rows.append((topic, state, label, _fill(text, state), reason, "extra-subtle" if label == "RED" else "extra"))

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["clause_text", "proposed_label", "topic", "state", "document_style", "reasoning"])
        for topic, state, label, text, reason, _round in rows:
            writer.writerow([text, label, topic, state["state"], state["document_style"], reason])

    from collections import Counter
    counts = Counter(r[2] for r in rows)
    print(f"wrote {len(rows)} rows to {OUT}")
    print(f"label balance: {dict(counts)}")


if __name__ == "__main__":
    main()
