"""Pack registry: loads every manifest under app/packs/manifests and answers "which packs can do this?"."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

MANIFEST_DIR = Path(__file__).parent / "manifests"
EXECUTORS = {"mcp", "bbps", "upi", "ride", "shop", "native", "pc", "handoff", "reader", "device", "commerce", "browser", "pcop", "mail", "cal", "sheets", "drive", "forms", "slides", "photos", "notebook", "youtube", "appcheck", "indiamart", "composio"}
LAYERS = {"L0", "L1", "L2", "L3", "L4"}


class PackTool(BaseModel):
    name: str
    tier: int = Field(ge=0, le=3)


class Pack(BaseModel):
    id: str
    name: str
    category: str
    sub_category: str
    pack_type: str
    layer: str
    phase: str
    priority: str
    description: str
    notes: str = ""
    master_list_row: int
    executor: str
    config: dict[str, Any]
    tools: list[PackTool]
    keywords: list[str]
    wave: str = "MVP"

    def tier_of(self, tool: str) -> int:
        for t in self.tools:
            if t.name == tool:
                return t.tier
        if self.executor == "mcp" and self.config.get("custom"):
            # v0.145 Supabase in read_only mode runs SQL as a read-only Postgres user, so execute_sql is a read there
            if tool == "execute_sql" and "mcp.supabase.com" in str(self.config.get("endpoint", "")) \
                    and "read_only=true" in str(self.config.get("endpoint", "")):
                return 0
            # v0.148 tools the featured server documents as output-only (21st.dev Magic) run like reads, unless she
            # switched "pehle poochho" on for that tool; never on a caution server
            if tool in (self.config.get("reads") or ()) and not self.config.get("caution"):
                try:
                    from ...mcp_prefs import _load, locked
                    if locked(tool, False):
                        return 2
                    p = _load(self.config.get("owner", ""), self.id).get(tool)
                    return 2 if (p is not None and p[1]) else 0
                except Exception:
                    return 0
            # servers the user added: anything not plainly a read needs a tap; v0.91 her per-tool "ask first" switch
            try:
                from ...mcp_prefs import needs_tap
                return 2 if needs_tap(self.config.get("owner", ""), self.id, tool, bool(self.config.get("caution"))) else 0
            except Exception:
                return 0 if is_read_only(tool) else 2
        if self.executor == "mcp":  # remote tools: classify by name; when in doubt it needs a tap
            low = tool.lower()
            words = set(re.split(r"[^a-z0-9]+", low))
            money_words = {"place", "checkout", "confirm", "pay", "payment", "book", "booking", "reserve", "reservation",
                           "purchase", "buy", "submit", "order", "cancel"}
            pats = self.config.get("money_tool_patterns", [])
            read_only = words & {"get", "list", "search", "fetch", "view", "show", "track", "status", "history", "details"}
            if (words & money_words or any(p in low for p in pats)) and not (read_only and low.split("_")[0] in
                                                                              {"get", "list", "search", "fetch", "view", "show", "track", "check"}):
                return 2
            return 0
        raise KeyError(f"{self.id} has no tool {tool}")

    def public(self) -> dict[str, Any]:
        return self.model_dump(exclude={"master_list_row"})


READ_VERBS = {"get", "list", "search", "find", "fetch", "read", "view", "show", "describe", "query", "lookup", "look",
              "check", "track", "status", "history", "details", "info", "count", "summarize", "summary", "explain",
              "validate", "preview", "browse", "download", "export", "calculate", "convert", "compare", "analyze",
              "analyse", "inspect", "resolve", "geocode", "translate", "retrieve", "scan", "stats", "report", "quote"}


# v0.143 exact names of reads whose first word isn't a verb (GitHub's official MCP merges reads into one tool each:
# issue_read / pull_request_read take a method like get / get_comments / get_diff, all reads)
READ_NAMES = {"issue_read", "pull_request_read", "actions_get", "actions_list", "projects_get", "projects_list",
              "discussion_read", "gist_read", "label_read", "generate_typescript_types"}


def is_read_only(tool: str) -> bool:
    """First word of a tool name (snake, kebab or camelCase) is a plain read verb, or a known read name."""
    if tool in READ_NAMES:
        return True
    first = re.split(r"[^a-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", tool).lower().strip("_- "))[0]
    return first in READ_VERBS


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


# extra pack sources (e.g. MCP servers a user added); each returns a Pack or None
_resolvers: list = []


def add_resolver(fn) -> None:
    if fn not in _resolvers:
        _resolvers.append(fn)


class Registry:
    def __init__(self, packs: list[Pack]):
        self.packs = {p.id: p for p in packs}

    def lookup(self, pack_id: str) -> Pack | None:
        p = self.packs.get(pack_id)
        if p is None:
            for fn in _resolvers:
                p = fn(pack_id)
                if p is not None:
                    break
        return p

    def get(self, pack_id: str) -> Pack:
        p = self.lookup(pack_id)
        if p is None:
            raise KeyError(pack_id)
        return p

    def all(self, phase: str | None = None, category: str | None = None, wave: str | None = None) -> list[Pack]:
        out = list(self.packs.values())
        if wave:
            out = [p for p in out if p.wave == wave]
        if phase:
            out = [p for p in out if p.phase == phase]
        if category:
            out = [p for p in out if p.category == category]
        return sorted(out, key=lambda p: (p.priority, p.category, p.name))

    def by_executor(self, executor: str) -> list[Pack]:
        return [p for p in self.packs.values() if p.executor == executor]

    def match(self, text: str, limit: int = 5, only: set[str] | None = None) -> list[tuple[Pack, int]]:
        """Keyword score: used by the offline planner and to shortlist packs before calling Claude."""
        t = _norm(text)
        scored: list[tuple[Pack, int]] = []
        for p in self.packs.values():
            if only is not None and p.id not in only:
                continue
            score = 0
            for kw in p.keywords:
                k = _norm(kw)
                if k and re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", t):
                    score += 3 if " " in k else 2
            nm = _norm(p.name.split(" (")[0])
            if nm and re.search(r"(?<![a-z0-9])" + re.escape(nm) + r"(?![a-z0-9])", t):  # "akola" is not "Ola"
                score += 5
            if score:
                scored.append((p, score))
        scored.sort(key=lambda x: (-x[1], x[0].priority, x[0].name))
        return scored[:limit]


def load_manifests(directory: Path = MANIFEST_DIR) -> list[Pack]:
    packs = []
    for f in sorted(directory.glob("*.json")):
        data = json.loads(f.read_text())
        p = Pack(**data)
        if p.executor not in EXECUTORS:
            raise ValueError(f"{f.name}: unknown executor {p.executor}")
        if p.layer not in LAYERS:
            raise ValueError(f"{f.name}: unknown layer {p.layer}")
        packs.append(p)
    return packs


@lru_cache
def registry() -> Registry:
    return Registry(load_manifests())
