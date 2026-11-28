"""v0.999.68 ULTIMATE PC PLAN P0 - the PORTAL exam: 15 READ-ONLY jobs on real government / business portals of several
countries (the plan is for every country). Nothing is logged into, submitted or paid: each ask ends with 'stop there'.
v0: the page / answer patterns are written from public knowledge of these sites and are NOT confirmed yet - the first
run on her PC shows which ones need fixing (a failed check can be the pattern, not the agent: read the step record)."""
from __future__ import annotations

SET_V = 1   # v0.999.104 after the first run (9/15): searching allowed, cookie banners answered, firmer checks
GROUPS = ("us", "uk_eu", "asia_me", "india", "global")

# v0.999.104 the first run showed 'do not fill anything' forbade the very search the task asked for (ABN Lookup stopped at
# the empty box): typing into a SEARCH box is reading; nothing else is filled, signed in to or submitted
_STOP = (" Only look: searching the site is fine, but do not sign in, do not fill any other form, do not submit or pay "
         "anything; stop there and tell me what you found.")


def _t(id, group, ask, check, minutes=6):
    return {"id": id, "group": group, "ask": ask + _STOP, "check": check, "max_minutes": minutes, "cookies": True}


def _page(rx):
    return {"kind": "page", "re": rx}


def _ans(rx):
    return {"kind": "answer", "re": rx}


TASKS: list[dict] = [
    _t("us_irs_refund", "us", "Open irs.gov and go to the 'Where's My Refund' page.", _page(r"where'?s my refund|refund status|check your refund")),
    _t("us_ssa_office", "us", "Open ssa.gov and find the Social Security office locator.", _page(r"office locator|find (a|an|your) (local )?office|field office|zip code")),
    _t("us_sam_search", "us", "Open sam.gov and search contract opportunities for 'cybersecurity'.", _page(r"cybersecurity|opportunit")),
    _t("uk_companies_tesco", "uk_eu", "Search Companies House (find-and-update.company-information.service.gov.uk) for TESCO PLC "
       "and tell me its company number.", _ans(r"00445790")),
    _t("uk_vat_rate", "uk_eu", "On GOV.UK find the VAT rates page and tell me the UK standard VAT rate.", _ans(r"20\s*%|20 per ?cent")),
    _t("eu_vies", "uk_eu", "Open the EU VIES VAT number validation page (ec.europa.eu).", _page(r"VIES|VAT number")),
    _t("eu_ted_search", "uk_eu", "Open ted.europa.eu and search tenders for 'software'.", _page(r"software")),
    _t("ae_gov_portal", "asia_me", "Open u.ae (the UAE government portal) and find information about working hours in the private sector.",
       _page(r"working hours")),
    _t("sg_bizfile", "asia_me", "Open bizfile.gov.sg (ACRA) and go to its business entity search.", _page(r"search|entit")),
    _t("au_abn_lookup", "asia_me", "Open abr.business.gov.au (ABN Lookup) and search for Woolworths.", _page(r"woolworths")),
    _t("in_gst_search", "india", "Open gst.gov.in and go to 'Search Taxpayer' by GSTIN.", _page(r"search taxpayer|GSTIN")),
    _t("in_incometax_calendar", "india", "Open incometax.gov.in and find the tax calendar or due dates.", _page(r"calendar|due date")),
    _t("in_epfo_uan", "india", "Open epfindia.gov.in and find the 'Know your UAN' service.", _page(r"UAN")),
    _t("ca_gst_hst", "global", "Open canada.ca and find the GST/HST rates page.", _page(r"GST/HST|HST")),
    _t("wb_gdp", "global", "Open data.worldbank.org and find the GDP (current US$) indicator page.", _page(r"GDP \(current US\$\)")),
]
