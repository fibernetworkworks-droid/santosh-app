"""Measure Gyaan on a test set: recall@k (the right source in the top k) per language slice, and abstention (questions with
no answer in the files must come back nahi_mila). `python -m app.gyaan.evaluate [k]` prints a table; the API / tool return
the same numbers. Runs on a throw-away owner, never on real data unless `tenant` is given."""
from __future__ import annotations

import sys
import uuid
from typing import Any

from . import evalset, ingest, search, store


def evaluate(questions: list[dict] | None = None, corpus: list | None = None, k: int = 8, tenant: str = "",
             queries_for: dict[str, list[str]] | None = None) -> dict[str, Any]:
    temp = not tenant
    tenant = tenant or f"eval-{uuid.uuid4().hex[:8]}"
    try:
        if corpus is not None or temp:
            for title, kind, text in (corpus if corpus is not None else evalset.CORPUS):
                src = "mail" if kind == "mail" else ("note" if kind == "note" else "file")
                ingest.add_text(tenant, src, f"eval:{title}", title, text, "sheet" if kind == "sheet" else
                                ("mail" if kind == "mail" else "doc"))
            while ingest.embed_pending(tenant):
                pass
        rows = []
        for q in (questions if questions is not None else evalset.QUESTIONS):
            r = search.search(tenant, q["q"], (queries_for or {}).get(q["q"]) or q.get("queries"), top=k, fast=True, memory=False)
            titles = [h["title"] for h in r["hits"]]
            exp = q.get("expect")
            if exp is None:
                ok = r["status"] == "nahi_mila"
            else:
                ok = exp in titles[:k]
            rows.append({"q": q["q"], "lang": q.get("lang", ""), "expect": exp, "ok": ok, "status": r["status"],
                         "got": titles[:3], "rank": (titles.index(exp) + 1) if exp in titles else None})
        out: dict[str, Any] = {"k": k, "rows": rows, "slices": {}}
        for lang in sorted({r["lang"] for r in rows}):
            ans = [r for r in rows if r["lang"] == lang and r["expect"]]
            out["slices"][lang] = {"recall": round(sum(r["ok"] for r in ans) / len(ans), 3) if ans else None, "n": len(ans)}
        ab = [r for r in rows if not r["expect"]]
        ans = [r for r in rows if r["expect"]]
        out["recall"] = round(sum(r["ok"] for r in ans) / len(ans), 3) if ans else None
        out["abstain"] = round(sum(r["ok"] for r in ab) / len(ab), 3) if ab else None
        out["false_found"] = [r["q"] for r in ab if not r["ok"]]
        out["missed"] = [r["q"] for r in ans if not r["ok"]]
        from . import embed
        e = embed.embedder()
        out["embedder"] = e.name if e else "none"
        return out
    finally:
        if temp:
            store.wipe(tenant)


def main() -> None:
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    r = evaluate(k=k)
    print(f"Gyaan eval  embedder={r['embedder']}  recall@{k}={r['recall']}  abstain={r['abstain']}")
    for lang, s in r["slices"].items():
        print(f"  {lang:9s} recall {s['recall']}  ({s['n']} questions)")
    for q in r["missed"]:
        print("  MISSED:", q)
    for q in r["false_found"]:
        print("  SHOULD SAY NAHI MILA:", q)


if __name__ == "__main__":
    main()
