"""HOOLA AEP stores - the key-value memory contract, the langchain-core
`stores.py` idea hand-built (upstream reference: stores.py:26 BaseStore,
:244 InMemoryStore, :267 InMemoryByteStore).

v0.510.0 HOOLA CORE: namespaced tuple keys, mget/mset/mdelete, prefix search via
yield_keys. The store is the slot the graph engine (P3) hands agents for
cross-thread memory (upstream InjectedStore) and what a SQL-backed store (P6)
will implement against the house engine. Inert.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator, Sequence


class InvalidKeyException(Exception):
    """Raised when a key is not a tuple of str (upstream stores.py:290)."""


def _check_key(key: Any) -> tuple[str, ...]:
    if not isinstance(key, tuple) or not all(isinstance(p, str) for p in key):
        raise InvalidKeyException(f"Store keys must be tuples of str, got: {key!r}")
    return key


class BaseStore(ABC):
    @abstractmethod
    def mget(self, keys: Sequence[tuple[str, ...]]) -> list[Any | None]: ...

    @abstractmethod
    def mset(self, pairs: Sequence[tuple[tuple[str, ...], Any]]) -> None: ...

    @abstractmethod
    def mdelete(self, keys: Sequence[tuple[str, ...]]) -> None: ...

    @abstractmethod
    def yield_keys(self, prefix: Sequence[str] | None = None) -> Iterator[tuple[str, ...]]: ...

    def get(self, key: tuple[str, ...]) -> Any | None:
        return self.mget([key])[0]

    def set(self, key: tuple[str, ...], value: Any) -> None:
        self.mset([(key, value)])

    def delete(self, key: tuple[str, ...]) -> None:
        self.mdelete([key])


class InMemoryStore(BaseStore):
    """Process-local store (upstream stores.py:244); values any picklable object."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, ...], Any] = {}

    def mget(self, keys: Sequence[tuple[str, ...]]) -> list[Any | None]:
        return [self._store.get(_check_key(k)) for k in keys]

    def mset(self, pairs: Sequence[tuple[tuple[str, ...], Any]]) -> None:
        for key, value in pairs:
            self._store[_check_key(key)] = value

    def mdelete(self, keys: Sequence[tuple[str, ...]]) -> None:
        for k in keys:
            self._store.pop(_check_key(k), None)

    def yield_keys(self, prefix: Sequence[str] | None = None) -> Iterator[tuple[str, ...]]:
        prefix_tuple = tuple(prefix or ())
        for key in list(self._store):
            if key[:len(prefix_tuple)] == prefix_tuple:
                yield key


class InMemoryByteStore(InMemoryStore):
    """The bytes-flavored variant (upstream stores.py:267) - values must be bytes."""

    def mset(self, pairs: Sequence[tuple[tuple[str, ...], Any]]) -> None:
        for key, value in pairs:
            if not isinstance(value, bytes):
                raise TypeError(f"InMemoryByteStore stores bytes, got {type(value).__name__}")
        super().mset(pairs)
