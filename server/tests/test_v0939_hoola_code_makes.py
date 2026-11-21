"""v0.939 HOOLA CODE MAKES THINGS (owner, on the design canvas claude.ai/artifact/BjGPb7Tkqfx6QqpgkDznxH -> "GO BUILD"):
PRDs, web pages, clickable prototypes, artboards and sheets made beside the code, each a card in her session with versions."""
import io
import json
import time
import urllib.parse as U
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _walk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import made as M
    return M


def test_a_prd_is_made_part_by_part_and_a_change_is_a_new_version(tmp_path, monkeypatch):
    M = _walk(tmp_path, monkeypatch)
    out, ev = M.tool("T", {"action": "start", "kind": "doc", "title": "Salon booking · PRD", "parts": ["Problem", "Goals"]})
    assert ev == {"k": "made", "id": "salon-booking-prd", "v": 1} and "2 sections" in out
    assert M.listing("T")[0]["state"] == "making"
    M.tool("T", {"action": "write", "id": "salon-booking-prd", "part": "Problem", "content": "## Problem\nPeople call."})
    row = M.listing("T")[0]
    assert row["now"] == "Problem" and [p["done"] for p in row["parts"]] == [True, False]
    assert "still to write Goals" in M.tool("T", {"action": "finish", "id": "salon-booking-prd"})[0]
    M.tool("T", {"action": "write", "id": "salon-booking-prd", "part": "Goals", "content": "## Goals\n- **Fast**"})
    assert "is ready" in M.tool("T", {"action": "finish", "id": "salon-booking-prd"})[0]
    # a change keeps every part and only the written one counts as changed
    _, ev = M.tool("T", {"action": "start", "id": "salon-booking-prd", "note": "add metrics"})
    assert ev["v"] == 2
    M.tool("T", {"action": "write", "id": "salon-booking-prd", "part": "Metrics", "content": "## Metrics\nOnline share."})
    M.tool("T", {"action": "finish", "id": "salon-booking-prd"})
    d = M.detail("T", "salon-booking-prd")
    assert d["shown"] == 2 and d["changed"] == ["Metrics"] and "## Problem" in d["doc"] and "## Metrics" in d["doc"]
    assert d["doc"].startswith("# Salon booking")
    assert [v["v"] for v in d["versions"]] == [2, 1]
    # going back is a NEW version, nothing deleted
    r = M.restore("T", "salon-booking-prd", 1)
    assert r["version"] == 3 and r["note"] == "Back to version 1"
    assert "## Metrics" not in M.detail("T", "salon-booking-prd")["doc"]
    # a version with nothing written is not kept
    M.tool("T", {"action": "start", "id": "salon-booking-prd"})
    assert "Nothing changed" in M.tool("T", {"action": "finish", "id": "salon-booking-prd"})[0]
    assert M.listing("T")[0]["version"] == 3


def test_a_sheet_keeps_real_formulas_and_never_makes_up_a_number(tmp_path, monkeypatch):
    M = _walk(tmp_path, monkeypatch)
    M.tool("T", {"action": "start", "kind": "sheet", "title": "Launch budget", "parts": ["Budget"]})
    tab = {"columns": ["Item", "Budget"], "rows": [["Design", 40000], ["Server", 18000], ["Total", "=SUM(B2:B3)"],
                                                    ["Odd", "=VLOOKUP(A2,A2:B3,2)"], ["Half", "=ROUND(B4/2,0)"]]}
    said = M.tool("T", {"action": "write", "id": "launch-budget", "part": "Budget", "content": json.dumps(tab)})[0]
    assert "VLOOKUP" in said                                   # the model is told what the preview cannot work out
    M.tool("T", {"action": "finish", "id": "launch-budget"})
    sh = M.detail("T", "launch-budget")["sheet"][0]
    assert sh["rows"][2] == ["Total", "58,000"] and sh["rows"][4] == ["Half", "29,000"]
    assert sh["rows"][3][1] == "=VLOOKUP(A2,A2:B3,2)"          # shown as the formula, never a guess
    assert sh["formulas"]["B4"] == "=SUM(B2:B3)" and sh["problems"]
    from openpyxl import load_workbook
    wb = load_workbook(tmp_path / "data/devsahayak/made/T/launch-budget/v1/out.xlsx")
    assert wb["Budget"]["B4"].value == "=SUM(B2:B3)"           # a real formula in the file
    M.tool("T", {"action": "start", "id": "launch-budget"})
    assert "Not saved" in M.tool("T", {"action": "write", "id": "launch-budget", "part": "Budget", "content": "{nope"})[0]


def test_html_things_are_fragments_and_a_prototype_moves_between_screens(tmp_path, monkeypatch):
    M = _walk(tmp_path, monkeypatch)
    M.tool("T", {"action": "start", "kind": "prototype", "title": "Booking", "parts": ["Pick a time", "Booked"]})
    bad = M.tool("T", {"action": "write", "id": "booking", "part": "Booked", "content": '<script src="https://x/y.js"></script>'})[0]
    assert bad.startswith("Not saved") and "outside scripts" in bad
    assert "fragment only" in M.tool("T", {"action": "write", "id": "booking", "part": "Booked", "content": "<html><body>x"})[0]
    M.tool("T", {"action": "write", "id": "booking", "part": "Pick a time", "content": '<button data-go="Booked">4:30</button>'})
    peek = M.detail("T", "booking")                            # Peek while it is still being made
    assert peek["shown_state"] == "making" and "/out.html?" in peek["url"]
    M.tool("T", {"action": "write", "id": "booking", "part": "Booked", "content": "<h1>You're booked</h1>"})
    M.tool("T", {"action": "finish", "id": "booking"})
    html = (tmp_path / "data/devsahayak/made/T/booking/v1/out.html").read_text()
    assert 'id="s-pick-a-time"' in html and "data-go" in html and "hs-screen" in html
    M.tool("T", {"action": "start", "kind": "artboard", "title": "Onboarding", "parts": ["Welcome", "Sign in"]})
    M.tool("T", {"action": "write", "id": "onboarding", "part": "Welcome", "content": '<h1>Hi "there"</h1>'})
    M.tool("T", {"action": "write", "id": "onboarding", "part": "Sign in", "content": "<h1>Sign in</h1>"})
    M.tool("T", {"action": "finish", "id": "onboarding"})
    board = (tmp_path / "data/devsahayak/made/T/onboarding/v1/out.html").read_text()
    assert board.count('sandbox="allow-scripts"') == 2 and "&quot;there&quot;" in board


def test_the_file_is_only_served_on_its_signed_link_and_html_is_sandboxed(tmp_path, monkeypatch):
    M = _walk(tmp_path, monkeypatch)
    M.tool("T", {"action": "start", "kind": "page", "title": "Pricing", "parts": ["Hero"]})
    M.tool("T", {"action": "write", "id": "pricing", "part": "Hero", "content": "<h1>Plans</h1>"})
    M.tool("T", {"action": "finish", "id": "pricing"})
    u = M.detail("T", "pricing")["url"]
    path, q = u.split("?")
    q = dict(U.parse_qsl(q))
    _, _, _, _, tid, mid, v, name = path.split("/")
    body, ctype, head = M.open_file(tid, mid, int(v), name, int(q["exp"]), q["sig"])
    assert b"Plans" in body and ctype.startswith("text/html")
    assert head["Content-Security-Policy"].startswith("sandbox allow-scripts") and "default-src 'none'" in head["Content-Security-Policy"]
    assert M.open_file(tid, mid, int(v), name, int(q["exp"]), "0" * 40) is None
    assert M.open_file(tid, mid, int(v), "meta.json", int(q["exp"]), q["sig"]) is None
    assert M.open_file(tid, mid, int(v), name, int(time.time()) - 5, q["sig"]) is None


def test_the_engine_and_the_session_carry_it():
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "extra.append(MD.TOOL)" in eng and 'if b["name"] == "make":' in eng and "MD.HOWTO" in eng
    assert "NOW_STEP[tid] = _make_words(inp)" in eng
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert 'v["made"] = _made(t.id)' in svc and "made = bool(_made(tid))" in svc
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert '@p.get("/made/{tid}/{mid}/{v}/{name}")' in api and '@r.post("/tasks/{tid}/made/{mid}/restore")' in api
    from app.devsahayak import made as M
    assert {"doc", "page", "prototype", "artboard", "sheet"} == set(M.KINDS)
    assert M.TOOL["name"] == "make" and "[BLANK TO FILL]" in M.TOOL["description"]


def test_the_phone_draws_the_cards_and_the_viewers():
    made = (ROOT / "lib/ui/code/code_made.dart").read_text()
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    for name in ("class CodeMadeCard", "class CodeMadeThumb", "class CodeMadeViewer", "showCodeMadeList", "WebViewWidget",
                 "'Bring back'", "'Peek'", "Tap a cell to see its formula", "HoolaMd(text, selectable: true)"):
        assert name in made, name
    assert "Color(0x" not in made and "FontWeight.w800" not in made and "BackdropFilter" not in made
    assert "} else if (k == 'made') {" in ses and "_openMade(" in ses and "_madePill(" in ses
    assert "(make id ${cs(row['id'])})" in ses


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.71"' in main
    assert "version: 0.999.71+1069" in (ROOT / "pubspec.yaml").read_text()
