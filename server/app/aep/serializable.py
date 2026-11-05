"""HOOLA AEP serializable - the load/serialization seed (the langchain-core
`load/serializable.py` idea, hand-built for the house; upstream reference read at
github.com/langchain-ai/langchain @ aa2528fb, libs/core/langchain_core/load/serializable.py).

v0.510.0 HOOLA CORE (P1 of the AEP plan): every aep object can declare an immutable
class id and dump itself to a plain dict shaped like langchain's `to_json()`
({"lc": 1, "type": "constructor", "id": [...], "kwargs": {...}}). P7 (HOOLA HUB) builds
the full from-dict loader on this seed; nothing here executes, touches the network or
reads config - the package is inert until called (the P1 kill-switch note in the story).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class Serializable(BaseModel):
    """Base for aep objects that serialize to a langchain-shaped constructor dict.

    Subclasses get a stable `lc_id()` (the tuple path a loader would import) and
    `to_json()` / `to_repr()`. Instantiation kwargs are captured so a round trip
    through P7's loader can rebuild the object.
    """

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    lc_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        exclude=True,
        description="The kwargs the object was actually built with (for rebuilding).",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # First-construction kwargs win; later mutations do not pollute the record.
        if not self.lc_kwargs:
            object.__setattr__(self, "lc_kwargs", dict(kwargs))

    @classmethod
    def lc_id(cls) -> tuple[str, ...]:
        """The import path a from-dict loader would use (house path, not upstream's)."""
        return ("aep", cls.__module__.rsplit(".", 1)[-1], cls.__name__)

    def to_json(self) -> dict[str, Any]:
        """The langchain-shaped serialization dict (upstream load/serializable.py)."""
        kwargs = dict(self.lc_kwargs) if self.lc_kwargs else {}
        if not kwargs:
            kwargs = {
                k: v for k, v in self.model_dump(exclude={"lc_kwargs"}).items()
                if k in type(self).model_fields
            }
        return {
            "lc": 1,
            "type": "constructor",
            "id": list(self.lc_id()),
            "kwargs": kwargs,
        }

    def to_repr(self) -> str:
        return f"{type(self).__name__}({self.to_json()['kwargs']!r})"

    # Private attrs survive model_copy and never serialize.
    _private: dict[str, Any] = PrivateAttr(default_factory=dict)
