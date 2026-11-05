"""Prayogshala P0 + P1 (docs/PRAYOG_PHYSICS_LAKH_PLAN.md): one rig serves a family of experiments, the catalogue is
paged, and the physics syllabus is counted honestly."""
import json
from pathlib import Path

import pytest

from app.prayog import count, lsl, service as S, specs

STATIC = Path(__file__).resolve().parent.parent / "app" / "static" / "prayog"


def _fam(tmp_path, monkeypatch, fam: dict):
    d = tmp_path / "families"
    d.mkdir()
    (d / f"{fam['base']}.json").write_text(json.dumps(fam))
    monkeypatch.setattr(specs, "FAM_DIR", d)
    specs.families.cache_clear()
    S.index.cache_clear()
    S._variant.cache_clear()


@pytest.fixture(autouse=True)
def _fresh():
    yield
    specs.families.cache_clear()
    S.index.cache_clear()
    S._variant.cache_clear()


def test_a_variant_is_the_base_lab_with_its_own_numbers(tmp_path, monkeypatch):
    _fam(tmp_path, monkeypatch, {"base": "hookes-law", "chapter": "Elasticity", "variants": [
        {"key": "soft", "title": "Hooke's law: a soft spring", "sample": "Spring A (unknown k)", "params": {"k": 12},
         "unknown": "k", "source": {"title": "Generic spring"}}]})
    lab = S.get("hookes-law--soft")
    assert lab and lab["rig"] == "hookes-law" and lab["params"]["k"] == 12
    assert lab["variant"]["sample"] == "Spring A (unknown k)" and lab["chapter"] == "Elasticity"
    hidden = next(k for k in lab["knobs"] if k["param"] == "k")
    assert hidden["value"] == 12                      # the hidden knob starts at the variant's own value
    assert lsl.run_check(lab)["ok"]
    assert S.get("hookes-law")["params"].get("k") is None   # the base lab is untouched


def test_grid_multiplies_axes_and_fills_titles(tmp_path, monkeypatch):
    _fam(tmp_path, monkeypatch, {"base": "screw-gauge", "grid": {"title": "Screw gauge: {wire} {zero}", "axes": {
        "wire": [{"key": "a", "label": "wire A", "params": {"L": 0.0005}}, {"key": "b", "label": "wire B", "params": {"L": 0.0007}}],
        "zero": [{"key": "z0", "label": "(no zero error)", "params": {"ze": 0}}, {"key": "zp", "label": "(+0.02 mm zero error)", "params": {"ze": 0.00002}}]}}})
    vs = specs.families()["screw-gauge"]["variants"]
    assert [v["key"] for v in vs] == ["a-z0", "a-zp", "b-z0", "b-zp"]
    assert vs[3]["title"] == "Screw gauge: wire B (+0.02 mm zero error)" and vs[3]["params"] == {"L": 0.0007, "ze": 0.00002}


def test_a_variant_that_fails_its_check_is_never_served(tmp_path, monkeypatch):
    _fam(tmp_path, monkeypatch, {"base": "hookes-law", "variants": [
        {"key": "bad", "title": "Bad", "params": {"nonsense": 3}}]})
    assert S.get("hookes-law--bad") is None
    assert S.get("hookes-law--missing") is None and S.get("nolab--x") is None


def test_bad_family_files_are_skipped_not_fatal(tmp_path, monkeypatch):
    _fam(tmp_path, monkeypatch, {"base": "hookes-law", "variants": [{"key": "Bad Key!", "title": "x"}]})
    assert specs.families() == {}
    assert S.get("hookes-law")                        # the catalogue still serves


def test_paged_search_with_filters(tmp_path, monkeypatch):
    _fam(tmp_path, monkeypatch, {"base": "hookes-law", "grid": {"title": "Hooke's law: spring {s}", "axes": {
        "s": [{"key": f"k{k}", "label": str(k), "sample": f"Spring {k}", "params": {"k": k}} for k in range(11, 31)]}}})
    page = S.search_page(base="hookes-law", limit=7, page=2)
    assert page["total"] == 21 and len(page["labs"]) == 7 and page["page"] == 2
    bases = S.search_page(variants=False, limit=200)
    assert all(r["base"] == r["id"] for r in bases["labs"])
    hk = next(r for r in bases["labs"] if r["id"] == "hookes-law")
    assert hk["n_variants"] == 20
    assert S.search_page(q="spring 17")["labs"][0]["id"] == "hookes-law--k17"
    assert S.search_page(level="class xii", base="hookes-law")["total"] == 0


def test_api_pages_and_serves_variants(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.prayog.api import make_router
    _fam(tmp_path, monkeypatch, {"base": "hookes-law", "variants": [{"key": "soft", "title": "Soft", "params": {"k": 12}}]})
    app = FastAPI()
    app.include_router(make_router())
    c = TestClient(app)
    d = c.get("/api/prayog/labs?base=hookes-law&limit=1").json()
    assert d["total"] == 2 and len(d["labs"]) == 1
    assert c.get("/api/prayog/labs/hookes-law--soft").json()["lab"]["params"]["k"] == 12
    assert c.get("/api/prayog/labs/hookes-law--nope").status_code == 404


# ------------------------------------------------------------------- the real families shipped in the repo
def test_every_shipped_variant_passes_the_checker_and_its_check():
    bad, n = [], 0
    for b, fam in specs.families().items():
        assert b in S.labs(), f"family for unknown lab {b}"
        assert (STATIC / "exp" / f"{fam.get('rig') or b}.js").exists()
        for v in fam["variants"]:
            n += 1
            lab = S.get(specs.vid(b, v["key"]))
            if not lab:
                bad.append(specs.vid(b, v["key"]))
            assert len(v["title"]) <= 80
    assert not bad, bad
    assert n >= 2


def test_shipped_families_name_a_source_or_say_generic():
    for b, fam in specs.families().items():
        for v in fam["variants"]:
            assert v.get("source") or "unknown" in (v.get("sample") or "").lower() or "generic" in json.dumps(v).lower() or fam.get("source"), (b, v["key"])


def test_lab_page_runs_a_variant_on_its_family_rig():
    html = (STATIC / "lab.html").read_text()
    assert "d.lab.rig || d.lab.id" in html
    js = (STATIC / "studio" / "studio.js").read_text()
    assert "DEFS[lab.rig || lab.id]" in js and "This experiment" in js


# ------------------------------------------------------------------- P0: the syllabus count
def test_count_checks_the_schema():
    good = {"level": "ug", "sources": [{"id": "s1", "title": "T", "checked": False}], "chapters": [{"name": "Optics", "setups": [
        {"id": "newton-rings", "title": "Newton's rings", "src": "s1", "kind": "practical", "methods": ["sodium lamp", "mercury green"],
         "samples": [], "unknowns": ["wavelength", "radius of curvature"]}]}]}
    count.check(good, "x")
    assert count.variants(good["chapters"][0]["setups"][0]) == 4
    t = count.totals([good])
    assert t["setups"] == 1 and t["variants"] == 4
    for broken in ({**good, "level": "phd2"},
                   {**good, "sources": [{"id": "s1", "title": "T"}]},
                   {**good, "chapters": [{"name": "O", "setups": [{**good["chapters"][0]["setups"][0], "src": "nope"}]}]},
                   {**good, "chapters": [{"name": "O", "setups": [{**good["chapters"][0]["setups"][0], "methods": ["a", "a"]}]}]}):
        with pytest.raises(count.SyllabusError):
            count.check(broken, "x")


def test_shipped_syllabus_files_are_valid():
    docs = count.load()
    for d in docs:
        for ch in d["chapters"]:
            for st in ch["setups"]:
                if st.get("built"):
                    assert S.get(st["built"]), st["built"]
    count.totals(docs)


def test_no_kernel_pack_or_lab_pack_is_silently_left_out():
    """A kernel-name collision makes the loader skip a WHOLE pack with only a log line, so one worker's pack can
    silently erase another's. Every pack module on disk must have loaded, and every lab builder must have produced a lab."""
    import pkgutil

    from app.prayog import kernels as KN, labs as L, packs as P, service as S

    on_disk = sorted(m.name for m in pkgutil.iter_modules(P.__path__))
    assert sorted(KN.PACKS) == on_disk, f"kernel packs left out: {sorted(set(on_disk) - set(KN.PACKS))}"
    S.labs.cache_clear()
    built = {b.__name__ for b in S._all_builders()}
    served = len(S.labs())
    assert served == len(S._all_builders()), f"{len(S._all_builders()) - served} lab builder(s) produced no lab (checker refused)"
    assert built
    lab_mods = sorted(m.name for m in pkgutil.iter_modules(L.__path__))
    assert lab_mods                                   # and the lab packs themselves all imported (a bad one is only logged)
    import importlib
    for m in lab_mods:
        importlib.import_module(f"{L.__name__}.{m}")
