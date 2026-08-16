"""Small provider-independent private object storage boundary.

The local backend is the default for development. A future R2 adapter can
implement the same three operations without changing API or database code.
"""

from pathlib import Path
from typing import Protocol


class PrivateObjectStore(Protocol):
    def put(self, key: str, content: bytes) -> None: ...
    def delete(self, key: str) -> None: ...
    def path(self, key: str) -> Path | None: ...


class LocalPrivateObjectStore:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if candidate.parent != self.root or candidate == self.root:
            raise ValueError("invalid storage key")
        return candidate

    def put(self, key: str, content: bytes) -> None:
        self._safe_path(key).write_bytes(content)

    def delete(self, key: str) -> None:
        self._safe_path(key).unlink(missing_ok=True)

    def path(self, key: str) -> Path | None:
        candidate = self._safe_path(key)
        return candidate if candidate.is_file() else None
