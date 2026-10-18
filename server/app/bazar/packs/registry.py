"""Pack registry: loads every manifest under app/packs/manifests and answers "which packs can do this?"."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

MANIFEST_DIR = Path(__file__).parent / "manifests"
EXECUTORS = {"mcp", "bbps", "upi", "ride", "shop", "native"}
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

    def tier_of(self, tool: str) -> int:
        for t in self.tools:
            if t.name == tool:
                return t.tier
        if self.executor == "mcp":  # remote tools: classify by name; when in doubt it needs a tap
            low = tool.lower()
            words = set(re.split(r"[^a-z0-9]+", low))
            money_words = {"place", "checkout", "confirm", "pay", "payment", "book", "booking", "reserve", "reservation",
                           "purchase", "buy", "submit", "order", "cancel"}
            pats = self.config.get("money_tool_patterns", [])
            read_only = words & {"get", "list", "search", "fetch", "view", "show", "track", "status", "history", "details"}
            if (words & money_words or any(p in low for p in pats)) and not (read_only and low.split("_")[0] in
                                                                              {"get", "list", "search", "fetch", "view", "show", "track"}):
                return 2
            return 0
        raise KeyError(f"{self.id} has no tool {tool}")

    def public(self) -> dict[str, Any]:
        return self.model_dump(exclude={"master_list_row"})


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


class Registry:
    def __init__(self, packs: list[Pack]):
        self.packs = {p.id: p for p in packs}

    def get(self, pack_id: str) -> Pack:
        return self.packs[pack_id]

    def all(self, phase: str | None = None, category: str | None = None) -> list[Pack]:
        out = list(self.packs.values())
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
            if _norm(p.name.split(" (")[0]) in t:
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
