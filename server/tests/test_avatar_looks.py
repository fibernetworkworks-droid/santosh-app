"""v0.48: 100 female 3D looks. The owner picks one; it is checked, stored, and travels on the Hoola Network."""
import itertools

import pytest
from fastapi.testclient import TestClient


def test_catalogue_is_100_unique_worldwide(env):
    from app.avatar import service as av
    L = av.looks()
    assert len(L) == 100 and len({x["id"] for x in L}) == 100
    assert {x["id"] for x in L} == {"f%03d" % i for i in range(1, 101)}
    assert len({x["country"] for x in L}) >= 60                     # from around the world
    assert {x["region"] for x in L} >= {"sa", "ea", "sea", "me", "af", "eu", "am", "oc"}
    for a, b in itertools.combinations(L, 2):                       # no two share name + city
        assert (a["name"], a["city"]) != (b["name"], b["city"])


def test_full_catalogue_every_pair_differs():
    """The renderer's full spec (tool/avatars/looks_full.json): every two looks differ in at least 5 visible features."""
    import json
    import os
    p = os.path.join(os.path.dirname(__file__), "..", "..", "tool", "avatars", "looks_full.json")
    if not os.path.exists(p):
        pytest.skip("full catalogue not present")
    L = json.load(open(p, encoding="utf-8"))

    def f(l):
        return [l["hair"]["style"], l["hair"]["color"], l["skin"], l["eyes"], l["top"]["style"], l["top"]["color"],
                l["top"]["color2"], l["bottom"]["style"], l["bottom"]["color"], l["glasses"]["style"], tuple(l["acc"]), l.get("straps")]
    worst = min(sum(x != y for x, y in zip(f(a), f(b))) for a, b in itertools.combinations(L, 2))
    assert worst >= 5


def test_pick_and_rules(env):
    from app.avatar import service as av
    a = av.get("default")
    assert a["look"] == "" and a["look_info"] is None                # male = Santosh
    with pytest.raises(av.AvatarError):
        av.save("default", look="f010")                             # female looks only for a female avatar
    a = av.save("default", name="Meera", gender="f")
    assert a["look"] == "f001" and a["look_info"]["name"]            # default female look
    a = av.save("default", look="f042")
    assert a["look"] == "f042" and a["look_info"]["id"] == "f042"
    with pytest.raises(av.AvatarError):
        av.save("default", look="f999")
    with pytest.raises(av.AvatarError):
        av.save("default", look="../x")
    assert av.save("default", gender="m")["look"] == ""              # switching gender drops the look
    assert av.save("default", gender="f")["look"] == "f001"


def test_api(env):
    from app import main
    with TestClient(main.app) as c:
        r = c.get("/api/avatar/looks").json()
        assert len(r["looks"]) == 100 and r["default"] == "f001"
        assert c.get("/api/avatar/looks", params={"gender": "m"}).json()["looks"] == []
        assert c.put("/api/avatar", json={"gender": "f", "look": "f007"}).json()["look"] == "f007"
        assert c.put("/api/avatar", json={"look": "f1000"}).status_code == 400
        assert c.get("/api/avatar").json()["look"] == "f007"


def test_look_travels_on_network(env):
    from app.avatar import service as av
    from app.net import identity as idn
    av.save("default", name="Meera", gender="f", look="f033")
    card = idn.my_card("default")
    assert card["avatar_look"] == "f033"
    # a peer's look is stored only when well formed and female
    idn.remember_peer({"address": "hl_zz@other.example", "public_key": "", "avatar_name": "Asha", "avatar_gender": "f", "avatar_look": "f012"})
    assert idn.peer_card("hl_zz@other.example")["avatar_look"] == "f012"
    idn.remember_peer({"address": "hl_yy@other.example", "public_key": "", "avatar_name": "X", "avatar_gender": "f", "avatar_look": "<script>"})
    assert idn.peer_card("hl_yy@other.example")["avatar_look"] == ""
    idn.remember_peer({"address": "hl_xx@other.example", "public_key": "", "avatar_name": "Raju", "avatar_gender": "m", "avatar_look": "f012"})
    assert idn.peer_card("hl_xx@other.example")["avatar_look"] == ""
