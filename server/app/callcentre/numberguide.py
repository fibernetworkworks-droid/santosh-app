"""v0.999.78 GET THE NUMBER (owner: "IN FRONT OF EVERY PROVIDER SHOW A FLOW PROPERLY WITHOUT MISTAKE --- A ICON NAME
GET THE NUMBER --- FOR EVERY PROVIDER").

One step-by-step guide per phone company: sign up -> checks -> money -> rent the number -> point it at Hoola -> copy the
keys -> paste them in Hoola -> test. Every step that needs a Hoola address names it by key (`copy`), and the desk shows the
REAL address for THAT company (its own webhook path), so nothing is typed by hand. The keys a step names are exactly the
keys Hoola asks for (`providers.KEYS`) - a test holds the two together. Menu names are the companies' own at the time of
writing and are said to be "about" where a company renames them often; the sites are their own top-level addresses.
"""
from __future__ import annotations

from typing import Any

# site = where she signs up; console = where she works after signing in
GUIDE: dict[str, dict[str, Any]] = {
    "plivo": {
        "site": "https://www.plivo.com/", "console": "https://console.plivo.com/",
        "number_word": "an Indian number",
        "steps": [
            ("Open an account", "Sign up on plivo.com with your business email."),
            ("Finish the business checks (KYC)", "Plivo asks for your company papers (GST / CIN / Udyam) and an ID. Calling to "
             "India opens only after they approve it, usually in 1-3 working days."),
            ("Add money", "Add credit in the console. Number rent and call minutes are taken from it."),
            ("Rent your number", "Console > Phone Numbers > Buy Number. Country India, type Voice. A landline (fixed line) "
             "number suits service calls; promotional calls to people who never asked need a 140 / 1600 series number with "
             "TRAI DLT registration through Plivo."),
            ("Make a voice application", "Console > Voice > Applications > New Application. Answer URL = the Answer address "
             "below (method POST). Hangup URL = the Hangup address below.", ["answer", "hangup"]),
            ("Connect the number", "Open the number you rented and choose that application under Application."),
            ("Copy your keys", "Console overview page: Auth ID and Auth Token.", [], ["auth_id", "auth_token"]),
        ]},
    "exotel": {
        "site": "https://exotel.com/", "console": "https://my.exotel.com/",
        "number_word": "an ExoPhone (Exotel's number)",
        "steps": [
            ("Open an account", "Sign up on exotel.com. Exotel's team calls you to open the account."),
            ("Finish the business checks (KYC)", "Exotel asks for your company papers and an ID before numbers go live."),
            ("Add money / choose a plan", "Pick a plan or add credit in your Exotel account."),
            ("Get your number", "Dashboard > ExoPhones. Exotel gives or sells you an ExoPhone for your city."),
            ("Ask Exotel to open the Voicebot", "The Voicebot (two-way call audio) is opened by Exotel on request: write to "
             "hello@exotel.com and ask for the Voicebot applet. Give them the Hoola server's address for IP whitelisting."),
            ("Build the call flow", "App Bazaar > Create a new flow: 1) Voicebot applet, URL = the Stream URL endpoint address "
             "below (dynamic URL). 2) After it, a Passthru applet, URL = the After address below. 3) On the Passthru's 200 "
             "path a Connect applet (dynamic URL = the Connect address below); on its 302 path a Hangup applet. Save it and "
             "note the flow id (the number in the flow's web address).", ["stream_url_endpoint", "after", "connect"]),
            ("Connect the number", "ExoPhones > your number > choose that flow."),
            ("Copy your keys", "Dashboard > API Settings: Account SID, API key, API token and the subdomain shown there "
             "(api.exotel.com or api.in.exotel.com). Add the flow id from the step above and the sample rate (8000 unless "
             "Exotel set 16000).", [], ["sid", "api_key", "api_token", "subdomain", "flow_id", "sample_rate"]),
        ]},
    "twilio": {
        "site": "https://www.twilio.com/", "console": "https://console.twilio.com/",
        "number_word": "a voice number in your country",
        "steps": [
            ("Open an account", "Sign up on twilio.com and verify your email and phone."),
            ("Upgrade the account", "Add a payment card and upgrade from the trial: a trial account can only call numbers "
             "you verified yourself."),
            ("Rent your number", "Console > Phone Numbers > Manage > Buy a number. Choose your country and tick Voice. "
             "Some countries ask for an address or ID first (Regulatory Compliance). In India use Plivo or Exotel instead: "
             "Twilio has no normal Indian calling numbers."),
            ("Point the number at Hoola", "Open the number > Voice Configuration: 'A call comes in' = Webhook, the Answer "
             "address below, HTTP POST. 'Call status changes' = the Hangup address below.", ["answer", "hangup"]),
            ("Copy your keys", "Console home > Account Info: Account SID and Auth Token.", [], ["account_sid", "auth_token"]),
        ]},
    "telnyx": {
        "site": "https://telnyx.com/", "console": "https://portal.telnyx.com/",
        "number_word": "a voice number in your country (140+ countries)",
        "steps": [
            ("Open an account", "Sign up on telnyx.com and verify your email."),
            ("Verify the account and add money", "Telnyx asks for account verification (business details) and a balance "
             "before numbers can be bought."),
            ("Rent your number", "Portal > Numbers > Search & Buy Numbers. Choose your country and Voice. Some countries ask "
             "for documents (Requirements)."),
            ("Make a TeXML application", "Portal > Voice > TeXML Applications > Add new. Voice URL = the Answer address below "
             "(POST). Status callback = the Hangup address below. Note the application id.", ["answer", "hangup"]),
            ("Connect the number", "Numbers > your number > Voice: choose that TeXML application."),
            ("Copy your keys", "Portal > Keys & Credentials: create an API key, and copy the Public key (for webhooks). The "
             "TeXML application id and the TeXML account SID are on the application's page.", [],
             ["api_key", "public_key", "application_id", "account_sid"]),
        ]},
    "vonage": {
        "site": "https://www.vonage.com/communications-apis/", "console": "https://dashboard.nexmo.com/",
        "number_word": "a voice number (many countries)",
        "steps": [
            ("Open an account", "Sign up for the Vonage API (Communications APIs) dashboard."),
            ("Add money", "Add credit in the dashboard (Billing)."),
            ("Rent your number", "Dashboard > Numbers > Buy numbers. Choose your country, feature Voice."),
            ("Make an application", "Dashboard > Applications > Create a new application. Turn on Voice: Answer URL = the "
             "Answer address below (HTTP POST), Event URL = the Hangup address below (HTTP POST). Click Generate public and "
             "private key - a private.key file downloads. Turn on signed webhooks.", ["answer", "hangup"]),
            ("Connect the number", "On the application's page, Link the number you rented."),
            ("Copy your keys", "The Application ID (application page), the whole private.key file (open it and copy all of "
             "it), and the Signature secret (API Settings).", [], ["application_id", "private_key", "signature_secret"]),
        ]},
    "signalwire": {
        "site": "https://signalwire.com/", "console": "https://signalwire.com/signin",
        "number_word": "a voice number (US, Canada, UK and more)",
        "steps": [
            ("Open an account", "Sign up on signalwire.com. You get a Space: your own address like yourname.signalwire.com."),
            ("Add money", "Add funds in your Space (Billing)."),
            ("Rent your number", "Your Space > Phone Numbers > Buy a New Phone Number."),
            ("Point the number at Hoola", "Phone Numbers > your number > Edit settings: handle calls using a LaML (cXML) "
             "webhook = the Answer address below (POST). Status callback = the Hangup address below.", ["answer", "hangup"]),
            ("Copy your keys", "Your Space > API: the Space address, Project ID, an API token (create one) and the Signing "
             "key.", [], ["space", "project_id", "api_token", "signing_key"]),
        ]},
    "bandwidth": {
        "site": "https://www.bandwidth.com/", "console": "https://dashboard.bandwidth.com/",
        "number_word": "a voice number (US, Canada, Europe)",
        "steps": [
            ("Open an account", "Bandwidth opens accounts through its sales team: ask for one on bandwidth.com."),
            ("Make an API user", "Dashboard > Account > Users: add a user with API access. Note its user name and password."),
            ("Make a Voice application", "Dashboard > Applications > Create: type Voice. Call initiated URL = the Answer "
             "address below (POST). Disconnect URL = the Hangup address below. Set a callback user name and password "
             "(any you choose).", ["answer", "hangup"]),
            ("Rent your number", "Dashboard > Numbers > Order numbers. Put it on a location whose sub-account uses that Voice "
             "application."),
            ("Copy your keys", "Account ID (top of the dashboard), the API user name / password, the application id, and "
             "the callback user name / password you chose.", [],
             ["account_id", "username", "password", "application_id", "callback_user", "callback_password"]),
        ]},
    "sinch": {
        "site": "https://sinch.com/", "console": "https://dashboard.sinch.com/",
        "number_word": "a voice number (60+ countries)",
        "steps": [
            ("Open an account", "Sign up on sinch.com and verify your email."),
            ("Add money", "Upgrade the account and add credit (Billing)."),
            ("Rent your number", "Dashboard > Numbers > Buy numbers: choose your country with Voice."),
            ("Make a Voice app", "Dashboard > Voice > Apps > Create app. Callback URL = the Answer address below (Sinch sends "
             "the call start, the answer and the end there).", ["answer"]),
            ("Connect the number", "Voice > Apps > your app > Voice numbers: assign the number you rented."),
            ("Copy your keys", "On the app's page: the Application key and the Application secret.", [],
             ["app_key", "app_secret"]),
        ]},
    "jambonz": {
        "site": "https://jambonz.org/", "console": "https://jambonz.cloud/",
        "number_word": "a number from any phone company in your country",
        "steps": [
            ("Choose a local phone company", "Pick any phone company (SIP trunk provider) that gives numbers where you are. "
             "Buy a number from them and ask for SIP trunk details."),
            ("Open a jambonz account", "Sign up on jambonz.cloud (or use your own jambonz server)."),
            ("Add the carrier", "jambonz > Carriers > Add carrier: enter the SIP details your phone company gave you."),
            ("Make an application", "jambonz > Applications > Add: Calling webhook = the Answer address below (POST). Call "
             "status webhook = the Hangup address below (POST). Copy the webhook secret it shows.", ["answer", "hangup"]),
            ("Add the number", "jambonz > Phone numbers > Add: the number from your phone company, its carrier, and the "
             "application above."),
            ("Copy your keys", "The API address (https://api.jambonz.cloud or your own), Account SID (Account page), an API "
             "key (create one), the webhook secret, and optionally the application SID.", [],
             ["base_url", "account_sid", "api_key", "webhook_secret", "application_sid"]),
        ]},
    "fake": {
        "site": "", "console": "", "number_word": "no number (a test line)",
        "steps": [("Nothing to buy", "The test line makes no real calls. Use it to try the script and the desk.")]},
}

FINAL = [
    ("Paste the keys in Hoola", "Here, in Settings: choose this company under Phone company, paste each key in its box "
     "under Keys and tap Save keys. Never paste keys in the chat."),
    ("Type your number", "Here, in Settings: the number you rented, with the country code (for example +91 20 4000 4410)."),
    ("Test it", "Make a call list with two or three of your own numbers and tap Start. Listen to the call, then tell "
     "Hoola what to change."),
]


def guide(provider: str, urls: dict[str, str], keys: list[tuple[str, str]]) -> dict[str, Any]:
    """The flow for one company: its sites + numbered steps, each with the Hoola addresses to copy and the key labels."""
    g = GUIDE.get(provider)
    if not g:
        return {}
    labels = dict(keys)
    steps = []
    for st in g["steps"]:
        title, text = st[0], st[1]
        copy = st[2] if len(st) > 2 else []
        need = st[3] if len(st) > 3 else []
        steps.append({"title": title, "text": text,
                      "copy": [{"key": k, "label": _NAMES.get(k, k), "value": urls.get(k, "")} for k in copy],
                      "keys": [labels.get(k, k) for k in need]})
    if provider != "fake":
        steps += [{"title": t, "text": x, "copy": [], "keys": []} for t, x in FINAL]
    return {"site": g["site"], "console": g["console"], "number_word": g["number_word"], "steps": steps,
            "note": "Menu names are the company's own and can change a little; look for the nearest one."}


_NAMES = {"answer": "Answer address", "hangup": "Hangup address", "stream": "Stream address",
          "stream_url_endpoint": "Stream URL endpoint", "after": "After address", "connect": "Connect address"}
