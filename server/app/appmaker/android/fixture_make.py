"""Writes android/fixture/spec.json: the project CI compiles on every change of the template (python -m
app.appmaker.android.fixture_make, from server/). Hand-written screens in fixture/screens exercise the whole kit; the
other screens get the code-made version."""
from __future__ import annotations

import json
from pathlib import Path

from .. import kit as K
from . import spec as S

HERE = Path(__file__).resolve().parent / "fixture"
FIXTURE_KEY = "akf1c7a2e0000000000000001"      # v0.314 a real-format app key (the CI e2e server knows it)


def main() -> None:
    tk = K.tokens("enterprise_pro", "paper_ink", None, {"nav": "drawer_bar", "fab": "speed_dial", "mode": "both"})
    plan = {"screens": ["home", "categories", "product", "cart", "orders", "profile", "dashboard", "support"],
            "tabs": ["home", "categories", "cart", "profile"], "flow": ["home", "product", "cart"],
            "code_screens": ["splash", "consent", "notify_permission", "seller_info", "privacy", "delete_account"],
            "labels": {"home": "Home", "categories": "Categories", "product": "Product", "cart": "Cart", "orders": "Orders",
                       "profile": "Profile", "dashboard": "Dashboard", "support": "Help"}}
    facts = {"name": "Sharma Kirana", "tagline": "Fresh groceries in 30 minutes", "phone": "9876543210",
             "address": "12 MG Road, Pune 411001", "hours": "8 am - 10 pm", "upi_id": "sharmakirana@okicici",
             "products": [{"name": "Atta 5 kg", "price": 265, "unit": "bag"}, {"name": "Toor dal 1 kg", "price": 158, "unit": "pack"},
                          {"name": "Amul butter 500 g", "price": 285, "unit": "pack"}]}
    sd = S.seed("Sharma Kirana", "shop", facts, plan)
    from .. import backend as BE                    # v0.314 the app's own backend lists (orders), as a real build carries

    class _P:
        goal, plan = "shop", "{}"
    sch = BE.schema_for(_P())
    sd["backend"] = {"kind": sch["kind"], "order": sch["order"], "signup": True, "collections": sch["collections"]}
    for p in sd["lists"]["products"]:
        p["category"] = "Staples" if "dal" in p["name"].lower() or "atta" in p["name"].lower() else "Dairy"

    class P:
        id, name, goal, language, version = "app_fixture", "Sharma Kirana", "shop", "en", 1
    screens = S.screens_of(plan, {}, sd)
    for s in screens:
        s["actions"] = [{"label": "Open cart", "go": "cart"}] if s["id"] != "cart" else [{"label": "Back to shop", "go": "home"}]
        if s["id"] in ("orders", "product"):
            s["lists"] = ["orders" if s["id"] == "orders" else "products"]
    scene = HERE / "scenes" / "hero.png"           # v0.140 a still of a 3D scene, so CI compiles + opens Scene3D
    if not scene.exists():
        from .. import render as RD
        RD.scene_png({"camera": {"distance": 6.5, "height": 1.2}, "light": "studio",
                      "objects": [{"shape": "lathe", "size": [1.3, 0.9, 1], "material": "satin", "colour": "accent",
                                   "args": {"points": [[0.2, -1], [1, -0.8], [1.15, 0.7], [1.2, 0.9]]}},
                                  {"shape": "sphere", "size": [0.42, 1, 1], "pos": [-0.4, 0.95, 0.2], "material": "glossy", "colour": "primary"},
                                  {"shape": "sphere", "size": [0.36, 1, 1], "pos": [0.45, 0.9, -0.1], "material": "glossy", "colour": "#e8553d"},
                                  {"shape": "capsule", "size": [0.16, 0.7, 1], "pos": [0.1, 1.15, 0.4], "rot": [0, 0, 35], "material": "matte",
                                   "colour": "#f0b429"}]},
                     {"primary": tk["primary"], "accent": tk["accent"]}, scene, size=480)
    fonts_dir = HERE / "fonts"
    fonts = S.fonts_ttf(S.with_tints(tk), fonts_dir)
    rel = {slot: {w: str(Path(p).relative_to(HERE.parents[4])) for w, p in d.items()} for slot, d in fonts.items()}
    kt = {f.stem.replace("Screen", "").lower(): f.read_text() for f in (HERE / "screens").glob("*.kt")}
    spec = {"app": {"name": "Sharma Kirana", "app_id": "in.hoola.preview.fixture", "version_code": 1, "version_name": "1.0",
                    "language": "en", "base_url": "https://example.invalid", "app_key": FIXTURE_KEY},
            "tokens": S.with_tints(tk), "structure": {}, "tabs": plan["tabs"], "start": "home", "flow": plan["flow"],
            "code_screens": plan["code_screens"], "screens": screens,
            "fab": S.fab_of(tk, "shop", plan, plan["labels"]) or {"label": "Cart", "icon": "cart", "go": "cart",
                                                                   "actions": [{"label": "Cart", "icon": "cart", "go": "cart"},
                                                                               {"label": "Orders", "icon": "receipt", "go": "orders"}]},
            "icons": S.icon_paths(), "app_icon": "cart", "fonts": rel, "seed": sd, "screens_kt": kt,
            "scenes": {"hero": str((HERE / "scenes" / "hero.png").relative_to(HERE.parents[4]))}}
    (HERE / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    print("fixture", len(screens), "screens,", len(kt), "hand-written, fonts", list(rel))


if __name__ == "__main__":
    main()
