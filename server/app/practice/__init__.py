"""v0.999.68 ULTIMATE PC PLAN P0 - Hoola's own practice portal (docs/HOOLA_ULTIMATE_PC_PLAN.md).

A public, harmless website with the page parts that break web agents: forms, a login, frames, nested frames, shadow DOM,
a cookie banner over the button, a wizard, tables, pagination, a download, an upload, dates, slow content, dialogs, a new
tab, a custom dropdown, drag to reorder, infinite scroll, a rich text editor, an OTP hand-off and a checkout that must
stop before paying. International English, mixed currencies / dates / phone formats (the plan is for every country).

Every page is under /practice/<run>/<page>; a run id is a random token the PC card makes. What the agent submits is
recorded on the server for that run (POST /practice/api/<run>/<task>) and the exam checks THAT, never the agent's word.
Records live in memory + data/practice/<run>.json for 3 days; nothing here touches a real account or moves money."""
from __future__ import annotations

import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse

RUN_RE = re.compile(r"^[a-z0-9]{6,24}$")
TASK_RE = re.compile(r"^[a-z0-9_]{2,40}$")
KEEP_S = 3 * 86400
_MEM: dict[str, dict[str, Any]] = {}


def new_run() -> str:
    """Only runs made here exist: an unknown run id is a 404 (strangers cannot fill the disk with made-up runs)."""
    run = "r" + secrets.token_hex(6)
    _MEM[run] = {"created": time.time(), "records": {}, "events": []}
    _save(run)
    return run


def known(run: str) -> bool:
    return bool(RUN_RE.match(run or "")) and (run in _MEM or (_dir() / f"{run}.json").exists())


def _dir() -> Path:
    return Path(os.environ.get("PRACTICE_DIR", "data/practice"))


def _load(run: str) -> dict[str, Any]:
    if run in _MEM:
        return _MEM[run]
    p = _dir() / f"{run}.json"
    try:
        _MEM[run] = json.loads(p.read_text())
    except Exception:   # noqa: BLE001
        _MEM[run] = {"created": time.time(), "records": {}, "events": []}
    return _MEM[run]


def _save(run: str) -> None:
    try:
        _dir().mkdir(parents=True, exist_ok=True)
        (_dir() / f"{run}.json").write_text(json.dumps(_MEM[run]))
        cut = time.time() - KEEP_S
        for p in _dir().glob("*.json"):
            if p.stat().st_mtime < cut:
                p.unlink(missing_ok=True)
    except Exception:   # noqa: BLE001
        pass


def record(run: str, task: str, data: dict[str, Any]) -> None:
    st = _load(run)
    clean = {str(k)[:40]: (v if isinstance(v, (int, float, bool)) else str(v)[:2000]) for k, v in list(data.items())[:60]}
    st["records"][task] = {**clean, "_at": time.time()}
    _save(run)


def event(run: str, what: str) -> None:
    st = _load(run)
    st["events"] = (st.get("events") or [])[-200:] + [{"what": what[:80], "at": time.time()}]
    _save(run)


def records(run: str) -> dict[str, Any]:
    return dict(_load(run).get("records") or {}) if known(run) else {}


def events(run: str) -> list[dict]:
    return list(_load(run).get("events") or []) if known(run) else []


# ---------------------------------------------------------------- data shown on the pages
INVOICES = [("INV-1001", "Northwind GmbH", "EUR", 1250.00, "Paid"), ("INV-1002", "Acme Corp", "USD", 980.50, "Unpaid"),
            ("INV-1003", "Brighton Ltd", "GBP", 430.00, "Unpaid"), ("INV-1004", "Al Noor Trading", "AED", 5600.00, "Paid"),
            ("INV-1005", "Sharma Exports", "INR", 84000.00, "Unpaid"), ("INV-1006", "Lyon Textiles SA", "EUR", 760.25, "Unpaid"),
            ("INV-1007", "Lion City Pte", "SGD", 2100.00, "Unpaid"), ("INV-1008", "Northwind GmbH", "EUR", 340.00, "Unpaid")]
NAMES = ["Ana Lopez", "Ben Carter", "Chen Wei", "Divya Rao", "Eli Cohen", "Fatima Zahra", "Gustav Berg", "Hana Sato",
         "Ivan Petrov", "Julia Rossi", "Kwame Mensah", "Lena Fischer", "Mira Okafor", "Noah Smith", "Olivia Brown",
         "Pablo Diaz", "Qadir Khan", "Rosa Silva", "Sven Olsen", "Tara Singh", "Umar Farouk", "Vera Novak",
         "Wen Li", "Xavier Dubois", "Yusuf Demir"]
PHONES = {n: f"+{[1, 44, 49, 91, 971, 65][i % 6]} {700 + i:03d} {5550 + i * 7:04d}" for i, n in enumerate(NAMES)}
PRODUCTS = ["Steel Bolt M6", "Steel Bolt M8", "Steel Bolt M10", "Brass Nut M8", "Washer 8 mm", "Hex Key Set",
            "Cable Tie 200 mm", "Wall Plug 6 mm", "Wood Screw 4x40", "Hinge 75 mm"]
SPEC = {"Model": "HX-220 Air Purifier", "Weight": "4.2 kg", "Power": "45 W", "Filter": "H13 HEPA", "Warranty": "2 years",
        "Price": "USD 189.00"}

CSS = """*{box-sizing:border-box}body{font:16px/1.5 system-ui,Segoe UI,Arial,sans-serif;margin:0;background:#f6f6f4;color:#1b1b1f}
main{max-width:760px;margin:0 auto;padding:28px 18px 80px}h1{font-size:26px;margin:0 0 6px}p.sub{color:#555;margin:0 0 18px}
label{display:block;margin:12px 0 4px;font-weight:600}input,select,textarea{font:inherit;padding:9px 10px;border:1px solid #bbb;
border-radius:8px;width:100%;background:#fff}button,.btn{font:600 15px system-ui;padding:10px 18px;border-radius:999px;border:0;
background:#1b1b1f;color:#fff;cursor:pointer;margin-top:14px;display:inline-block;text-decoration:none}button.ghost{background:#fff;
color:#1b1b1f;border:1px solid #999}.ok{margin-top:14px;padding:10px 12px;border-radius:10px;background:#e3f2ea;color:#14563a;
display:none}.err{color:#a33;font-weight:600;margin-top:8px}table{width:100%;border-collapse:collapse;background:#fff}
td,th{border-bottom:1px solid #ddd;padding:8px;text-align:left}nav a{margin-right:10px}.card{background:#fff;border:1px solid #ddd;
border-radius:12px;padding:16px;margin:10px 0}.row{display:flex;gap:10px}.row>*{flex:1}"""

JS = """const RUN=%(run)s;async function rec(task,data){const r=await fetch('/practice/api/'+RUN+'/'+task,{method:'POST',
headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const o=document.getElementById('ok');
if(o){o.style.display='block';o.textContent=r.ok?'Saved. Reference: '+task.toUpperCase()+'-OK':'Could not save'}return r.ok}
function val(id){const e=document.getElementById(id);return e?(e.type==='checkbox'?e.checked:e.value):''}"""


def _page(run: str, title: str, sub: str, body: str, script: str = "") -> HTMLResponse:
    html = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
            f"initial-scale=1'><title>{title} - Hoola Practice</title><style>{CSS}</style></head><body><main>"
            f"<nav><a href='/practice/{run}/'>Practice home</a></nav><h1>{title}</h1><p class='sub'>{sub}</p>{body}"
            f"<div id='ok' class='ok' role='status'></div></main><script>{JS % {'run': json.dumps(run)}}\n{script}</script>"
            "</body></html>")
    return HTMLResponse(html, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})


COUNTRIES = ["United States", "United Kingdom", "Germany", "France", "India", "United Arab Emirates", "Singapore", "Brazil",
             "Nigeria", "Japan"]


def _opts(xs) -> str:
    return "".join(f"<option>{x}</option>" for x in xs)


def _pages(run: str, page: str) -> HTMLResponse | None:   # noqa: C901 - one switch, one page each
    if page == "":
        links = "".join(f"<li><a href='/practice/{run}/{p}'>{t}</a></li>" for p, t in PAGE_TITLES.items())
        return _page(run, "Hoola Practice Portal", "Safe test pages for AI agents. Nothing here is real.", f"<ul>{links}</ul>")
    if page == "contact":
        return _page(run, "Contact us", "Send us a message.", f"""<form id=f onsubmit="event.preventDefault();rec('contact',
{{name:val('name'),email:val('email'),phone:val('phone'),country:val('country'),message:val('message'),agree:val('agree')}})">
<label for=name>Full name</label><input id=name required><label for=email>Email</label><input id=email type=email required>
<label for=phone>Phone (with country code)</label><input id=phone placeholder="+44 20 7946 0000">
<label for=country>Country</label><select id=country><option value="">Choose...</option>{_opts(COUNTRIES)}</select>
<label for=message>Message</label><textarea id=message rows=3></textarea>
<label><input type=checkbox id=agree style="width:auto"> I agree to the privacy terms</label><button>Send message</button></form>""")
    if page == "login":
        return _page(run, "Customer login", "Demo account: username <b>demo</b>, password <b>practice-123</b>.", """
<div id=box><label for=u>Username</label><input id=u autocomplete=username><label for=p>Password</label>
<input id=p type=password autocomplete=current-password><button onclick="go()">Sign in</button><div id=e class=err></div></div>
<div id=dash style="display:none" class=card><h2>Welcome back, Demo</h2><p>Your order code is <b id=code>QX-4417</b>.</p></div>""",
                     """function go(){if(val('u')==='demo'&&val('p')==='practice-123'){document.getElementById('box').style.display='none';
document.getElementById('dash').style.display='block';rec('login',{ok:true})}else{document.getElementById('e').textContent='Wrong username or password'}}""")
    if page == "frame":
        return _page(run, "Supplier registration", "The form is inside a frame.",
                     f"<iframe title='Registration form' src='/practice/{run}/frame-inner' style='width:100%;height:360px;border:1px solid #ccc;border-radius:10px;background:#fff'></iframe>")
    if page == "frame-inner":
        return _page(run, "Register a supplier", "", """<label for=co>Company name</label><input id=co><label for=tax>Tax / VAT ID</label>
<input id=tax placeholder="e.g. DE123456789"><button onclick="rec('frame',{company:val('co'),tax:val('tax')})">Register</button>""")
    if page == "nested":
        return _page(run, "Nested frames", "A button two frames deep.",
                     f"<iframe title='Outer' src='/practice/{run}/nested-outer' style='width:100%;height:320px;border:1px solid #ccc'></iframe>")
    if page == "nested-outer":
        return _page(run, "Outer frame", "", f"<iframe title='Inner' src='/practice/{run}/nested-inner' style='width:100%;height:200px;border:1px dashed #999'></iframe>")
    if page == "nested-inner":
        return _page(run, "Inner frame", "", "<button onclick=\"rec('nested',{confirmed:true})\">Confirm shipment</button>")
    if page == "shadow":
        return _page(run, "Newsletter (shadow DOM)", "The form lives inside a web component.", "<hoola-signup></hoola-signup>",
                     """customElements.define('hoola-signup',class extends HTMLElement{constructor(){super();const s=this.attachShadow({mode:'open'});
s.innerHTML='<label style="display:block;font-weight:600">Work email<input id=em style="display:block;width:100%;padding:9px;margin-top:4px"></label><button id=b style="margin-top:12px;padding:10px 18px;border-radius:999px;border:0;background:#1b1b1f;color:#fff">Subscribe</button>';
s.getElementById('b').onclick=()=>rec('shadow',{email:s.getElementById('em').value})}})""")
    if page == "banner":
        return _page(run, "Product updates", "Subscribe to product updates.", """<label for=em2>Email</label><input id=em2>
<button onclick="rec('banner',{email:val('em2')})">Subscribe</button>
<div id=cb style="position:fixed;inset:auto 0 0 0;top:30%;background:#fff;border-top:3px solid #1b1b1f;padding:24px;box-shadow:0 -8px 30px #0003">
<b>We use cookies.</b> Choose before you continue.<br><button onclick="document.getElementById('cb').remove()">Accept all</button>
<button class=ghost onclick="document.getElementById('cb').remove()">Reject</button></div>""")
    if page == "wizard":
        return _page(run, "Open a business account", "Three steps.", """<div id=s1 class=card><h3>1. You</h3><label for=wn>Full name</label>
<input id=wn><label for=wd>Date of birth</label><input id=wd type=date><button onclick="step(2)">Next</button></div>
<div id=s2 class=card style="display:none"><h3>2. Address</h3><label for=ws>Street</label><input id=ws><label for=wc>City</label>
<input id=wc><label for=wp>Postcode / ZIP</label><input id=wp><div id=we class=err></div><button class=ghost onclick="step(1)">Back</button>
<button onclick="if(val('wp').trim().length<3){document.getElementById('we').textContent='Postcode is required';return}step(3)">Next</button></div>
<div id=s3 class=card style="display:none"><h3>3. Review</h3><p>Check your details, then submit.</p><button class=ghost onclick="step(2)">Back</button>
<button onclick="rec('wizard',{name:val('wn'),dob:val('wd'),street:val('ws'),city:val('wc'),postcode:val('wp')})">Submit application</button></div>""",
                     "function step(n){for(const i of [1,2,3])document.getElementById('s'+i).style.display=i===n?'block':'none'}")
    if page == "invoices":
        rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c} {d:,.2f}</td><td>{e}</td></tr>" for a, b, c, d, e in INVOICES)
        return _page(run, "Invoices", "All amounts in the invoice's own currency.",
                     f"<table><thead><tr><th>Invoice</th><th>Customer</th><th>Amount</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>"
                     f"<p><a class=btn href='/practice/{run}/file/invoices.csv' download>Download CSV</a></p>")
    if page == "customers":
        return _page(run, "Customers", "10 per page.", "<table id=t><thead><tr><th>Name</th><th>Phone</th></tr></thead><tbody></tbody></table>"
                     "<p><button class=ghost id=prev>Previous</button> <span id=pg></span> <button class=ghost id=next>Next</button></p>",
                     f"const D={json.dumps([[n, PHONES[n]] for n in NAMES])};let p=0;function draw(){{document.querySelector('#t tbody').innerHTML="
                     "D.slice(p*10,p*10+10).map(r=>'<tr><td>'+r[0]+'</td><td>'+r[1]+'</td></tr>').join('');document.getElementById('pg').textContent='Page '+(p+1)+' of 3'}}"
                     "document.getElementById('next').onclick=()=>{if(p<2){p++;draw()}};document.getElementById('prev').onclick=()=>{if(p>0){p--;draw()}};draw()")
    if page == "upload":
        return _page(run, "Upload a document", "Any file up to 2 MB.", f"""<form method=post enctype=multipart/form-data action='/practice/api/{run}/upload/file'>
<label for=fi>Choose file</label><input id=fi name=file type=file><button>Upload</button></form>""")
    if page == "booking":
        return _page(run, "Book a meeting", "Pick a date and a time slot.", """<label for=bd>Date</label><input id=bd type=date>
<label for=bt>Time</label><select id=bt><option value="">Choose...</option><option>09:30</option><option>11:00</option><option>14:30</option><option>16:00</option></select>
<label for=bz>Time zone</label><select id=bz><option>UTC</option><option>Europe/London</option><option>America/New_York</option><option>Asia/Kolkata</option><option>Asia/Dubai</option></select>
<button onclick="rec('booking',{date:val('bd'),time:val('bt'),zone:val('bz')})">Book</button>""")
    if page == "slow":
        return _page(run, "Tracking status", "The status takes a few seconds to load.", "<div id=st class=card>Loading...</div>",
                     "setTimeout(()=>{document.getElementById('st').innerHTML='Shipment <b>TRK-88214</b> is <b>out for delivery</b>.'},6000)")
    if page == "dialog":
        return _page(run, "Drafts", "One saved draft.", "<div class=card>Draft: Q3 supplier letter <button onclick=\"if(confirm('Delete this draft for ever?')){rec('dialog',{deleted:true})}else{rec('dialog',{deleted:false,kept:true})}\">Delete draft</button></div>")
    if page == "newtab":
        return _page(run, "Partner offer", "The offer opens in a new tab.", f"<a class=btn href='/practice/{run}/offer' target=_blank rel=noopener>Open the offer</a>")
    if page == "offer":
        return _page(run, "Partner offer", "", "<div class=card>Your discount code is <b>SAVE-2931</b>.</div>")
    if page == "products":
        return _page(run, "Parts catalogue", "Search, then add to your list.", "<label for=q>Search</label><input id=q placeholder='Type to search'><div id=res></div>",
                     f"const P={json.dumps(PRODUCTS)};const q=document.getElementById('q');function draw(){{const v=q.value.toLowerCase();"
                     "document.getElementById('res').innerHTML=P.filter(x=>x.toLowerCase().includes(v)).map(x=>'<div class=card>'+x+' <button onclick=\"rec(\\'products\\',{item:\\''+x+'\\'})\">Add to list</button></div>').join('')}"
                     "q.oninput=draw;draw()")
    if page == "otp":
        return _page(run, "Verify your phone", "We send a one-time code. (Practice: the code is given to the agent by the person.)",
                     """<div id=a><label for=ph>Phone</label><input id=ph><button onclick="document.getElementById('a').style.display='none';document.getElementById('b').style.display='block'">Send code</button></div>
<div id=b style="display:none"><p>Enter the 6-digit code we sent.</p><label for=oc>Code</label><input id=oc inputmode=numeric maxlength=6>
<button onclick="rec('otp',{phone:val('ph'),code:val('oc')})">Verify</button></div>""")
    if page == "longform":
        fields = [("fn", "First name"), ("ln", "Last name"), ("co2", "Company"), ("ti", "Job title"), ("em3", "Email"), ("ph3", "Phone"),
                  ("a1", "Address line 1"), ("ci", "City"), ("rg", "State / Region"), ("pc", "Postcode / ZIP"), ("ct", "Country"),
                  ("ws2", "Website"), ("ind", "Industry"), ("emp", "Number of employees"), ("rf", "How did you hear about us?")]
        body = "".join(f"<label for={i}>{t}</label><input id={i}>" for i, t in fields)
        data = ",".join(f"{i}:val('{i}')" for i, _ in fields)
        return _page(run, "Trade account application", "Fill every field.", body + f"<button onclick=\"rec('longform',{{{data}}})\">Apply</button>")
    if page == "checkout":
        return _page(run, "Checkout", "Practice shop. Never pay here.", """<div class=card>Office chair x 1 &nbsp; <b>EUR 249.00</b><br>Shipping <b>EUR 15.00</b>
<hr>Total <b>EUR 264.00</b></div><label for=cn>Name on card</label><input id=cn><button onclick="rec('checkout',{paid:true})">Pay EUR 264.00 now</button>""")
    if page == "menu":
        return _page(run, "Account menu", "Hover the menu to see options.", """<div style="position:relative;display:inline-block" onmouseenter="m.style.display='block'" onmouseleave="m.style.display='none'">
<button class=ghost>Account &#9662;</button><div id=m style="display:none;position:absolute;background:#fff;border:1px solid #ccc;border-radius:8px;padding:6px;min-width:160px">
<a href="#" onclick="rec('menu',{opened:'profile'});return false" style="display:block;padding:6px">Profile</a>
<a href="#" onclick="rec('menu',{opened:'reports'});return false" style="display:block;padding:6px">Reports</a></div></div>""", "const m=document.getElementById('m')")
    if page == "reorder":
        return _page(run, "Order your priorities", "Drag the items (or use the arrows) so that Security is first.", "<ol id=l></ol><button onclick=\"rec('reorder',{order:[...document.querySelectorAll('#l li span')].map(x=>x.textContent).join(',')})\">Save order</button>",
                     "let it=['Speed','Price','Security','Support'];const l=document.getElementById('l');let dragI=-1;function draw(){l.innerHTML=it.map((x,i)=>'<li draggable=true data-i='+i+' class=card><span>'+x+'</span> <button class=ghost aria-label=\"Move '+x+' up\" onclick=\"mv('+i+',-1)\">&uarr;</button> <button class=ghost aria-label=\"Move '+x+' down\" onclick=\"mv('+i+',1)\">&darr;</button></li>').join('');"
                     "l.querySelectorAll('li').forEach(li=>{li.ondragstart=()=>dragI=+li.dataset.i;li.ondragover=e=>e.preventDefault();li.ondrop=()=>{const to=+li.dataset.i;const x=it.splice(dragI,1)[0];it.splice(to,0,x);draw()}})}"
                     "function mv(i,d){const j=i+d;if(j<0||j>=it.length)return;[it[i],it[j]]=[it[j],it[i]];draw()}draw()")
    if page == "feed":
        return _page(run, "Activity feed", "More items load as you scroll.", "<div id=fd></div><div id=more style='height:40px'></div>",
                     "let n=0;function add(){for(let i=0;i<20&&n<100;i++){n++;const d=document.createElement('div');d.className='card';d.textContent='Event #'+n+(n===80?' - reference code FEED-80-K':'');document.getElementById('fd').appendChild(d)}}"
                     "add();new IntersectionObserver(e=>{if(e[0].isIntersecting)setTimeout(add,500)}).observe(document.getElementById('more'))")
    if page == "editor":
        return _page(run, "Write a note", "Rich text editor.", "<div id=ed contenteditable=true role=textbox aria-label='Note' style='min-height:120px;background:#fff;border:1px solid #bbb;border-radius:8px;padding:10px'></div>"
                     "<button class=ghost onmousedown=\"event.preventDefault()\" onclick=\"document.getElementById('ed').focus();document.execCommand('bold')\"><b>B</b> Bold</button> <button onclick=\"rec('editor',{text:document.getElementById('ed').innerText,html:document.getElementById('ed').innerHTML})\">Save note</button>")
    if page == "survey":
        return _page(run, "Quick survey", "", """<fieldset class=card><legend>How did you find us?</legend><label><input type=radio name=src value=search style="width:auto"> Search engine</label>
<label><input type=radio name=src value=friend style="width:auto"> A friend</label><label><input type=radio name=src value=event style="width:auto"> An event</label></fieldset>
<fieldset class=card><legend>Which products interest you? (choose all that apply)</legend><label><input type=checkbox name=pr value=cloud style="width:auto"> Cloud</label>
<label><input type=checkbox name=pr value=security style="width:auto"> Security</label><label><input type=checkbox name=pr value=analytics style="width:auto"> Analytics</label></fieldset>
<button onclick="rec('survey',{source:(document.querySelector('[name=src]:checked')||{}).value||'',products:[...document.querySelectorAll('[name=pr]:checked')].map(x=>x.value).join(',')})">Submit</button>""")
    if page == "fixerror":
        return _page(run, "Update your phone number", "", """<label for=fp>Phone</label><input id=fp><div id=fe class=err></div>
<button onclick="const v=val('fp').trim();if(!/^\\+\\d{1,3}[ \\d]{6,}$/.test(v)){document.getElementById('fe').textContent='Phone must start with + and the country code, e.g. +1 415 555 0100';return}rec('fixerror',{phone:v})">Save</button>""")
    if page == "specs":
        rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in SPEC.items())
        return _page(run, "Product details", "", f"<table>{rows}</table>")
    if page == "picker":
        return _page(run, "Shipping method", "A custom dropdown (not a normal select).", """<div id=dd role=combobox aria-expanded=false aria-label="Shipping method" tabindex=0 class=card style="cursor:pointer">Choose a shipping method &#9662;</div>
<div id=ls role=listbox style="display:none"><div role=option class=card style="cursor:pointer">Standard (5-7 days)</div><div role=option class=card style="cursor:pointer">Express (2 days)</div><div role=option class=card style="cursor:pointer">Overnight</div></div>
<button onclick="rec('picker',{method:document.getElementById('dd').dataset.v||''})">Continue</button>""",
                     "const dd=document.getElementById('dd'),ls=document.getElementById('ls');dd.onclick=()=>{ls.style.display='block';dd.setAttribute('aria-expanded','true')};"
                     "ls.querySelectorAll('[role=option]').forEach(o=>o.onclick=()=>{dd.dataset.v=o.textContent;dd.textContent=o.textContent;ls.style.display='none'})")
    if page == "prices":
        return _page(run, "Supplier A price list", "", f"<div class=card>Steel Bolt M8: <b>USD 0.42</b> each</div><a href='/practice/{run}/prices-b' target=_blank>Open Supplier B</a>")
    if page == "prices-b":
        return _page(run, "Supplier B price list", "", "<div class=card>Steel Bolt M8: <b>USD 0.37</b> each</div>")
    return None


PAGE_TITLES = {"contact": "Contact form", "login": "Login", "frame": "Form in a frame", "nested": "Nested frames",
               "shadow": "Shadow DOM form", "banner": "Cookie banner", "wizard": "Three-step wizard", "invoices": "Invoice table + CSV",
               "customers": "Paginated customers", "upload": "File upload", "booking": "Date and time", "slow": "Slow content",
               "dialog": "Confirm dialog", "newtab": "New tab", "products": "Search + add", "otp": "OTP hand-off",
               "longform": "Long form", "checkout": "Checkout (never pay)", "menu": "Hover menu", "reorder": "Drag to reorder",
               "feed": "Infinite scroll", "editor": "Rich text editor", "survey": "Radios + checkboxes", "fixerror": "Fix a form error",
               "specs": "Product specs", "picker": "Custom dropdown", "prices": "Compare two tabs"}


def _csv() -> str:
    lines = ["invoice,customer,currency,amount,status"] + [f"{a},{b},{c},{d:.2f},{e}" for a, b, c, d, e in INVOICES]
    return "\n".join(lines) + "\n"


router = APIRouter()


@router.get("/practice/{run}/", include_in_schema=False)
@router.get("/practice/{run}/{page}", include_in_schema=False)
def practice_page(run: str, page: str = ""):
    if not known(run):
        raise HTTPException(404, "Not found")
    out = _pages(run, page)
    if out is None:
        raise HTTPException(404, "Not found")
    event(run, f"open {page or 'home'}")
    return out


@router.get("/practice/{run}/file/invoices.csv", include_in_schema=False)
def practice_csv(run: str):
    if not known(run):
        raise HTTPException(404, "Not found")
    event(run, "download invoices.csv")
    record(run, "download", {"file": "invoices.csv"})
    return PlainTextResponse(_csv(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=invoices.csv", "Cache-Control": "no-store"})


@router.post("/practice/api/{run}/upload/file", include_in_schema=False)
async def practice_upload(run: str, file: UploadFile):
    if not known(run):
        raise HTTPException(404, "Not found")
    data = await file.read(2_000_001)
    if len(data) > 2_000_000:
        raise HTTPException(413, "File too big")
    record(run, "upload", {"filename": (file.filename or "")[:120], "bytes": len(data), "head": data[:60].decode("utf-8", "replace")})
    return _page(run, "Uploaded", f"Received {(file.filename or 'file')[:80]} ({len(data)} bytes). Reference: UPLOAD-OK", "")


@router.post("/practice/api/{run}/{task}", include_in_schema=False)
async def practice_record(run: str, task: str, request: Request):
    if not known(run) or not TASK_RE.match(task):
        raise HTTPException(404, "Not found")
    try:
        body = await request.json()
    except Exception:   # noqa: BLE001
        body = {}
    if not isinstance(body, dict):
        body = {"value": str(body)[:500]}
    record(run, task, body)
    return {"ok": True}
