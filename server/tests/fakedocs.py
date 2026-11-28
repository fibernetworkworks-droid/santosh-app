"""A small Google Docs engine for tests: it keeps a document as Google does (indexes in UTF-16 code units, a section
break at 0, every paragraph ending in a newline, tables made of table / row / cell markers) and answers the Docs API
the way Google's reference says, refusing what Google refuses (inserting outside a paragraph, deleting a table's
markers, a stale requiredRevisionId, unknown fields). Not a copy of Google - enough to prove Hoola's place math."""
from __future__ import annotations

import copy
import json
import re

import httpx


def u16(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


class Tok:
    __slots__ = ("k", "ch", "st", "ps", "sug", "obj", "dele", "sugst")

    def __init__(self, k, ch="", st=None, ps=None, sug=None, obj=None):
        self.k, self.ch, self.st, self.ps, self.sug, self.obj = k, ch, dict(st or {}), ps, sug, obj
        self.dele, self.sugst = None, {}

    @property
    def size(self):
        return u16(self.ch) if self.k == "c" else 1


class Seg:
    def __init__(self, text="\n"):
        self.toks: list[Tok] = []
        for line in text.split("\n")[:-1] if text.endswith("\n") else text.split("\n"):
            for ch in line:
                self.toks.append(Tok("c", ch))
            self.toks.append(Tok("c", "\n", ps={"namedStyleType": "NORMAL_TEXT"}))
        if not self.toks:
            self.toks.append(Tok("c", "\n", ps={"namedStyleType": "NORMAL_TEXT"}))


class FakeDocs:
    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.calls: list[dict] = []
        self.busy = 0

    # ---------------------------------------------------------------- set-up
    def add(self, did: str, title: str, text: str = "\n", tabs: list[tuple[str, str]] | None = None):
        tabs = tabs or [("t.0", title)]
        self.docs[did] = {"title": title, "rev": 1, "tabs": [], "comments": [], "suggestions": []}
        for k, (tid, ttl) in enumerate(tabs):
            self.docs[did]["tabs"].append(self._newtab(tid, ttl, k, text if k == 0 else "\n"))
        return self.docs[did]

    def _newtab(self, tid, title, index, text="\n", parent=""):
        return {"id": tid, "title": title, "index": index, "emoji": "", "parent": parent, "body": Seg(text),
                "headers": {}, "footers": {}, "footnotes": {}, "style": {}, "named": {}, "ddefs": {}, "nstyles": {}}

    # ---------------------------------------------------------------- index helpers
    @staticmethod
    def _pos(seg: Seg, index: int, base: int = 1):
        """token position whose start index == index (base: the first token's index)."""
        i = base
        for k, t in enumerate(seg.toks):
            if i == index:
                return k
            i += t.size
            if i > index:
                raise ValueError(f"index {index} is inside a character")
        if i == index:
            return len(seg.toks)
        raise ValueError(f"index {index} is past the end")

    def _bad(self, msg):
        return httpx.Response(400, json={"error": {"code": 400, "message": msg, "status": "INVALID_ARGUMENT"}})

    def _tab(self, d, tid):
        if not tid:
            return d["tabs"][0]
        for t in d["tabs"]:
            if t["id"] == tid:
                return t
        raise KeyError(tid)

    def _seg(self, tab, loc):
        sid = (loc or {}).get("segmentId", "")
        if not sid:
            return tab["body"], 1
        for kind in ("headers", "footers", "footnotes"):
            if sid in tab[kind]:
                return tab[kind][sid], 0
        raise KeyError(sid)

    # ---------------------------------------------------------------- reading
    def _content(self, seg: Seg, base: int, d: dict, tab: dict) -> list[dict]:
        out = []
        if base == 1:
            out.append({"startIndex": 0, "endIndex": 1, "sectionBreak": {"sectionStyle": {}}})
        i = base
        stack: list = []        # table being read: [table dict, row, cell, cell content]
        para: list = []
        pstart = i
        for t in seg.toks:
            if t.k == "ts":
                tbl = {"startIndex": i, "table": {"rows": 0, "columns": 0, "tableRows": []}}
                stack.append([tbl, None, None])
                i += 1
                continue
            if t.k == "rs":
                tb = stack[-1][0]
                row = {"startIndex": i, "tableCells": []}
                tb["table"]["tableRows"].append(row)
                stack[-1][1] = row
                i += 1
                continue
            if t.k == "cs":
                cell = {"startIndex": i, "content": []}
                stack[-1][1]["tableCells"].append(cell)
                stack[-1][2] = cell
                i += 1
                pstart = i
                continue
            if t.k == "sb":
                out.append({"startIndex": i, "endIndex": i + 1, "sectionBreak": {"sectionStyle": dict(t.obj or {})}})
                i += 1
                continue
            if t.k == "te":
                tb = stack.pop()[0]
                i += 1
                tb["endIndex"] = i
                rows = tb["table"]["tableRows"]
                tb["table"]["rows"] = len(rows)
                tb["table"]["columns"] = max((len(r["tableCells"]) for r in rows), default=0)
                (stack[-1][2]["content"] if stack else out).append(tb)
                pstart = i
                continue
            if not para:
                pstart = i
            para.append((i, t))
            i += t.size
            if t.k == "c" and t.ch == "\n":
                el = self._para(para, d, tab)
                (stack[-1][2]["content"] if stack else out).append(el)
                para = []
        return out

    def _para(self, para, d, tab):
        start = para[0][0]
        end = para[-1][0] + para[-1][1].size
        nl = para[-1][1]
        elements, run, rst, rstart, rsug = [], "", None, None, None
        for i, t in para:
            if t.k == "c":
                key = (t.sug, t.dele, tuple(sorted(t.sugst)))
                if run and (t.st != rst or key != rsug):
                    elements.append(self._run(rstart, i, run, rst, rsug))
                    run = ""
                if not run:
                    rst, rstart, rsug = t.st, i, key
                    self._last = t
                run += t.ch
            else:
                if run:
                    elements.append(self._run(rstart, i, run, rst, rsug))
                    run = ""
                elements.append({"startIndex": i, "endIndex": i + 1, **t.obj})
        if run:
            elements.append(self._run(rstart, end, run, rst, rsug))
        p = {"elements": elements, "paragraphStyle": dict(nl.ps or {"namedStyleType": "NORMAL_TEXT"})}
        if p["paragraphStyle"].get("namedStyleType", "").startswith("HEADING_"):
            p["paragraphStyle"]["headingId"] = "h." + re.sub(r"[^a-z0-9]", "", "".join(
                t.ch for _i, t in para if t.k == "c").lower())[:10]
        if nl.ps and nl.ps.get("_bullet"):
            p["bullet"] = {"listId": "l1", "nestingLevel": nl.ps.get("_level", 0)}
            p["paragraphStyle"] = {k: v for k, v in nl.ps.items() if not k.startswith("_")}
        return {"startIndex": start, "endIndex": end, "paragraph": p}

    def _run(self, a, b, text, st, key):
        sug, dele, _ks = key if isinstance(key, tuple) else (key, None, ())
        tr = {"content": text, "textStyle": dict(st or {})}
        if sug:
            tr["suggestedInsertionIds"] = [sug]
        if dele:
            tr["suggestedDeletionIds"] = [dele]
        last = getattr(self, "_last", None)
        if last is not None and last.sugst:
            tr["suggestedTextStyleChanges"] = copy.deepcopy(last.sugst)
        return {"startIndex": a, "endIndex": a + u16(text), "textRun": tr}

    def view(self, did: str, comments: bool = False) -> dict:
        d = self.docs[did]
        tabs = []
        for t in d["tabs"]:
            dt = {"body": {"content": self._content(t["body"], 1, d, t)},
                  "headers": {k: {"headerId": k, "content": self._content(v, 0, d, t)} for k, v in t["headers"].items()},
                  "footers": {k: {"footerId": k, "content": self._content(v, 0, d, t)} for k, v in t["footers"].items()},
                  "footnotes": {k: {"footnoteId": k, "content": self._content(v, 0, d, t)} for k, v in t["footnotes"].items()},
                  "documentStyle": copy.deepcopy(t["style"]), "namedRanges": copy.deepcopy(t["named"]),
                  "dropdownDefinitions": copy.deepcopy(t["ddefs"]), "inlineObjects": {},
                  "positionedObjects": copy.deepcopy(t.setdefault("pos", {}))}
            props = {"tabId": t["id"], "title": t["title"], "index": t["index"]}
            if t["emoji"]:
                props["iconEmoji"] = t["emoji"]
            if t["parent"]:
                props["parentTabId"] = t["parent"]
            tabs.append({"tabProperties": props, "documentTab": dt})
        out = {"documentId": did, "title": d["title"], "revisionId": f"rev{d['rev']}", "tabs": tabs}
        if comments:
            out["comments"] = copy.deepcopy(d["comments"])
            out["suggestions"] = copy.deepcopy(d["suggestions"])
        return out

    def text(self, did: str, tab: int = 0) -> str:
        return "".join(t.ch if t.k == "c" else {"ts": "[T", "rs": "|R", "cs": "|", "te": "T]"}.get(t.k, "*")
                       for t in self.docs[did]["tabs"][tab]["body"].toks)

    def paras(self, did: str, tab: int = 0) -> list[tuple[str, dict]]:
        out, cur = [], ""
        for t in self.docs[did]["tabs"][tab]["body"].toks:
            if t.k == "c" and t.ch == "\n":
                out.append((cur, t.ps or {}))
                cur = ""
            elif t.k == "c":
                cur += t.ch
        return out

    # ---------------------------------------------------------------- writing
    def _insert(self, seg, base, index, toks_new, sug=None):
        k = self._pos(seg, index, base)
        if k >= len(seg.toks):
            raise ValueError("insertion past the final newline")
        prev = seg.toks[k]                       # the token now at this place = inside some paragraph
        # paragraph that holds the place: its newline gives the copied paragraph look
        j = k
        while j < len(seg.toks) and not (seg.toks[j].k == "c" and seg.toks[j].ch == "\n"):
            if seg.toks[j].k in ("ts", "rs", "cs", "te"):
                raise ValueError("Text must be inserted inside the bounds of an existing paragraph")
            j += 1
        nl_ps = dict(seg.toks[j].ps or {}) if j < len(seg.toks) else {}
        before = seg.toks[k - 1] if k > 0 and seg.toks[k - 1].k == "c" and seg.toks[k - 1].ch != "\n" else None
        st = dict(before.st) if before else (dict(prev.st) if prev.k == "c" and prev.ch != "\n" else {})
        for t in toks_new:
            if t.k == "c" and not t.st:
                t.st = dict(st)
            if t.k == "c" and t.ch == "\n" and t.ps is None:
                t.ps = dict(nl_ps)
            t.sug = sug
        seg.toks[k:k] = toks_new

    def _range(self, seg, base, a, b):
        ka, kb = self._pos(seg, a, base), self._pos(seg, b, base)
        return ka, kb

    def _paras_in(self, seg, base, a, b):
        """newline tokens of every paragraph overlapping [a, b)."""
        out, i, pstart = [], base, base
        for t in seg.toks:
            if t.k == "c" and t.ch == "\n":
                if pstart < b and i + 1 > a:
                    out.append(t)
                pstart = i + 1
            elif t.k in ("ts", "rs", "cs", "te"):
                pstart = i + 1
            i += t.size
        return out

    def apply(self, did: str, req: dict, suggest: bool) -> dict:
        d = self.docs[did]
        (kind, r), = req.items()
        sug = "suggest.s1" if suggest else None
        if suggest and kind not in ("insertText", "deleteContentRange", "updateTextStyle", "updateParagraphStyle",
                                    "replaceAllText", "createParagraphBullets", "deleteParagraphBullets",
                                    "insertTable", "insertInlineImage", "insertPageBreak"):
            raise ValueError(f"{kind} cannot be written as a suggestion")
        loc = r.get("location") or r.get("endOfSegmentLocation") or (r.get("range") or {})
        tab = self._tab(d, loc.get("tabId") or r.get("tabId", ""))
        if kind == "insertText":
            seg, base = self._seg(tab, loc)
            idx = loc.get("index") if "location" in r else self._end(seg, base)
            toks = [Tok("c", ch) for ch in r["text"] if ch not in ""]
            self._insert(seg, base, idx, toks, sug)
            if suggest and not any(x["suggestionId"] == sug and x["status"] == "OPEN" for x in d["suggestions"]):
                d["suggestions"].append({"suggestionId": sug, "status": "OPEN", "summaryText": f"Add \"{r['text'][:30]}\"",
                                         "headPost": {"author": {"displayName": "Meghana"}}})
            return {}
        if kind == "deleteContentRange" and suggest:
            seg, base = self._seg(tab, r["range"])
            ka, kb = self._range(seg, base, r["range"]["startIndex"], r["range"]["endIndex"])
            for t in seg.toks[ka:kb]:
                t.dele = "suggest.del1"
            d["suggestions"].append({"suggestionId": "suggest.del1", "status": "OPEN", "summaryText": "Delete text",
                                     "headPost": {"author": {"displayName": "Meghana"}}})
            return {}
        if kind == "updateTextStyle" and suggest:
            seg, base = self._seg(tab, r["range"])
            ka, kb = self._range(seg, base, r["range"]["startIndex"], r["range"]["endIndex"])
            state = {f + "Suggested": True for f in r["fields"].split(",")}
            old_text = [t for t in seg.toks[ka:kb] if t.k == "c" and not t.sug]
            for t in seg.toks[ka:kb]:
                if t.k != "c":
                    continue
                if t.sug:              # text that is itself a suggested insertion takes the look directly
                    for f in r["fields"].split(","):
                        if f in r["textStyle"]:
                            t.st[f] = r["textStyle"][f]
                        else:
                            t.st.pop(f, None)
                else:
                    t.sugst["suggest.look1"] = {"textStyle": dict(r["textStyle"]), "textStyleSuggestionState": state}
            if old_text and not any(x["suggestionId"] == "suggest.look1" for x in d["suggestions"]):
                d["suggestions"].append({"suggestionId": "suggest.look1", "status": "OPEN", "summaryText": "Format text",
                                         "headPost": {"author": {"displayName": "Meghana"}}})
            return {}
        if kind == "deleteContentRange":
            seg, base = self._seg(tab, r["range"])
            ka, kb = self._range(seg, base, r["range"]["startIndex"], r["range"]["endIndex"])
            cut = seg.toks[ka:kb]
            if any(t.k in ("ts", "rs", "cs", "te") for t in cut) and not (cut and cut[0].k == "ts" and cut[-1].k == "te"):
                raise ValueError("Invalid deletion range: cannot delete part of a table")
            if kb >= len(seg.toks):
                raise ValueError("cannot delete the last newline of the segment")
            del seg.toks[ka:kb]
            return {}
        if kind == "updateTextStyle":
            seg, base = self._seg(tab, r["range"])
            ka, kb = self._range(seg, base, r["range"]["startIndex"], r["range"]["endIndex"])
            fields = r["fields"].split(",")
            for t in seg.toks[ka:kb]:
                if t.k == "c" and t.ch != "\n":
                    for f in fields:
                        if f in r["textStyle"]:
                            t.st[f] = r["textStyle"][f]
                        else:
                            t.st.pop(f, None)
            return {}
        if kind == "updateParagraphStyle":
            seg, base = self._seg(tab, r["range"])
            for nl in self._paras_in(seg, base, r["range"]["startIndex"], r["range"]["endIndex"]):
                nl.ps = nl.ps or {}
                for f in r["fields"].split(","):
                    if f in r["paragraphStyle"]:
                        nl.ps[f] = r["paragraphStyle"][f]
                    else:
                        nl.ps.pop(f, None)
            return {}
        if kind in ("createParagraphBullets", "deleteParagraphBullets"):
            seg, base = self._seg(tab, r["range"])
            nls = self._paras_in(seg, base, r["range"]["startIndex"], r["range"]["endIndex"])
            for nl in nls:
                nl.ps = nl.ps or {}
                if kind == "deleteParagraphBullets":
                    nl.ps.pop("_bullet", None)
                    continue
                k = seg.toks.index(nl)
                j = k
                while j > 0 and not (seg.toks[j - 1].k == "c" and seg.toks[j - 1].ch == "\n") and seg.toks[j - 1].k == "c":
                    j -= 1
                lvl = 0
                while seg.toks[j].k == "c" and seg.toks[j].ch == "\t":
                    del seg.toks[j]
                    lvl += 1
                nl.ps["_bullet"] = r["bulletPreset"]
                nl.ps["_level"] = lvl
            return {}
        if kind == "insertTable":
            seg, base = self._seg(tab, loc)
            idx = loc.get("index") if "location" in r else self._end(seg, base)
            toks = [Tok("c", "\n"), Tok("ts")]
            for _ in range(r["rows"]):
                toks.append(Tok("rs"))
                for _ in range(r["columns"]):
                    toks += [Tok("cs"), Tok("c", "\n", ps={"namedStyleType": "NORMAL_TEXT"})]
            toks.append(Tok("te"))
            self._insert(seg, base, idx, toks, sug)
            return {}
        if kind == "insertInlineImage":
            assert r["uri"].startswith("https://")
            seg, base = self._seg(tab, loc)
            idx = loc.get("index") if "location" in r else self._end(seg, base)
            self._insert(seg, base, idx, [Tok("o", obj={"inlineObjectElement": {"inlineObjectId": "kix.img1"}})], sug)
            return {"insertInlineImage": {"objectId": "kix.img1"}}
        if kind == "insertPageBreak":
            seg, base = self._seg(tab, loc)
            idx = loc.get("index") if "location" in r else self._end(seg, base)
            self._insert(seg, base, idx, [Tok("o", obj={"pageBreak": {}}), Tok("c", "\n")], sug)
            return {}
        if kind == "replaceAllText":
            want = r["containsText"]["text"]
            n = 0
            for t in d["tabs"]:
                if r.get("tabsCriteria") and t["id"] not in r["tabsCriteria"]["tabIds"]:
                    continue
                for seg in [t["body"], *t["headers"].values(), *t["footers"].values()]:
                    s = "".join(x.ch if x.k == "c" else "\x00" for x in seg.toks)
                    flags = 0 if r["containsText"].get("matchCase") else re.I
                    pat = want if r["containsText"].get("searchByRegex") else re.escape(want)
                    for m in reversed(list(re.finditer(pat, s, flags))):
                        st = dict(seg.toks[m.start()].st)
                        seg.toks[m.start():m.end()] = [Tok("c", ch, st=st, sug=sug) for ch in r["replaceText"]]
                        n += 1
            return {"replaceAllText": {"occurrencesChanged": n}}
        if kind == "insertComment":
            cid = f"c{len(d['comments']) + 1}"
            seg, base = self._seg(tab, r["range"])
            ka, kb = self._range(seg, base, r["range"]["startIndex"], r["range"]["endIndex"])
            q = "".join(t.ch for t in seg.toks[ka:kb] if t.k == "c")
            d["comments"].append({"commentId": cid, "status": "OPEN", "plainTextQuote": q,
                                  "headPost": {"postId": "p1", "content": r["content"],
                                               "assigneeEmail": r.get("assigneeEmailAddress", ""),
                                               "author": {"displayName": "Meghana"}}, "replies": []})
            return {"insertComment": {"commentId": cid}}
        if kind == "addCommentReply":
            th = next(x for x in d["comments"] if x["commentId"] == r.get("commentId"))
            post = r["post"]
            if post.get("commentAction") == "RESOLVE":
                th["status"] = "RESOLVED"
            elif post.get("commentAction") == "REOPEN":
                th["status"] = "OPEN"
            else:
                assert post.get("content"), "a reply needs content"
            th["replies"].append({"postId": f"p{len(th['replies']) + 2}", "content": post.get("content", ""),
                                  "author": {"displayName": "Meghana"}})
            return {}
        if kind in ("acceptSuggestion", "rejectSuggestion"):
            sg = next(x for x in d["suggestions"] if x["suggestionId"] == r["suggestionId"])
            sg["status"] = "ACCEPTED" if kind == "acceptSuggestion" else "REJECTED"
            for t in d["tabs"]:
                keep = []
                for x in t["body"].toks:
                    if x.sug == r["suggestionId"]:
                        if kind == "rejectSuggestion":
                            continue
                        x.sug = None
                    keep.append(x)
                t["body"].toks = keep
            return {}
        if kind == "insertSectionBreak":
            seg, base = self._seg(tab, loc)
            idx = loc.get("index")
            self._insert(seg, base, idx, [Tok("c", "\n"), Tok("sb", obj={"sectionType": r["sectionType"]})])
            return {}
        if kind == "updateSectionStyle":
            seg, base = self._seg(tab, r["range"])
            i, cur = base, None
            for t in seg.toks:                     # the section break before the range's start
                if t.k == "sb" and i < r["range"]["startIndex"]:
                    cur = t
                i += t.size
            target = cur.obj if cur is not None else tab["style"].setdefault("_first_section", {})
            for f in r["fields"].split(","):
                target[f] = r["sectionStyle"][f]
            self.calls.append({kind: r})
            return {}
        if kind == "deleteSuggestion":
            sg = next(x for x in d["suggestions"] if x["suggestionId"] == r["suggestionId"])
            sg["status"] = "REJECTED"
            for t in d["tabs"]:
                t["body"].toks = [x for x in t["body"].toks if x.sug != r["suggestionId"]]
            return {}
        if kind == "deleteCommentReply":
            th = next(x for x in d["comments"] if x["commentId"] == r.get("commentId"))
            th["replies"] = [x for x in th["replies"] if x["postId"] != r["postId"]]
            return {}
        if kind == "updateCommentPost":
            th = next(x for x in d["comments"] if x["commentId"] == r.get("commentId"))
            post = th["headPost"] if th["headPost"]["postId"] == r["postId"] else next(
                x for x in th["replies"] if x["postId"] == r["postId"])
            post["content"] = r["content"]
            return {}
        if kind == "updateDropdownDefinitionProperties":
            dd = tab["ddefs"][r["dropdownDefinitionId"]]
            for f in r["fields"].split(","):
                dd["dropdownDefinitionProperties"][f] = r["dropdownDefinitionProperties"][f]
            ids = {o["optionId"] for o in dd["dropdownDefinitionProperties"]["options"]}
            for k_, v_ in (r.get("selectedOptionIdReplacements") or {}).items():
                assert v_ in ids, "a replacement must be a remaining option"
            return {}
        if kind == "deleteDropdownDefinition":
            for t in tab["body"].toks:
                if t.k == "o" and (t.obj.get("dropdown") or {}).get("dropdownProperties", {}).get(
                        "dropdownDefinitionId") == r["dropdownDefinitionId"]:
                    raise ValueError("the dropdown definition is still used by a chip")
            del tab["ddefs"][r["dropdownDefinitionId"]]
            return {}
        if kind == "deleteNamedRange":
            assert r["name"] in tab["named"], "no such named range"
            del tab["named"][r["name"]]
            return {}
        if kind == "deletePositionedObject":
            del tab["pos"][r["objectId"]]
            return {}
        if kind == "deleteComment":
            d["comments"] = [x for x in d["comments"] if x["commentId"] != r["commentId"]]
            return {}
        if kind == "updateDocumentStyle":
            for f in r["fields"].split(","):
                if f in ("firstPageHeaderId", "evenPageHeaderId", "firstPageFooterId", "evenPageFooterId",
                         "defaultHeaderId", "defaultFooterId"):
                    raise ValueError(f"{f} is read-only")
                tab["style"][f] = r["documentStyle"][f]
            return {}
        if kind in ("createHeader", "createFooter"):
            part = "headers" if kind == "createHeader" else "footers"
            hid = f"kix.{part[:-1]}{len(tab[part]) + 1}"
            key = "defaultHeaderId" if part == "headers" else "defaultFooterId"
            if tab["style"].get(key):
                raise ValueError("A header of the specified type already exists")
            tab[part][hid] = Seg("\n")
            tab["style"][key] = hid
            return {kind: {("headerId" if part == "headers" else "footerId"): hid}}
        if kind == "createFootnote":
            seg, base = self._seg(tab, loc)
            idx = loc.get("index") if "location" in r else self._end(seg, base)
            fid = f"kix.fn{len(tab['footnotes']) + 1}"
            self._insert(seg, base, idx, [Tok("o", obj={"footnoteReference": {"footnoteId": fid,
                                                                             "footnoteNumber": str(len(tab['footnotes']) + 1)}})])
            tab["footnotes"][fid] = Seg(" \n")
            return {"createFootnote": {"footnoteId": fid}}
        if kind == "addDocumentTab":
            p = r["tabProperties"]
            tid = f"t.{len(d['tabs'])}"
            d["tabs"].append(self._newtab(tid, p.get("title", ""), len(d["tabs"]), "\n", p.get("parentTabId", "")))
            d["tabs"][-1]["emoji"] = p.get("iconEmoji", "")
            return {"addDocumentTab": {"tabProperties": {"tabId": tid, "title": p.get("title", "")}}}
        if kind == "updateDocumentTabProperties":
            t = self._tab(d, r["tabProperties"]["tabId"])
            for f in r["fields"].split(","):
                t[{"title": "title", "iconEmoji": "emoji", "index": "index", "parentTabId": "parent"}[f]] = r["tabProperties"][f]
            return {}
        if kind == "deleteTab":
            d["tabs"] = [t for t in d["tabs"] if t["id"] != r["tabId"] and t["parent"] != r["tabId"]]
            return {}
        if kind in ("insertPerson", "insertDate", "insertRichLink", "insertDropdown"):
            seg, base = self._seg(tab, loc)
            idx = loc.get("index") if "location" in r else self._end(seg, base)
            obj = {"insertPerson": lambda: {"person": {"personProperties": r["personProperties"]}},
                   "insertDate": lambda: {"dateElement": {"dateElementProperties": {**r["dateElementProperties"],
                                                                                    "displayText": "Dec 1, 2026"}}},
                   "insertRichLink": lambda: {"richLink": {"richLinkProperties": {**r["richLinkProperties"], "title": "Budget"}}},
                   "insertDropdown": lambda: {"dropdown": {"dropdownId": f"kix.dd{len(self.calls)}", "dropdownProperties": {
                       "dropdownDefinitionId": r["dropdownDefinitionId"], "selectedOptionId": r.get("selectedOptionId", ""),
                       "displayValue": "x"}}}}[kind]()
            if kind == "insertDropdown":
                assert r["dropdownDefinitionId"] in tab["ddefs"], "define the dropdown first"
            self._insert(seg, base, idx, [Tok("o", obj=obj)], sug)
            return {}
        if kind == "createDropdownDefinition":
            dd = r["dropdownDefinition"]
            assert re.fullmatch(r"kix\.[a-zA-Z0-9_-]{2,14}", dd["dropdownDefinitionId"]), dd["dropdownDefinitionId"]
            opts = dd["dropdownDefinitionProperties"]["options"]
            assert 2 <= len(opts) <= 50
            for o in opts:
                assert o["optionId"].startswith("dropdownItem.")
            tab["ddefs"][dd["dropdownDefinitionId"]] = dd
            return {}
        if kind == "createNamedRange":
            tab["named"].setdefault(r["name"], {"name": r["name"], "namedRanges": []})["namedRanges"].append(
                {"namedRangeId": f"kix.nr{len(tab['named'])}", "ranges": [r["range"]]})
            return {"createNamedRange": {"namedRangeId": "kix.nr"}}
        if kind in ("insertTableRow", "insertTableColumn", "deleteTableRow", "deleteTableColumn", "mergeTableCells",
                    "unmergeTableCells", "updateTableCellStyle", "updateTableColumnProperties", "pinTableHeaderRows",
                    "updateNamedStyle", "replaceImage", "replaceNamedRangeContent", "updateTableRowStyle",
                    "updateDropdownProperties", "deleteHeader", "deleteFooter"):
            self.calls.append({kind: r})       # recorded; their shape is checked by the test
            if kind == "insertTableRow":
                self._table_row(tab, r)
            return {}
        raise ValueError(f"fake does not know {kind}")

    def _table_row(self, tab, r):
        seg = tab["body"]
        start = r["tableCellLocation"]["tableStartLocation"]["index"]
        k = self._pos(seg, start, 1)
        assert seg.toks[k].k == "ts", "tableStartLocation must be the table's start"
        rows, j = [], k + 1
        while seg.toks[j].k != "te":
            if seg.toks[j].k == "rs":
                rows.append(j)
            j += 1
        ri = r["tableCellLocation"]["rowIndex"]
        cols = sum(1 for x in seg.toks[rows[0]:rows[1] if len(rows) > 1 else j] if x.k == "cs")
        at = (rows[ri + 1] if ri + 1 < len(rows) else j) if r.get("insertBelow") else rows[ri]
        new = [Tok("rs")]
        for _ in range(cols):
            new += [Tok("cs"), Tok("c", "\n", ps={"namedStyleType": "NORMAL_TEXT"})]
        seg.toks[at:at] = new

    @staticmethod
    def _end(seg, base):
        i = base
        for t in seg.toks[:-1]:
            i += t.size
        return i

    # ---------------------------------------------------------------- HTTP
    def __call__(self, req: httpx.Request) -> httpx.Response:
        u = req.url
        if self.busy:
            self.busy -= 1
            return httpx.Response(429, json={"error": {"message": "Quota exceeded for quota metric 'Write requests'"}})
        m = re.fullmatch(r"/v1/documents(?:/([^/:]+))?(:batchUpdate)?", u.path)
        assert m, u.path
        did = m.group(1)
        if req.method == "POST" and not did:
            body = json.loads(req.content)
            nid = f"newdoc{len(self.docs) + 1}"
            self.add(nid, body.get("title", "Untitled document"))
            return httpx.Response(200, json={"documentId": nid, "title": body.get("title")})
        if did not in self.docs:
            return httpx.Response(404, json={"error": {"message": "Requested entity was not found."}})
        if req.method == "GET":
            p = u.params
            assert p.get("includeTabsContent") == "true"
            com = p.get("commentsViewMode") == "COMMENTS_VIEW_MODE_INCLUDED"
            if com:
                assert p.get("suggestionsViewMode") == "SUGGESTIONS_INLINE", "Google: comments need SUGGESTIONS_INLINE"
            return httpx.Response(200, json=self.view(did, com))
        body = json.loads(req.content)
        wc = body.get("writeControl") or {}
        d = self.docs[did]
        if wc.get("requiredRevisionId") and wc["requiredRevisionId"] != f"rev{d['rev']}":
            return self._bad("The required revision ID does not match the latest revision of the document.")
        snapshot = copy.deepcopy(d)
        replies = []
        try:
            for r in body["requests"]:
                self.calls.append(r)
                replies.append(self.apply(did, r, wc.get("writeMode") == "SUGGEST"))
        except (ValueError, KeyError, AssertionError, StopIteration) as e:
            self.docs[did] = snapshot                  # Google applies all or nothing
            return self._bad(f"Invalid requests: {e}")
        d = self.docs[did]
        d["rev"] += 1
        return httpx.Response(200, json={"documentId": did, "replies": replies,
                                         "writeControl": {"requiredRevisionId": f"rev{d['rev']}"}})
