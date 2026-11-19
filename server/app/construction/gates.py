"""The tier gate of the Construction & Real Estate department (v0.512.0).

PREPARE, never CERTIFY. From the research (docs/research/building_industry/, R5): the application is the
owner's act, the technical certification is reserved to a named licensee on a specific register, and
preparation is unreserved - 70-80% of the labour, almost none of the liability. "An agent that drafts
those certificates and lets the licensee sign is useful and lawful; an agent that signs or files them is
forgery."

Every construction tool runs `tier_c_check()` over what it was asked to do before it does anything. A hit
returns the refusal text (the model says it verbatim, with the name of the human who must do the act).
This is the fence pattern: pure functions, no state, no I/O, imported anywhere."""
from __future__ import annotations

# (id, what is reserved, the refusal Hoola says). Kept in register order (the register's NEVER list).
TIER_C: tuple[tuple[str, str], ...] = (
    ("sign or stamp a drawing", "Signing or stamping a drawing / design is reserved: a licensed architect / registered "
     "engineer does it. Hoola prepares the working paper - the signature space stays empty."),
    ("sign or stamp a structural design", "The sign-stamp on a structural design is the work of an engineer on the corporation's register."),
    ("sign or stamp a stability certificate", "A stability certificate is given by an engineer on that municipal corporation's register; Hoola only shows the computation."),
    ("sign or stamp a fire certificate", "Fire NOC Form A/B is issued only by a Licensed Agency - not one word is changed."),
    ("sign or stamp an MEP certificate", "The MEP certification is signed by the specialist licensee."),
    ("sign or stamp a completion or occupancy certificate", "A Completion / Occupancy certificate is given by the licensed architect / authority; Hoola only assembles the packet."),
    ("file a permission application", "Filing the application is the owner's / licensee's act (your DSC, your name). Hoola prepares the file; it does not submit it."),
    ("certify RERA percentage completion", "Certifying the RERA completion % is the promoter's / architect's / engineer's declaration."),
    ("certify escrow withdrawal", "The escrow 70% withdrawal certificate is given by the CA / architect / engineer; Hoola only makes the reconciliation."),
    ("accept or reject work on site", "Passing / rejecting work at inspection is done by the site engineer / QA engineer; Hoola keeps the record."),
    ("accept a concrete cube", "Cube acceptance is the QA engineer's decision (Hoola only computes the IS 456 criteria as a DRAFT)."),
    ("approve a design", "Approving a design is the client's / PMC's job."),
    ("approve a change order", "Approving a change order is the client's / PMC's job."),
    ("sign a contract", "A contract is signed only with your (or your counsel's) approval."),
    ("release a payment", "A payment is released only by your tap; Hoola only makes the working paper and the card."),
    ("release a bank guarantee", "A BG is released only by your tap; Hoola only makes the working paper and the card."),
    ("issue a notice", "Issuing a notice (termination / delay / LD) happens through you and your advocate; Hoola stops at the draft."),
    ("issue a termination", "A termination notice is yours to issue; Hoola only keeps the draft and the record."),
    ("issue an LD deduction", "Deducting or waiving LD is a decision on legal entitlement; Hoola only shows the arithmetic."),
    ("decide delay entitlement", "A conclusion on delay entitlement does not come from code - it is the advocate's/counsel's conclusion on the "
     "commercial manager's working paper; Hoola makes the as-planned vs as-built working paper "
     "(with the notice-compliance arithmetic)."),
    ("certify measurement", "Certifying a measurement is the billing engineer's job; the measurement stays as it was written."),
    ("certify an area statement", "Certifying an area statement / carpet area is the job of the licensed surveyor / project architect / "
     "engineer; Hoola makes the calculation and the discrepancy report - the sign line stays empty."),
    ("certify a survey", "A survey certificate carries the licensed surveyor's signature; Hoola shows the closure, area and "
     "discrepancy arithmetic - it does not make the certificate."),
    ("certify an RA bill", "An RA bill is certified / passed by the billing engineer / department; Hoola drafts the bill."),
    ("give a safety clearance", "A safety clearance is given by the safety officer; Hoola keeps the permit DRAFT + records."),
    ("give a permit-to-work", "A permit-to-work is given by the safety officer; Hoola keeps the permit DRAFT + records."),
    ("certify green rating", "The IGBC / GRIHA / LEED rating is decided by the assessor; Hoola keeps the credit tracker and the evidence binder."),
    ("certify commissioning", "Commissioning sign-off is the Cx authority's."),
    ("certify an energy audit", "An energy audit is done by a certified auditor; Hoola prepares the data and the calculations."),
    ("give a structural-safety verdict", "A structural-safety verdict is given by a registered engineer; never by Hoola."),
    ("approve the as-built set", "The as-built set is approved by the site architect / QS before handover; "
     "Hoola shows the completeness register and the missing list - the sign line stays empty."),
    ("order formwork striking", "The order to strike (remove) formwork is given by the site engineer; Hoola only shows the "
     "calculation against IS 456 Table 10."),
    ("tag a scaffold safe", "A scaffold's green tag is put on by a competent person; Hoola keeps the inspection REGISTER, "
     "it does not tag."),
    # Wave 4 (v0.586.0): the remaining seats
    ("certify a clear title", "A conclusion on title is the title advocate's opinion; Hoola makes the document checklist "
     "and the land-record reconciliation - it gives no opinion."),
    ("declare the critical path", "Marking the critical path / an extension of time is the planner's / PMC's word; "
     "Hoola shows the variance in dates, criticality does not come from code."),
    ("declare a site safe or resume work", "Declaring a site safe / resuming work is the EHS head's decision; "
     "Hoola keeps the register, the checklist and the expiry calculations."),
    ("give tax or investment advice", "Tax / investment advice is the CA's or tax consultant's; Hoola only shows the "
     "computation - and the rate comes from the source you gave."),
    ("advertise a project without its RERA number", "Advertising a project without its RERA number is prohibited under RERA 2016 "
     "s.3; Hoola asks for the RERA number in the ad asset register."),
    ("certify a structural audit", "A structural audit certificate is given by a registered structural engineer; "
     "Hoola only keeps the schedule and the register."),
    ("file a GST return", "Filing a GST return is your CA's job; Hoola only shows the computation."),
)


def tier_c_check(ask: str) -> str | None:
    """Return the refusal text if the ask hits a reserved (tier C) act, else None. Match is deliberately
    broad - a false refusal costs one clarifying sentence, a missed one costs a forged certificate."""
    t = (ask or "").lower().strip()
    if not t:
        return None
    for what, refusal in TIER_C:
        words = what.lower().replace("sign or stamp a ", "sign ").replace("sign or stamp an ", "sign ").split()
        # every keyword of the reserved phrase must appear (order-free) - keeps 'sign the drawing' caught
        if all(w in t for w in words if len(w) > 2):
            return refusal
    return None


NEVER_TIER_C = [w for w, _ in TIER_C]

# The one-line law repeated in every construction system prompt block.
LAW = ("PREPARE, never CERTIFY: Hoola makes the record, the calculations and the working paper; whatever sign / certify / file / "
       "approve / accept / release is reserved is done by the named person it belongs to (on a tier C refusal, say "
       "the refusal text exactly as it is). Every number comes with its formula and inputs; money moves only by your tap.")
