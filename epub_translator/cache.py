from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import Lock

from .settings import TranslationSettings


class TranslationCache:
    def __init__(self, path: Path | None):
        self.path = path
        self._lock = Lock()
        self._data: dict[str, str] = {}
        if path and path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._data = {}

    def key(self, text: str, settings: TranslationSettings) -> str:
        payload = "\n".join(
            [
                settings.provider,
                settings.api_url,
                settings.model,
                settings.target_language,
                settings.glossary,
                text,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, text: str, settings: TranslationSettings) -> str | None:
        return self._data.get(self.key(text, settings))

    def set(self, text: str, translated: str, settings: TranslationSettings) -> None:
        if not self.path:
            return
        with self._lock:
            self._data[self.key(text, settings)] = translated

    def save(self) -> None:
        if not self.path:
            return
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
