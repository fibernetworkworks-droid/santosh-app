"""PC bridge end to end: the real server (uvicorn) + the real Santosh Desktop code + a fake TallyPrime on port 9000-style XML.

Phone pairs a PC -> PC connects out over WebSocket -> phone and Santosh's agent search files, pull a file to the phone,
send a file to the PC, read Tally, and make an approved Tally entry. Paths outside shared folders are refused; removing
the PC from the phone disconnects it.
"""
import asyncio
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
import pytest
import uvicorn

from tests.test_bazar import bz  # noqa: F401  (fixture)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


LEDGERS = """<ENVELOPE><BODY><DATA><COLLECTION>
<LEDGER NAME="Sharma Traders"><PARENT>Sundry Debtors</PARENT><CLOSINGBALANCE>-45000.00</CLOSINGBALANCE><SANTOSHPRIMARY>Sundry Debtors</SANTOSHPRIMARY></LEDGER>
<LEDGER NAME="Gupta Hardware&#4;"><PARENT>Akola Debtors</PARENT><CLOSINGBALANCE>-12500.50</CLOSINGBALANCE><SANTOSHPRIMARY>Sundry Debtors</SANTOSHPRIMARY></LEDGER>
<LEDGER NAME="Steel Supplier"><PARENT>Sundry Creditors</PARENT><CLOSINGBALANCE>30000.00</CLOSINGBALANCE><SANTOSHPRIMARY>Sundry Creditors</SANTOSHPRIMARY></LEDGER>
<LEDGER NAME="Sales"><PARENT>Sales Accounts</PARENT><CLOSINGBALANCE>75000.00</CLOSINGBALANCE></LEDGER>
<LEDGER NAME="Cash"><PARENT>Cash-in-Hand</PARENT><CLOSINGBALANCE>-5000.00</CLOSINGBALANCE></LEDGER>
</COLLECTION></DATA></BODY></ENVELOPE>"""

VOUCHERS = """<ENVELOPE><BODY><DATA><COLLECTION>
<VOUCHER><DATE>20261015</DATE><VOUCHERTYPENAME>GST Sales</VOUCHERTYPENAME><VOUCHERNUMBER>101</VOUCHERNUMBER><PARTYLEDGERNAME>Sharma Traders</PARTYLEDGERNAME><AMOUNT>-45000.00</AMOUNT><SANTOSHSALES>Yes</SANTOSHSALES></VOUCHER>
<VOUCHER><DATE>20261016</DATE><VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME><VOUCHERNUMBER>7</VOUCHERNUMBER><PARTYLEDGERNAME>Gupta Hardware</PARTYLEDGERNAME><AMOUNT>5000.00</AMOUNT><SANTOSHRCPT>Yes</SANTOSHRCPT></VOUCHER>
</COLLECTION></DATA></BODY></ENVELOPE>"""


class FakeTally(BaseHTTPRequestHandler):
    imports: list[str] = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        if "Import Data" in body:
            FakeTally.imports.append(body)
            out = "<RESPONSE><CREATED>1</CREATED><ALTERED>0</ALTERED><ERRORS>0</ERRORS></RESPONSE>"
        elif "<TYPE>Company</TYPE>" in body:
            out = '<ENVELOPE><BODY><DATA><COLLECTION><COMPANY NAME="Patil Steel"><NAME>Patil Steel</NAME></COMPANY></COLLECTION></DATA></BODY></ENVELOPE>'
        elif "<TYPE>Ledger</TYPE>" in body:
            out = LEDGERS
        elif "<TYPE>Voucher</TYPE>" in body:
            out = VOUCHERS
        else:
            out = "<ENVELOPE><BODY><DATA><COLLECTION></COLLECTION></DATA></BODY></ENVELOPE>"
        data = out.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def _wait(cond, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def world(bz, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("API_KEY", "phone-key")
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "relay"))
    monkeypatch.setenv("SANTOSH_DESKTOP_HOME", str(tmp_path / "desk"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    from app.pc.hub import hub
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", ws="websockets"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    assert _wait(lambda: server.started)
    tport = _free_port()
    tally_srv = HTTPServer(("127.0.0.1", tport), FakeTally)
    threading.Thread(target=tally_srv.serve_forever, daemon=True).start()
    FakeTally.imports = []

    docs = tmp_path / "Accounts"
    (docs / "Oct").mkdir(parents=True)
    (docs / "Oct" / "Invoice_Sharma_Traders_101.txt").write_text("TAX INVOICE\nSharma Traders\nGSTIN 27ABCDE1234F1Z5\nTotal 45,000")
    (docs / "bank statement march.csv").write_text("date,amount\n2026-03-01,1000\n")
    secret = tmp_path / "Private"
    secret.mkdir()
    (secret / "salary.txt").write_text("secret")
    base = f"http://127.0.0.1:{port}"
    phone = httpx.Client(base_url=base, headers={"Authorization": "Bearer phone-key"}, timeout=30)
    yield {"base": base, "phone": phone, "docs": docs, "secret": secret, "tport": tport, "hub": hub, "tmp": tmp_path,
           "svc": bz["svc"], "conv": bz["conv"]}
    server.should_exit = True
    tally_srv.shutdown()
    th.join(timeout=5)


def _start_pc(w):
    from santosh_desktop.actions import Actions
    from santosh_desktop.bridge import Bridge, pair
    from santosh_desktop.config import Config, save
    from santosh_desktop.index import Index
    from santosh_desktop.tally import Tally
    code = w["phone"].post("/api/pc/pair/start").json()["code"]
    dev, tok = pair(w["base"], code, "Office PC", "Windows 10")
    cfg = Config(server=w["base"], device_id=dev, folders=[str(w["docs"])], inbox=str(w["tmp"] / "Inbox"), name="Office PC")
    cfg.token = tok
    save(cfg)
    idx = Index(w["tmp"] / "index.db")
    assert idx.rebuild(cfg.folders) == 2
    acts = Actions(cfg, idx, log=lambda m: None, tally=Tally("127.0.0.1", w["tport"]))
    br = Bridge(cfg, acts, on_status=lambda s: None)
    br.start()
    assert _wait(lambda: w["hub"].is_online("default"))
    return cfg, br


def test_pair_code_is_single_use_and_checked(world):
    from santosh_desktop.bridge import pair
    code = world["phone"].post("/api/pc/pair/start").json()["code"]
    pair(world["base"], code, "PC", "Windows")
    with pytest.raises(ValueError, match="galat"):
        pair(world["base"], code, "PC2", "Windows")
    with pytest.raises(ValueError):
        pair(world["base"], "000000", "PC3", "Windows")
    assert httpx.post(world["base"] + "/api/pc/pair/start").status_code == 401   # phone must be signed in


def test_end_to_end(world):
    cfg, br = _start_pc(world)
    phone = world["phone"]
    try:
        devs = phone.get("/api/pc/devices").json()["devices"]
        assert devs[0]["online"] and devs[0]["name"] == "Office PC"
        assert _wait(lambda: phone.get("/api/pc/devices").json()["devices"][0]["tally"].get("available"))

        # phone searches the PC and pulls the invoice
        res = phone.post("/api/pc/search", json={"query": "sharma invoice"}).json()["results"]
        assert res[0]["name"] == "Invoice_Sharma_Traders_101.txt" and res[0]["category"] in ("GST", "Invoice")
        f = phone.post("/api/pc/pull", json={"path": res[0]["path"]}).json()
        got = httpx.get(world["base"] + f["url"])
        assert got.status_code == 200 and b"Sharma Traders" in got.content
        assert httpx.get(world["base"] + f["url"].replace("sig=", "sig=x")).status_code == 403

        # phone sends a photo to the PC's Santosh Inbox
        r = phone.post("/api/pc/send", files={"file": ("bill photo.jpg", b"\xff\xd8jpegdata", "image/jpeg")}).json()
        assert Path(r["saved_path"]).read_bytes() == b"\xff\xd8jpegdata" and "Inbox" in r["saved_path"]

        # outside the shared folders: refused
        bad = phone.post("/api/pc/pull", json={"path": str(world["secret"] / "salary.txt")})
        assert bad.status_code == 400 and "share" in bad.json()["detail"]
        bad2 = phone.post("/api/pc/pull", json={"path": str(world["docs"] / ".." / "Private" / "salary.txt")})
        assert bad2.status_code == 400

        # Santosh's agent: Tally receivables (runs in a worker thread like every Connector call)
        svc, conv = world["svc"], world["conv"]
        rec = svc.run("default", conv, "pc-bridge", "tally_report", {"report": "receivables"})
        assert rec["total_text"] == "₹57,500.50" and rec["parties"][0]["party"] == "Sharma Traders"
        sales = svc.run("default", conv, "pc-bridge", "tally_report", {"report": "sales", "from_date": "2026-10-01",
                                                                        "to_date": "2026-10-31"})
        assert sales["count"] == 1 and sales["total"] == 45000.0
        sent = svc.run("default", conv, "pc-bridge", "send_file", {"path": res[0]["path"]})
        assert sent["pc_file"]["name"] == "Invoice_Sharma_Traders_101.txt"

        # a Tally entry needs the tap; only the frozen entry is posted, with Tally's sign rules
        ap = svc.run("default", conv, "pc-bridge", "tally_voucher",
                     {"voucher_type": "Receipt", "party": "sharma traders", "amount": 20000, "ledger": "Cash"})
        assert ap["needs_approval"] and not FakeTally.imports
        out = svc.decide("default", ap["approval_id"], "approve")
        assert "entry ho gayi" in out["outcome"]["message"]
        xml = FakeTally.imports[-1]
        assert "<LEDGERNAME>Cash</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-20000.00</AMOUNT>" in xml
        assert "<LEDGERNAME>Sharma Traders</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>20000.00</AMOUNT>" in xml

        from app.pc import service as pcs
        pcs.flush_writes()
        jobs = phone.get("/api/pc/jobs").json()["jobs"]
        assert {"search", "send_file", "save_file", "tally_report", "tally_voucher"} <= {j["action"] for j in jobs}

        # paused on the PC: nothing runs
        cfg.paused = True
        br.push_info()
        assert _wait(lambda: phone.get("/api/pc/devices").json()["devices"][0]["paused"])
        assert phone.post("/api/pc/search", json={"query": "sharma"}).status_code == 400
        cfg.paused = False
        br.push_info()

        # removed from the phone: PC is disconnected and forgets its token
        dev_id = devs[0]["id"]
        assert phone.delete(f"/api/pc/devices/{dev_id}").json()["removed"]
        assert _wait(lambda: not world["hub"].is_online("default"))
        assert _wait(lambda: not cfg.paired)
    finally:
        br.stop()


def test_offline_pc_is_reported(world):
    from app.bazar.connectors.base import ToolError
    st = world["svc"].find("default", "office pc tally")
    pc = [p for p in st["packs"] if p["pack_id"] == "pc-bridge"][0]
    assert pc["status"] == "pc_not_paired"
    with pytest.raises(ToolError, match="offline"):
        world["svc"].run("default", world["conv"], "pc-bridge", "search", {"query": "x"})
    assert world["phone"].post("/api/pc/search", json={"query": "x"}).status_code == 409
