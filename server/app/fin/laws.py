"""The six laws (plan section 3), in code, the same at every size. Every finance tool calls `screen()` before it runs.

1 money never moves without her tap   2 tier C refused   3 no secrets   4 figures from data (calc + checker)   5 rules from checked packs
6 the decider is named.  Plus the advice wording guard (D8)."""
from __future__ import annotations

import re
from typing import Any

# The 13 tier C acts (register, "Never an AI employee"). key -> (what, why, what Hoola does instead)
TIER_C: dict[str, tuple[str, str, str]] = {
    "move_money": ("Moving money, paying, sending a remittance, releasing a settlement instruction",
                   "Money moves only on her own tap in her own app or bank; a firm's payments officer releases",
                   "Hoola prepares the payment and shows it; she taps it in Hoola Wallet or her bank app."),
    "place_order": ("Placing, changing or cancelling an order; confirming a trade; setting margin",
                    "Broker / dealer licence and market-abuse liability", "Hoola prepares an order ticket she places herself."),
    "approve_decision": ("Approving or declining a loan, claim, account, KYC, benefit or a customer risk rating",
                         "The regulated firm or public body is accountable",
                         "Hoola prepares the file with the rule hits; the named officer decides."),
    "freeze_account": ("Freezing, blocking or closing an account; placing holds; deciding a dispute or a scam refund",
                       "Due process and the firm's liability decision", "Hoola prepares the case for the decider."),
    "file_as_institution": ("Filing a SAR / STR, regulatory, tax or statistical return as the institution or as a client's agent",
                            "A named reporting officer or registered agent files", "Hoola drafts the return or report; the named person files."),
    "sign_opinion": ("Signing an audit opinion, valuation, actuarial or rating opinion, financial statements or a fairness opinion",
                     "A licensed professional signs and is liable", "Hoola prepares the working papers."),
    "licensed_advice": ("Personalised regulated advice on investments, pensions, mortgages, debt or insurance",
                        "Licensing in each country", "Hoola explains options, costs and maths, and names the free official help or her adviser."),
    "bind_settlement": ("Agreeing a settlement, write-off or binding payment plan; pressure collection calls",
                        "The lender's credit decision and conduct rules", "Hoola prepares the proposal for the person who decides."),
    "publish_rating": ("Publishing research, issuing a rating, a listing or an index decision",
                       "Research and rating-agency rules", "Hoola drafts the note for the analyst who publishes."),
    "act_as_fiduciary": ("Acting as attorney, trustee, executor or guardian; probate, will drafting and legal advice",
                         "A fiduciary or court appointment; reserved legal activities", "Hoola prepares the paperwork for the appointed person."),
    "shariah_ruling": ("Issuing a Shariah ruling or certifying a product", "Shariah Supervisory Board authority",
                       "Hoola explains the structures and prepares questions for the board."),
    "statutory_decision": ("Ombudsman / ADR adjudication, enforcement or licensing decisions, fund freezes", "Statutory decision-makers",
                           "Hoola prepares the case file."),
    "physical_custody": ("Handling cash, cheques and valuables; notarising or witnessing signatures", "Physical custody and presence",
                         "Hoola prepares the list of what to bring and where."),
}

# words in an action / tool name that mean one of the acts above
_ACT_WORDS = {
    "move_money": r"\b(pay|transfer|send_money|remit_now|send_remittance|release_payment|payout|disburse|reimburse|issue_refund|refund_now)\b",
    "place_order": r"\b(place_order|buy_order|sell_order|cancel_order|execute_trade)\b",
    "approve_decision": r"\b(approve_loan|decline_loan|approve_kyc|approve_claim|approve_account|approve_refund|decline_refund|decide_claim|decide_case|close_case)\b",
    "freeze_account": r"\b(freeze|freeze_account|block_account|close_account|decide_dispute)\b",
    "file_as_institution": r"\b(file_sar|file_str|file_return|submit_return)\b",
    "sign_opinion": r"\b(sign_opinion|sign_audit|sign_valuation)\b",
}

SECRET_KEYS = re.compile(r"^(pin|upi_pin|mpin|otp|cvv|cvc|password|passcode|card_number|card_no|pan_card_number_full)$", re.I)
_CARDISH = re.compile(r"card|acct|account|number", re.I)
_DIGITS = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_ADVICE = re.compile(
    r"\byou should (buy|sell|switch|invest|borrow|take out|move your|put your|transfer your|cash in|surrender)\b"
    r"|\b(i|we) recommend (you )?(buy|sell|invest|switch|borrow)\b"
    r"|\bthe best (fund|stock|share|policy|loan|mortgage|pension) for you is\b", re.I)


class Refused(PermissionError):
    def __init__(self, key: str, message: str):
        self.key = key
        super().__init__(message)


def _luhn(s: str) -> bool:
    d = [int(c) for c in s if c.isdigit()]
    if not 13 <= len(d) <= 19:
        return False
    tot = 0
    for i, x in enumerate(reversed(d)):
        if i % 2:
            x *= 2
            if x > 9:
                x -= 9
        tot += x
    return tot % 10 == 0


def tier_c(key: str) -> dict[str, str]:
    what, why, instead = TIER_C[key]
    return {"key": key, "what": what, "why": why, "instead": instead}


def refuse_act(key: str) -> None:
    t = tier_c(key)
    raise Refused(key, f"Hoola does not do this: {t['what'].lower()}. {t['why']}. {t['instead']}")


def act_of(action: str) -> str:
    a = str(action or "").lower()
    for key, rx in _ACT_WORDS.items():
        if re.search(rx, a):
            return key
    return ""


def secrets_in(args: dict[str, Any] | None) -> list[str]:
    """Keys whose value is a secret: a PIN / OTP / CVV / password field with a value, or a full card number (13-19 digits passing
    the Luhn check) in a field about a card or account. Statement text is not scanned: banks print long reference numbers."""
    hits: list[str] = []

    def walk(v: Any, path: str, cardish: bool = False) -> None:
        if isinstance(v, dict):
            for k, x in v.items():
                key = str(k)
                if SECRET_KEYS.match(key) and str(x or "").strip():
                    hits.append(f"{path}{key}")
                else:
                    walk(x, f"{path}{key}.", bool(_CARDISH.search(key)))
        elif isinstance(v, list):
            for i, x in enumerate(v[:2000]):
                walk(x, f"{path}{i}.", cardish)
        elif isinstance(v, (str, int)) and cardish:
            v = str(v)
            for m in _DIGITS.finditer(v):
                if _luhn(m.group(0)):
                    hits.append(path.rstrip(".") or "text")
                    return

    walk(args or {}, "")
    return hits


def screen(tool: str, action: str, args: dict[str, Any] | None) -> None:
    """Run before every finance tool. Refuses a tier C act and any secret. Raises Refused with the words to say."""
    key = act_of(action)
    if key:
        refuse_act(key)
    hits = secrets_in(args)
    if hits:
        raise Refused("secret", "Hoola never takes a PIN, OTP, CVV, password or full card number. Please remove it "
                                "(" + ", ".join(sorted(set(hits))[:4]) + ") - the last 4 digits are enough.")


def advice_flags(text: str) -> list[str]:
    """Words that read as a personal recommendation (D8). The caller rewrites or sends the ask to a licensed person / free help."""
    return [m.group(0) for m in _ADVICE.finditer(str(text or ""))]


NOT_ADVICE = "Hoola is not a licensed adviser. It explains, calculates and prepares; decisions are yours or your adviser's."


def decider(ws: dict[str, Any] | None, part: str = "") -> str:
    """Who decides / signs in this workspace (law 6). Personal and solo: her. Others: the first named approver / reviewer."""
    s = (ws or {}).get("settings") or {}
    if s.get("size") in (None, "personal", "solo"):
        return "you"
    for p in s.get("deciders") or []:
        if p.get("role") in ("approver", "owner"):
            return p["name"]
    for p in s.get("deciders") or []:
        return p["name"]
    return "the named approver (none set yet - add one in Settings)"
