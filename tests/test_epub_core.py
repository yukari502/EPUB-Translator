from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup

from epub_translator.epub import EpubBook
from epub_translator.config import load_config, save_config, settings_from_config
import epub_translator.html_translate as html_translate
from epub_translator.html_translate import apply_translation, collect_targets, translate_html
from epub_translator.providers import OpenAICompatibleProvider
from epub_translator.settings import TranslationSettings
from epub_translator.gui import render_preview_text


def make_epub(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""",
        )
        archive.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf">
  <manifest><item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/></manifest>
  <spine><itemref idref="c1"/></spine>
</package>""",
        )
        archive.writestr("OEBPS/chapter1.xhtml", "<html><body><h1>Title</h1><p>Hello</p></body></html>")


class EpubCoreTests(unittest.TestCase):
    def test_epub_loads_spine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            epub = Path(tmp) / "book.epub"
            make_epub(epub)
            book = EpubBook.load(epub)
            self.assertEqual([chapter.path for chapter in book.chapters], ["OEBPS/chapter1.xhtml"])
            self.assertIn("Hello", book.read_text("OEBPS/chapter1.xhtml"))

    def test_collect_targets_skips_translation_blocks(self) -> None:
        soup = BeautifulSoup(
            "<body><p>Hello</p><p class='translation-block translated'>Bonjour</p></body>",
            "html.parser",
        )
        targets = collect_targets(soup)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].name, "p")

    def test_collect_targets_handles_nested_text(self) -> None:
        soup = BeautifulSoup(
            "<body><p><span>Hello</span> <em>world</em></p><p><code>x = 1</code></p></body>",
            "html.parser",
        )
        targets = collect_targets(soup)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].name, "p")

    def test_bilingual_dims_original_without_changing_contents(self) -> None:
        soup = BeautifulSoup('<p class="lead"><b>Hello</b> world</p>', "html.parser")
        original_tag = soup.p
        original_inner = "".join(str(child) for child in original_tag.contents)
        apply_translation(soup, original_tag, "<b>你好</b> 世界", TranslationSettings(mode="bilingual"))
        self.assertEqual("".join(str(child) for child in original_tag.contents), original_inner)
        self.assertIn("opacity:.72", original_tag["style"])
        self.assertEqual(soup.find(class_="translation-block").get_text(" ", strip=True), "你好 世界")
        self.assertLess(str(soup).index("translation-block"), str(soup).index('data-epub-translator-original="1"'))
        self.assertNotIn("border-left", soup.find(class_="translation-block").get("style", ""))

    def test_api_root_urls_are_normalized(self) -> None:
        deepseek = OpenAICompatibleProvider(
            TranslationSettings(provider="deepseek", api_url="https://api.deepseek.com")
        )
        ollama = OpenAICompatibleProvider(
            TranslationSettings(provider="ollama", api_url="http://localhost:11434")
        )
        self.assertEqual(deepseek._chat_completions_url(), "https://api.deepseek.com/chat/completions")
        self.assertEqual(ollama._chat_completions_url(), "http://localhost:11434/v1/chat/completions")

    def test_live_preview_renders_readable_text(self) -> None:
        text = render_preview_text(
            '<html><body><p class="translation-block translated">你好</p>'
            '<p data-epub-translator-original="1">Hello</p></body></html>'
        )
        self.assertEqual(text, "译文: 你好\n\n原文: Hello")

    def test_translate_html_updates_nested_bilingual_paragraphs(self) -> None:
        class FakeProvider:
            def translate_batch(self, texts: list[str]) -> list[str]:
                return ["<span>你好</span>"]

        original_builder = html_translate.build_provider
        html_translate.build_provider = lambda _settings: FakeProvider()
        try:
            result = translate_html(
                "<html><body><p><span>Hello</span></p></body></html>",
                TranslationSettings(mode="bilingual", cache_path=None),
            )
        finally:
            html_translate.build_provider = original_builder
        self.assertIn('data-epub-translator-original="1"', result)
        self.assertIn('class="translation-block translated"', result)
        self.assertIn("<span>你好</span>", result)

    def test_config_round_trips_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            save_config(
                TranslationSettings(
                    provider="openai",
                    api_key="secret",
                    api_url="https://api.example.test",
                    model="model-a",
                    mode="bilingual",
                    target_language="Japanese",
                    max_concurrency=7,
                    paragraphs_per_request=3,
                    glossary="Alice -> アリス",
                ),
                path,
            )
            settings = settings_from_config(load_config(path))
            self.assertEqual(settings.provider, "openai")
            self.assertEqual(settings.api_key, "secret")
            self.assertEqual(settings.mode, "bilingual")
            self.assertEqual(settings.target_language, "Japanese")
            self.assertEqual(settings.max_concurrency, 7)
            self.assertEqual(settings.paragraphs_per_request, 3)
            self.assertEqual(settings.glossary, "Alice -> アリス")


if __name__ == "__main__":
    unittest.main()
