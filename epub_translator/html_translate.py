from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from threading import Event
from typing import Callable

from bs4 import BeautifulSoup, Tag

from .cache import TranslationCache
from .providers import build_provider
from .settings import TranslationSettings


ProgressCallback = Callable[[int, int, str], None]
PreviewCallback = Callable[[str], None]

TRANSLATABLE_TAGS = ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "figcaption")
SKIP_PARENT_TAGS = {"script", "style", "svg", "math", "pre", "code"}


def translate_html(
    html: str,
    settings: TranslationSettings,
    cache: TranslationCache | None = None,
    progress: ProgressCallback | None = None,
    preview: PreviewCallback | None = None,
    cancel_event: Event | None = None,
) -> str:
    soup = BeautifulSoup(remove_scripts(html), "xml")
    targets = collect_targets(soup)
    if not targets:
        return str(soup)

    units = [(tag, inner_html(tag)) for tag in targets]
    provider = build_provider(settings)
    cache = cache or TranslationCache(None)
    total = len(units)
    completed = 0

    pending: list[tuple[Tag, str]] = []
    for tag, text in units:
        cached = cache.get(text, settings)
        if cached:
            if is_cancelled(cancel_event):
                cache.save()
                return str(soup)
            apply_translation(soup, tag, cached, settings)
            completed += 1
            if progress:
                progress(completed, total, "cache")
            if preview:
                preview(str(soup))
        else:
            pending.append((tag, text))

    chunk_size = max(1, settings.paragraphs_per_request)
    chunks = [pending[i : i + chunk_size] for i in range(0, len(pending), chunk_size)]
    max_workers = max(1, settings.max_concurrency)
    if settings.provider == "google-web":
        max_workers = min(max_workers, 3)

    def translate_chunk(chunk: list[tuple[Tag, str]]) -> tuple[list[tuple[Tag, str]], list[str]]:
        texts = [text for _, text in chunk]
        return chunk, provider.translate_batch(texts)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        iterator = iter(chunks)
        futures: set[Future[tuple[list[tuple[Tag, str]], list[str]]]] = set()

        def fill_queue() -> None:
            while not is_cancelled(cancel_event) and len(futures) < max_workers:
                try:
                    chunk = next(iterator)
                except StopIteration:
                    return
                futures.add(executor.submit(translate_chunk, chunk))

        fill_queue()
        while futures:
            done, futures = wait(futures, return_when=FIRST_COMPLETED)
            if is_cancelled(cancel_event):
                for future in futures:
                    future.cancel()
                break
            for future in done:
                chunk, translations = future.result()
                for (tag, text), translated in zip(chunk, translations):
                    if is_cancelled(cancel_event):
                        break
                    if translated not in ("[Translation Failed]", "[Translation Missing]"):
                        apply_translation(soup, tag, translated, settings)
                        cache.set(text, translated, settings)
                    completed += 1
                    if progress:
                        progress(completed, total, "translated")
                    if preview:
                        preview(str(soup))
            fill_queue()

    cache.save()
    return str(soup)


def is_cancelled(cancel_event: Event | None) -> bool:
    return bool(cancel_event and cancel_event.is_set())


def remove_scripts(html: str) -> str:
    soup = BeautifulSoup(html, "xml")
    for script in soup.find_all("script"):
        script.decompose()
    return str(soup)


def collect_targets(soup: BeautifulSoup) -> list[Tag]:
    targets: list[Tag] = []
    for tag in soup.find_all(TRANSLATABLE_TAGS):
        classes = set(tag.get("class", []))
        if "translated" in classes or "translation-block" in classes:
            continue
        if tag.get("data-epub-translator-original") == "1":
            continue
        if tag.find_parent(class_="translation-block"):
            continue
        if has_selected_parent(tag, targets):
            continue
        if has_translatable_text(tag) and inner_html(tag).strip():
            targets.append(tag)
    return targets


def has_selected_parent(tag: Tag, targets: list[Tag]) -> bool:
    return any(parent in targets for parent in tag.parents if isinstance(parent, Tag))


def has_translatable_text(tag: Tag) -> bool:
    for text in tag.find_all(string=True):
        if not text.strip():
            continue
        if any(parent.name in SKIP_PARENT_TAGS for parent in text.parents if isinstance(parent, Tag)):
            continue
        return True
    return False


def inner_html(tag: Tag) -> str:
    return "".join(str(child) for child in tag.contents).strip()


def apply_translation(soup: BeautifulSoup, tag: Tag, translated: str, settings: TranslationSettings) -> None:
    if settings.mode == "bilingual":
        trans_tag = soup.new_tag(tag.name)
        trans_tag["class"] = ["translation-block", "translated"]
        trans_tag["style"] = "color:#111;margin-top:4px;margin-bottom:4px;"
        trans_tag.append(BeautifulSoup(translated, "html.parser"))
        tag["data-epub-translator-original"] = "1"
        append_style(tag, "color:#777;opacity:.72;margin-top:0;margin-bottom:12px;")
        tag.insert_before(trans_tag)
    else:
        tag.clear()
        tag.append(BeautifulSoup(translated, "html.parser"))
        add_class(tag, "translated")


def add_class(tag: Tag, class_name: str) -> None:
    classes = list(tag.get("class", []))
    if class_name not in classes:
        classes.append(class_name)
    tag["class"] = classes


def append_style(tag: Tag, style: str) -> None:
    current = str(tag.get("style", "")).strip()
    if style in current:
        return
    separator = "" if not current or current.endswith(";") else ";"
    tag["style"] = f"{current}{separator}{style}" if current else style
