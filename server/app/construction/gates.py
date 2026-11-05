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
    ("sign or stamp a drawing", "Drawing / design par sign-stamp reserved hai: licensed architect / registered "
     "engineer karenge. Hoola working paper taiyaar karta hai - signature ki jagah khaali rehti hai."),
    ("sign or stamp a structural design", "Structural design ka sign-stamp corporation ke register ke engineer ka kaam hai."),
    ("sign or stamp a stability certificate", "Stability certificate us nagar nigam ke register ke engineer deta hai; Hoola sirf computation dikhata hai."),
    ("sign or stamp a fire certificate", "Fire NOC Form A/B sirf Licensed Agency issue karti hai - ek shabd bhi nahi badalta."),
    ("sign or stamp an MEP certificate", "MEP certification ka sign specialist licensee karega."),
    ("sign or stamp a completion or occupancy certificate", "Completion / Occupancy certificate licensed architect / authority deti hai; Hoola sirf packet jodta hai."),
    ("file a permission application", "Application file karna owner / licensee ka kaam hai (aapki DSC, aapke naam). Hoola file taiyaar karta hai, jama nahi karta."),
    ("certify RERA percentage completion", "RERA completion % certify karna promoter / architect / engineer ki declaration hai."),
    ("certify escrow withdrawal", "Escrow 70% withdrawal certificate CA / architect / engineer dete hain; Hoola sirf reconciliation banata hai."),
    ("accept or reject work on site", "Kaam ka inspection pass / reject site engineer / QA engineer karte hain; Hoola record rakhta hai."),
    ("accept a concrete cube", "Cube acceptance QA engineer ka decision hai (IS 456 criteria Hoola sirf DRAFT mein computing karta hai)."),
    ("approve a design", "Design approve karna client / PMC ka kaam hai."),
    ("approve a change order", "Change order approve karna client / PMC ka kaam hai."),
    ("sign a contract", "Contract par sign aapki (ya aapke counsel ki) haan se hota hai."),
    ("release a payment", "Payment chhodna aapke tap se hota hai; Hoola sirf working paper aur card banata hai."),
    ("release a bank guarantee", "BG chhodna aapke tap se hota hai; Hoola sirf working paper aur card banata hai."),
    ("issue a notice", "Notice issue karna (termination / delay / LD) aapke aur aapke advocate ke through hota hai; Hoola draft ke saath rukta hai."),
    ("issue a termination", "Termination notice aapke adhikaar mein hai; Hoola sirf draft aur record rakhta hai."),
    ("issue an LD deduction", "LD kaati ya maafi - yeh legal entitlement ka decision hai; Hoola sirf arithmetic dikhata hai."),
    ("decide delay entitlement", "Delay entitlement ka nishkarsh code se nahi nikalta - woh commercial manager ke "
     "working paper par advocate/counsel ka conclusion hota hai; Hoola as-planned vs as-built ka working paper "
     "banata hai (notice-compliance ka hisaab saath)."),
    ("certify measurement", "Measurement certify karna billing engineer ka kaam hai; naap jaisa likha waisa rehta hai."),
    ("certify an RA bill", "RA bill ka certification / pass billing engineer / department karta hai; Hoola bill draft karta hai."),
    ("give a safety clearance", "Safety clearance safety officer deti hai; Hoola permit DRAFT + records rakhta hai."),
    ("give a permit-to-work", "Permit-to-work safety officer deti hai; Hoola permit DRAFT + records rakhta hai."),
    ("certify green rating", "IGBC / GRIHA / LEED rating assessor decide karta hai; Hoola credit tracker aur evidence binder rakhta hai."),
    ("certify commissioning", "Commissioning sign-off Cx authority ka hai."),
    ("certify an energy audit", "Energy audit certified auditor karta hai; Hoola data aur hisaab taiyaar karta hai."),
    ("give a structural-safety verdict", "Structural-safety ka verdict registered engineer deta hai; Hoola kabhi nahi."),
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
LAW = ("PREPARE, never CERTIFY: Hoola record, hisaab aur working paper banata hai; jo sign / certify / file / "
       "approve / accept / release reserved hai woh uske naam-waale insaan karta hai (tier C refusal ho to "
       "refusal ka text waise ka waisa bolo). Har number ke saath uska formula aur input; paisa sirf aapke tap se.")
