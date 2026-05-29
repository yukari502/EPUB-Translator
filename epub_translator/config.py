from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .settings import TranslationSettings


CONFIG_PATH = Path.home() / ".epub_translator" / "config.json"

CONFIG_KEYS = {
    "mode",
    "provider",
    "api_key",
    "api_url",
    "model",
    "target_language",
    "max_concurrency",
    "paragraphs_per_request",
    "glossary",
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: value for key, value in data.items() if key in CONFIG_KEYS}


def save_config(settings: TranslationSettings, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "mode": settings.mode,
        "provider": settings.provider,
        "api_key": settings.api_key,
        "api_url": settings.api_url,
        "model": settings.model,
        "target_language": settings.target_language,
        "max_concurrency": settings.max_concurrency,
        "paragraphs_per_request": settings.paragraphs_per_request,
        "glossary": settings.glossary,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def settings_from_config(config: dict[str, Any]) -> TranslationSettings:
    settings = TranslationSettings()
    for key, value in config.items():
        if not hasattr(settings, key):
            continue
        if key in {"max_concurrency", "paragraphs_per_request"}:
            try:
                value = max(1, int(value))
            except (TypeError, ValueError):
                continue
        elif not isinstance(value, str):
            continue
        setattr(settings, key, value)
    return settings
