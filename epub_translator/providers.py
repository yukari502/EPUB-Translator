from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urlparse

import requests

from .settings import TranslationSettings


SEPARATOR = "\n\n%%\n\n"

LANGUAGE_CODES = {
    "Chinese": "zh-CN",
    "Simplified Chinese": "zh-CN",
    "Traditional Chinese": "zh-TW",
    "English": "en",
    "Japanese": "ja",
    "Korean": "ko",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Russian": "ru",
    "Italian": "it",
    "Portuguese": "pt",
    "Vietnamese": "vi",
}


def system_prompt(target_language: str, glossary: str = "") -> str:
    prompt = f"""You are a professional {target_language} native translator.

Translation rules:
1. Output only the translated content.
2. Keep exactly the same number of paragraphs as the input.
3. Preserve the original HTML structure exactly: do not add, remove, rename, reorder, or simplify tags and attributes.
4. Translate only human-readable text nodes. Keep code, URLs, placeholders, entities, punctuation-only text, and proper nouns unchanged when appropriate.
5. Keep inline formatting tags around the corresponding translated words.
6. For multi-paragraph input, separate translated paragraphs with %%."""
    if glossary.strip():
        prompt += f"\n\nGlossary and custom instructions:\n{glossary.strip()}"
    return prompt


class TranslationProvider(ABC):
    def __init__(self, settings: TranslationSettings):
        self.settings = settings

    @abstractmethod
    def translate_batch(self, texts: list[str]) -> list[str]:
        raise NotImplementedError

    def _request_with_retries(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, self.settings.retries + 1):
            try:
                response = requests.request(method, url, timeout=self.settings.timeout, **kwargs)
                if response.ok:
                    return response
                last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
            except requests.RequestException as exc:
                last_error = exc
            if attempt < self.settings.retries:
                time.sleep(2 ** (attempt - 1))
        raise RuntimeError(str(last_error or "request failed"))


class GoogleWebProvider(TranslationProvider):
    def translate_batch(self, texts: list[str]) -> list[str]:
        target = LANGUAGE_CODES.get(self.settings.target_language, "zh-CN")
        results: list[str] = []
        for index, text in enumerate(texts):
            response = self._request_with_retries(
                "POST",
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "auto", "tl": target, "dt": "t"},
                data={"q": text},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            payload = response.json()
            if payload and payload[0]:
                results.append("".join(part[0] for part in payload[0] if part and part[0]))
            else:
                results.append("[Translation Failed]")
            if index < len(texts) - 1:
                time.sleep(0.6)
        return results


class OpenAICompatibleProvider(TranslationProvider):
    DEFAULT_URLS = {
        "openai": "https://api.openai.com/v1/chat/completions",
        "deepseek": "https://api.deepseek.com/chat/completions",
        "ollama": "http://localhost:11434/v1/chat/completions",
        "custom": "",
    }
    DEFAULT_MODELS = {
        "openai": "gpt-4.1-mini",
        "deepseek": "deepseek-chat",
        "ollama": "llama3",
        "custom": "gpt-4.1-mini",
    }

    def translate_batch(self, texts: list[str]) -> list[str]:
        url = self._chat_completions_url()
        model = self.settings.model or self.DEFAULT_MODELS.get(self.settings.provider, self.DEFAULT_MODELS["openai"])
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        response = self._request_with_retries(
            "POST",
            url,
            headers=headers,
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system_prompt(self.settings.target_language, self.settings.glossary)},
                    {"role": "user", "content": SEPARATOR.join(texts)},
                ],
            },
        )
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        return normalize_parts(content, len(texts))

    def _chat_completions_url(self) -> str:
        url = (self.settings.api_url or self.DEFAULT_URLS.get(self.settings.provider, "")).strip()
        if not url:
            if self.settings.provider == "custom":
                raise ValueError("Custom provider requires an API URL.")
            url = self.DEFAULT_URLS["openai"]
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid API URL: {url}")
        if url.rstrip("/").endswith("/chat/completions"):
            return url
        if self.settings.provider == "deepseek":
            return url.rstrip("/") + "/chat/completions"
        return url.rstrip("/") + "/v1/chat/completions"


class GeminiProvider(TranslationProvider):
    def translate_batch(self, texts: list[str]) -> list[str]:
        model = self.settings.model or "gemini-1.5-pro"
        url = self.settings.api_url or (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )
        params = {}
        if self.settings.api_key and "key=" not in url:
            params["key"] = self.settings.api_key
        response = self._request_with_retries(
            "POST",
            url,
            params=params,
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {
                    "parts": [{"text": system_prompt(self.settings.target_language, self.settings.glossary)}]
                },
                "contents": [{"parts": [{"text": SEPARATOR.join(texts)}]}],
                "generationConfig": {"temperature": 0},
            },
        )
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return normalize_parts(content, len(texts))


def normalize_parts(content: str, expected: int) -> list[str]:
    parts = [part.strip() for part in content.split("%%")]
    if len(parts) < expected:
        parts.extend("[Translation Missing]" for _ in range(expected - len(parts)))
    return parts[:expected]


def build_provider(settings: TranslationSettings) -> TranslationProvider:
    if settings.provider == "google-web":
        return GoogleWebProvider(settings)
    if settings.provider == "gemini":
        return GeminiProvider(settings)
    return OpenAICompatibleProvider(settings)
