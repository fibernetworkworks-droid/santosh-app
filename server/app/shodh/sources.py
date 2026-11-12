"""Official open scholarly APIs, each normalised to one shape: {doi, title, authors[], year, venue, abstract, url,
oa_url, citations, ids{}, via}. No scraping: only documented public endpoints (OpenAlex, Crossref, arXiv, PubMed
E-utilities, Semantic Scholar Graph API, Unpaywall). `TRANSPORT` lets tests answer without the network."""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

log = logging.getLogger("santosh.shodh.sources")
TRANSPORT = None
TIMEOUT = 20
UA = "Hoola-Shodh/1.0 (research assistant; mailto:{email})"
ALL = ("openalex", "crossref", "arxiv", "pubmed", "semantic_scholar")


class SourceError(Exception):
    pass


def _client(email: str = ""):
    import httpx
    return httpx.Client(timeout=TIMEOUT, transport=TRANSPORT, follow_redirects=True,
                        headers={"User-Agent": UA.format(email=email or "unknown"), "Accept": "application/json"})


def clean_doi(v: str) -> str:
    d = str(v or "").strip()
    d = re.sub(r"(?i)^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d)
    return d.lower() if re.match(r"10\.\d{4,9}/\S+", d) else ""


def _ws(s: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(s or ""))).strip()


def _year(s: Any) -> int:
    m = re.search(r"\b(19|20)\d{2}\b", str(s or ""))
    return int(m.group(0)) if m else 0


def _abstract_from_index(idx: dict | None) -> str:
    """OpenAlex keeps abstracts as an inverted index {word: [positions]}."""
    if not isinstance(idx, dict):
        return ""
    pos: dict[int, str] = {}
    for w, ps in idx.items():
        for p in ps or []:
            pos[int(p)] = w
    return " ".join(pos[i] for i in sorted(pos))


# ---------------------------------------------------------------- the adapters
def openalex(q: str, year_from: int = 0, limit: int = 20, email: str = "") -> list[dict]:
    params: dict[str, Any] = {"search": q, "per-page": min(limit, 50)}
    if year_from:
        params["filter"] = f"from_publication_date:{year_from}-01-01"
    if email:
        params["mailto"] = email
    with _client(email) as c:
        r = c.get("https://api.openalex.org/works", params=params)
    if r.status_code >= 400:
        raise SourceError(f"OpenAlex {r.status_code}")
    out = []
    for w in r.json().get("results") or []:
        loc = w.get("primary_location") or {}
        out.append({"doi": clean_doi(w.get("doi")), "title": _ws(w.get("display_name") or w.get("title")),
                    "authors": [a.get("author", {}).get("display_name", "") for a in w.get("authorships") or []][:30],
                    "year": int(w.get("publication_year") or 0), "venue": _ws((loc.get("source") or {}).get("display_name")),
                    "abstract": _abstract_from_index(w.get("abstract_inverted_index")), "url": w.get("id") or "",
                    "oa_url": (w.get("open_access") or {}).get("oa_url") or "", "citations": int(w.get("cited_by_count") or 0),
                    "ids": {"openalex": w.get("id") or ""}, "via": "openalex"})
    return out


def _crossref_item(it: dict) -> dict:
    issued = ((it.get("issued") or it.get("published") or {}).get("date-parts") or [[0]])[0]
    return {"doi": clean_doi(it.get("DOI")), "title": _ws((it.get("title") or [""])[0]),
            "authors": [" ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name", "")
                        for a in it.get("author") or []][:30],
            "year": int(issued[0] or 0) if issued else 0, "venue": _ws((it.get("container-title") or [""])[0]),
            "abstract": _ws(it.get("abstract")), "url": it.get("URL") or "", "oa_url": "",
            "citations": int(it.get("is-referenced-by-count") or 0), "ids": {}, "via": "crossref"}


def crossref(q: str, year_from: int = 0, limit: int = 20, email: str = "") -> list[dict]:
    params: dict[str, Any] = {"query": q, "rows": min(limit, 50)}
    if year_from:
        params["filter"] = f"from-pub-date:{year_from}"
    if email:
        params["mailto"] = email
    with _client(email) as c:
        r = c.get("https://api.crossref.org/works", params=params)
    if r.status_code >= 400:
        raise SourceError(f"Crossref {r.status_code}")
    return [_crossref_item(it) for it in ((r.json().get("message") or {}).get("items") or [])]


def crossref_doi(doi: str, email: str = "") -> dict | None:
    """The truth check for a DOI: Crossref's record, or None when the DOI does not exist."""
    d = clean_doi(doi)
    if not d:
        return None
    with _client(email) as c:
        r = c.get(f"https://api.crossref.org/works/{d}")
    if r.status_code == 404:
        return None
    if r.status_code >= 400:
        raise SourceError(f"Crossref {r.status_code}")
    return _crossref_item(r.json().get("message") or {})


def arxiv(q: str, year_from: int = 0, limit: int = 20, email: str = "") -> list[dict]:
    with _client(email) as c:
        r = c.get("https://export.arxiv.org/api/query", params={"search_query": f"all:{q}", "max_results": min(limit, 50)})
    if r.status_code >= 400:
        raise SourceError(f"arXiv {r.status_code}")
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    out = []
    for e in ET.fromstring(r.content).findall("a:entry", ns):
        year = int((e.findtext("a:published", "", ns) or "0")[:4] or 0)
        if year_from and year and year < year_from:
            continue
        aid = (e.findtext("a:id", "", ns) or "").rsplit("/abs/", 1)[-1]
        pdf = next((ln.get("href") for ln in e.findall("a:link", ns) if ln.get("title") == "pdf"), "")
        out.append({"doi": clean_doi(e.findtext("x:doi", "", ns)), "title": _ws(e.findtext("a:title", "", ns)),
                    "authors": [_ws(a.findtext("a:name", "", ns)) for a in e.findall("a:author", ns)][:30], "year": year,
                    "venue": "arXiv", "abstract": _ws(e.findtext("a:summary", "", ns)), "url": e.findtext("a:id", "", ns),
                    "oa_url": pdf, "citations": 0, "ids": {"arxiv": aid}, "via": "arxiv"})
    return out


def pubmed(q: str, year_from: int = 0, limit: int = 20, email: str = "") -> list[dict]:
    term = q + (f" AND {year_from}:3000[dp]" if year_from else "")
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    with _client(email) as c:
        r = c.get(f"{base}/esearch.fcgi", params={"db": "pubmed", "term": term, "retmode": "json", "retmax": min(limit, 50),
                                                  "tool": "hoola", "email": email or ""})
        if r.status_code >= 400:
            raise SourceError(f"PubMed {r.status_code}")
        ids = (r.json().get("esearchresult") or {}).get("idlist") or []
        if not ids:
            return []
        s = c.get(f"{base}/esummary.fcgi", params={"db": "pubmed", "id": ",".join(ids), "retmode": "json", "tool": "hoola"})
    res = s.json().get("result") or {}
    out = []
    for uid in res.get("uids") or ids:
        it = res.get(uid) or {}
        doi = next((a.get("value") for a in it.get("articleids") or [] if a.get("idtype") == "doi"), "")
        out.append({"doi": clean_doi(doi), "title": _ws(it.get("title")), "authors": [a.get("name", "") for a in it.get("authors") or []][:30],
                    "year": _year(it.get("pubdate")),
                    "venue": _ws(it.get("fulljournalname") or it.get("source")), "abstract": "",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/", "oa_url": "", "citations": 0, "ids": {"pmid": uid},
                    "via": "pubmed"})
    return out


def semantic_scholar(q: str, year_from: int = 0, limit: int = 20, email: str = "", key: str = "") -> list[dict]:
    params: dict[str, Any] = {"query": q, "limit": min(limit, 50),
                              "fields": "title,year,authors,venue,abstract,externalIds,citationCount,openAccessPdf,url"}
    if year_from:
        params["year"] = f"{year_from}-"
    with _client(email) as c:
        r = c.get("https://api.semanticscholar.org/graph/v1/paper/search", params=params,
                  headers={"x-api-key": key} if key else None)
    if r.status_code == 429:
        raise SourceError("Semantic Scholar is busy right now (rate limit); try again in a while or with your own API key")
    if r.status_code >= 400:
        raise SourceError(f"Semantic Scholar {r.status_code}")
    out = []
    for p in r.json().get("data") or []:
        ext = p.get("externalIds") or {}
        out.append({"doi": clean_doi(ext.get("DOI")), "title": _ws(p.get("title")),
                    "authors": [a.get("name", "") for a in p.get("authors") or []][:30], "year": int(p.get("year") or 0),
                    "venue": _ws(p.get("venue")), "abstract": _ws(p.get("abstract")), "url": p.get("url") or "",
                    "oa_url": (p.get("openAccessPdf") or {}).get("url") or "", "citations": int(p.get("citationCount") or 0),
                    "ids": {"s2": p.get("paperId") or "", "arxiv": ext.get("ArXiv") or "", "pmid": ext.get("PubMed") or ""},
                    "via": "semantic_scholar"})
    return out


def unpaywall(doi: str, email: str) -> str:
    """A legal free full-text link for a DOI (Unpaywall needs a contact email), or ''."""
    d = clean_doi(doi)
    if not d or not email:
        return ""
    try:
        with _client(email) as c:
            r = c.get(f"https://api.unpaywall.org/v2/{d}", params={"email": email})
        if r.status_code >= 400:
            return ""
        best = r.json().get("best_oa_location") or {}
        return best.get("url_for_pdf") or best.get("url") or ""
    except Exception as e:
        log.info("unpaywall: %s", e)
        return ""


def search(q: str, sources: list[str] | None = None, year_from: int = 0, limit: int = 20, email: str = "",
           s2_key: str = "") -> tuple[list[dict], dict[str, str]]:
    """Every chosen source; one failing source never stops the others (its error is reported)."""
    fns = {"openalex": openalex, "crossref": crossref, "arxiv": arxiv, "pubmed": pubmed, "semantic_scholar": semantic_scholar}
    got, errors = [], {}
    for name in sources or ("openalex", "crossref", "arxiv"):
        if name not in fns:
            errors[name] = "unknown source"
            continue
        try:
            kw = {"key": s2_key} if name == "semantic_scholar" else {}
            got += fns[name](q, year_from, limit, email, **kw)
        except Exception as e:
            errors[name] = str(e)[:160]
    return got, errors
