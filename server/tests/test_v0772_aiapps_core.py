def test_core(env):
    from app.aiapps import store as ST, runtime as RT
    a = ST.create("t1", "Sharma Kirana", soul={"name": "Sharma Kirana", "about": "Grocery shop in Pune",
                  "facts": ["Open 9 am to 9 pm", "Delivery free above Rs 500"], "actions": ["ticket"]})
    assert a["errors"] == [], a
    r = ST.row("t1", a["id"])
    RT.ASK[0] = lambda s, p, n: "We are open 9 am to 9 pm."
    out = RT.answer(r, "When are you open?", channel="preview")
    print(out)
    assert out["outcome"] == "model"
    assert RT.answer(r, "my OTP is 123456", channel="preview")["outcome"] == "refused"
    assert RT.answer(r, "please refund my money", channel="preview")["outcome"] == "refused"
    RT.ASK[0] = lambda s, p, n: "Delivery is Rs 50."
    assert RT.answer(r, "delivery charge?", channel="preview")["outcome"] == "unknown"
    assert RT.answer(r, "hi", channel="page")["outcome"] == "paused"
    p = ST.publish("t1", a["id"], a["draft_hash"])
    assert p["version"] == 1
    r = ST.row("t1", a["id"])
    RT.ASK[0] = lambda s, p, n: "We are open 9 am to 9 pm."
    assert RT.answer(r, "timings", channel="page")["outcome"] == "model"
    t = RT.answer(r, "my order arrived damaged", channel="page")
    print(t)
    assert t["outcome"] == "action"


def test_a_secret_is_never_stored(env):
    from app.aiapps import store as ST, runtime as RT
    from app.aiapps.models import AiAppMessage
    from app.db import session
    a = ST.create("t1", "X", soul={"name": "X", "about": "Shop"})
    out = RT.answer(ST.row("t1", a["id"]), "my OTP is 482913 please", channel="preview")
    assert out["outcome"] == "refused"
    with session() as s:
        q = s.get(AiAppMessage, out["message_id"]).question
    assert "482913" not in q and "******" in q
