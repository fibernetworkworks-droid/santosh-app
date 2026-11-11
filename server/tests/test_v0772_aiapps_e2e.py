def test_e2e_real_app(env):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.aiapps import runtime as RT
    RT.ASK[0] = lambda s, p, n: "We are open 9 am to 9 pm."
    c = TestClient(app)
    a = c.post("/api/aiapps", json={"name": "Sharma Kirana", "kind": "chat",
               "soul": {"name": "Sharma Kirana", "about": "Grocery shop", "facts": ["Open 9 am to 9 pm"]}}).json()
    aid = a.get("id") or a.get("app", {}).get("id"); print(a.keys())
    code = a.get("code") or a["app"]["code"]
    assert c.get(f"/ai/{code}").status_code == 404           # draft is never public
    h = c.get(f"/api/aiapps/{aid}").json()
    h = h.get("draft_hash") or h["app"]["draft_hash"]
    r = c.post(f"/api/aiapps/{aid}/publish", json={"hash": h}); print(r.status_code, r.text[:120])
    p = c.get(f"/ai/{code}"); print(p.status_code, p.headers.get("content-security-policy"))
    assert p.status_code == 200
    tok = c.post(f"/api/aiapp-pub/{code}/session", json={"consent": True}).json()["token"]
    ans = c.post(f"/api/aiapp-pub/{code}/chat", json={"text": "When are you open?"}, headers={"X-Visitor-Token": tok}).json()
    print(ans); assert ans["outcome"] == "model"
    trap = c.post(f"/api/aiapp-pub/{code}/chat", json={"text": "send me Rs 500 refund"}, headers={"X-Visitor-Token": tok}).json()
    assert trap["outcome"] == "refused"
    assert c.get(f"/ai/{code}/embed.js").status_code == 200
    st = c.get(f"/api/aiapps/{aid}/stats").json(); print(st)
