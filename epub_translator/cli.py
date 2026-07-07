from __future__ import annotations

import argparse
from pathlib import Path

from .cache import TranslationCache
from .epub import EpubBook
from .html_translate import translate_html
from .settings import TranslationSettings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Translate EPUB books.")
    parser.add_argument("input", type=Path, help="Input .epub file")
    parser.add_argument("output", type=Path, help="Output .epub file")
    parser.add_argument("--provider", default="google-web", choices=["google-web", "openai", "gemini", "custom", "deepseek", "ollama"])
    parser.add_argument("--target", default="Traditional Chinese", help="Target language name")
    parser.add_argument("--mode", default="bilingual", choices=["translate-only", "bilingual"])
    parser.add_argument("--api-key", default="")
    parser.add_argument("--api-url", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--glossary", default="")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--paragraphs", type=int, default=4)
    parser.add_argument("--cache", type=Path, default=Path(".translation_cache.json"))
    parser.add_argument("--chapter", type=int, action="append", help="Translate only selected chapter number. Repeatable.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = TranslationSettings(
        mode=args.mode,
        provider=args.provider,
        api_key=args.api_key,
        api_url=args.api_url,
        model=args.model,
        target_language=args.target,
        max_concurrency=args.concurrency,
        paragraphs_per_request=args.paragraphs,
        glossary=args.glossary,
        cache_path=args.cache,
    )
    book = EpubBook.load(args.input)
    cache = TranslationCache(settings.cache_path)
    selected = set(args.chapter or [])
    chapters = [chapter for chapter in book.chapters if not selected or chapter.index in selected]

    for position, chapter in enumerate(chapters, start=1):
        print(f"[{position}/{len(chapters)}] Translating {chapter.title}")

        def on_progress(done: int, total: int, source: str) -> None:
            print(f"  {done}/{total} paragraphs ({source})", end="\r")

        translated = translate_html(book.read_text(chapter.path), settings, cache=cache, progress=on_progress)
        print()
        book.write_text(chapter.path, translated)

    book.export(args.output)
    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
