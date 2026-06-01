from __future__ import annotations

import queue
import threading
import webbrowser
from pathlib import Path
from tempfile import NamedTemporaryFile
from tkinter import BOTH, END, LEFT, RIGHT, X, filedialog, messagebox
import tkinter as tk
from tkinter import ttk

from bs4 import BeautifulSoup

from .cache import TranslationCache
from .config import CONFIG_PATH, load_config, save_config, settings_from_config
from .epub import Chapter, EpubBook
from .html_translate import translate_html
from .settings import TranslationSettings


PROVIDERS = ["google-web", "ollama", "deepseek", "openai", "gemini", "custom"]
LANGUAGES = ["Simplified Chinese", "Traditional Chinese", "English", "Japanese", "Korean", "Spanish", "French", "German", "Russian"]


class TranslatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("EPUB Translator")
        self.geometry("1120x760")
        self.minsize(900, 620)
        self.book: EpubBook | None = None
        self.active_chapter: Chapter | None = None
        self.cache = TranslationCache(Path(".translation_cache.json"))
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.is_busy = False
        self.cancel_event = threading.Event()
        self.preview_window: tk.Toplevel | None = None
        self.preview_text: tk.Text | None = None
        self.saved_settings = settings_from_config(load_config())

        self.provider = tk.StringVar(value=self.saved_settings.provider)
        self.mode = tk.StringVar(value=self.saved_settings.mode)
        self.target = tk.StringVar(value=self.saved_settings.target_language)
        self.api_key = tk.StringVar(value=self.saved_settings.api_key)
        self.api_url = tk.StringVar(value=self.saved_settings.api_url)
        self.model = tk.StringVar(value=self.saved_settings.model)
        self.concurrency = tk.IntVar(value=self.saved_settings.max_concurrency)
        self.paragraphs = tk.IntVar(value=self.saved_settings.paragraphs_per_request)

        self._build_ui()
        self.glossary.insert("1.0", self.saved_settings.glossary)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self._drain_events)

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill=X)
        ttk.Button(toolbar, text="Open EPUB", command=self.open_epub).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Translate Chapter", command=self.translate_active).pack(side=LEFT, padx=6)
        ttk.Button(toolbar, text="Translate All", command=self.translate_all).pack(side=LEFT, padx=6)
        self.stop_button = ttk.Button(toolbar, text="Stop", command=self.cancel_translation, state=tk.DISABLED)
        self.stop_button.pack(side=LEFT, padx=6)
        ttk.Button(toolbar, text="Save Settings", command=self.save_settings).pack(side=LEFT, padx=6)
        ttk.Button(toolbar, text="Export", command=self.export_epub).pack(side=LEFT, padx=6)
        ttk.Button(toolbar, text="Live Preview", command=self.open_live_preview).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(toolbar, text="Open Preview", command=self.open_preview).pack(side=RIGHT)

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=BOTH, expand=True)

        left = ttk.Frame(body, padding=8)
        body.add(left, weight=1)
        ttk.Label(left, text="Chapters").pack(anchor="w")
        self.chapter_list = tk.Listbox(left, exportselection=False)
        self.chapter_list.pack(fill=BOTH, expand=True, pady=(6, 0))
        self.chapter_list.bind("<<ListboxSelect>>", self.on_chapter_select)

        right = ttk.PanedWindow(body, orient=tk.VERTICAL)
        body.add(right, weight=4)

        settings = ttk.LabelFrame(right, text="Settings", padding=8)
        right.add(settings, weight=0)
        self._settings_grid(settings)

        preview_frame = ttk.Frame(right, padding=8)
        right.add(preview_frame, weight=4)
        ttk.Label(preview_frame, text="Chapter XHTML").pack(anchor="w")
        self.text = create_scrolled_text(preview_frame, wrap="word", undo=True)

        status = ttk.Frame(self, padding=(8, 4))
        status.pack(fill=X)
        self.progress = ttk.Progressbar(status, mode="determinate")
        self.progress.pack(side=LEFT, fill=X, expand=True)
        self.status = ttk.Label(status, text="Ready", width=34)
        self.status.pack(side=RIGHT, padx=(8, 0))

    def _settings_grid(self, parent: ttk.Frame) -> None:
        fields = [
            ("Provider", ttk.Combobox(parent, textvariable=self.provider, values=PROVIDERS, state="readonly", width=18)),
            ("Mode", ttk.Combobox(parent, textvariable=self.mode, values=["translate-only", "bilingual"], state="readonly", width=18)),
            ("Target", ttk.Combobox(parent, textvariable=self.target, values=LANGUAGES, width=18)),
            ("Model", ttk.Entry(parent, textvariable=self.model, width=24)),
            ("API URL", ttk.Entry(parent, textvariable=self.api_url, width=36)),
            ("API Key", ttk.Entry(parent, textvariable=self.api_key, show="*", width=28)),
            ("Concurrency", ttk.Spinbox(parent, from_=1, to=100, textvariable=self.concurrency, width=8)),
            ("Paragraphs", ttk.Spinbox(parent, from_=1, to=20, textvariable=self.paragraphs, width=8)),
        ]
        for index, (label, widget) in enumerate(fields):
            row = index // 4
            col = (index % 4) * 2
            ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=(0, 4), pady=4)
            widget.grid(row=row, column=col + 1, sticky="we", padx=(0, 12), pady=4)
        ttk.Label(parent, text="Glossary / Instructions").grid(row=2, column=0, sticky="nw", pady=4)
        self.glossary = tk.Text(parent, height=3, width=80)
        self.glossary.grid(row=2, column=1, columnspan=7, sticky="we", pady=4)
        for column in range(8):
            parent.columnconfigure(column, weight=1 if column % 2 == 1 else 0)
            
        cache_frame = ttk.Frame(parent)
        cache_frame.grid(row=3, column=0, columnspan=8, sticky="w", pady=(8, 4))
        ttk.Button(cache_frame, text="Load Cache...", command=self.load_cache).pack(side=LEFT, padx=(0, 6))
        ttk.Button(cache_frame, text="Clear Cache", command=self.clear_cache).pack(side=LEFT)

    def settings(self) -> TranslationSettings:
        return TranslationSettings(
            mode=self.mode.get(),
            provider=self.provider.get(),
            api_key=self.api_key.get(),
            api_url=self.api_url.get(),
            model=self.model.get(),
            target_language=self.target.get(),
            max_concurrency=max(1, int(self.concurrency.get())),
            paragraphs_per_request=max(1, int(self.paragraphs.get())),
            glossary=self.glossary.get("1.0", END).strip(),
            cache_path=Path(".translation_cache.json"),
        )

    def save_settings(self) -> None:
        try:
            save_config(self.settings())
            self.status.config(text=f"Settings saved: {CONFIG_PATH}")
        except Exception as exc:
            messagebox.showerror("Save settings failed", str(exc))

    def open_epub(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("EPUB files", "*.epub"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.book = EpubBook.load(path)
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))
            return
        self.chapter_list.delete(0, END)
        for chapter in self.book.chapters:
            self.chapter_list.insert(END, f"{chapter.index}. {chapter.title}")
        if self.book.chapters:
            self.chapter_list.selection_set(0)
            self.load_chapter(self.book.chapters[0])
        self.status.config(text=f"Loaded {Path(path).name}")

    def on_chapter_select(self, _event: object) -> None:
        if not self.book:
            return
        selection = self.chapter_list.curselection()
        if selection:
            self.load_chapter(self.book.chapters[selection[0]])

    def load_chapter(self, chapter: Chapter) -> None:
        if not self.book:
            return
        self.active_chapter = chapter
        self.text.delete("1.0", END)
        self.text.insert("1.0", self.book.read_text(chapter.path))
        self.update_live_preview(self.text.get("1.0", END))
        self.status.config(text=chapter.title)

    def translate_active(self) -> None:
        if not self.book or not self.active_chapter:
            messagebox.showinfo("No chapter", "Open an EPUB and select a chapter first.")
            return
        self._start_worker([self.active_chapter])

    def translate_all(self) -> None:
        if not self.book:
            messagebox.showinfo("No EPUB", "Open an EPUB first.")
            return
        if messagebox.askyesno("Translate all", "Translate every spine chapter in this EPUB?"):
            self._start_worker(self.book.chapters)

    def _start_worker(self, chapters: list[Chapter]) -> None:
        if self.is_busy or not self.book:
            return
        self.is_busy = True
        self.cancel_event.clear()
        self.stop_button.config(state=tk.NORMAL)
        self.progress.config(maximum=max(1, len(chapters)), value=0)
        settings = self.settings()
        save_config(settings)
        book = self.book
        cancel_event = self.cancel_event

        def worker() -> None:
            try:
                for index, chapter in enumerate(chapters, start=1):
                    if cancel_event.is_set():
                        self.events.put(("cancelled", "Translation stopped"))
                        return
                    self.events.put(("status", f"Translating {chapter.title}"))

                    def on_progress(done: int, total: int, source: str) -> None:
                        self.events.put(("status", f"{chapter.title}: {done}/{total} paragraphs ({source})"))

                    def on_preview(html: str) -> None:
                        self.events.put(("preview_update", (chapter, html)))

                    translated = translate_html(
                        book.read_text(chapter.path),
                        settings,
                        self.cache,
                        on_progress,
                        on_preview,
                        cancel_event,
                    )
                    book.write_text(chapter.path, translated)
                    self.events.put(("chapter_done", (index, chapter, translated)))
                    if cancel_event.is_set():
                        self.events.put(("cancelled", "Translation stopped"))
                        return
                self.events.put(("done", "Translation complete"))
            except Exception as exc:
                import traceback
                self.events.put(("error", traceback.format_exc()))

        threading.Thread(target=worker, daemon=True).start()

    def _drain_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "status":
                self.status.config(text=str(payload))
            elif kind == "chapter_done":
                index, chapter, translated = payload  # type: ignore[misc]
                self.progress.config(value=index)
                if self.active_chapter and chapter.path == self.active_chapter.path:
                    self.text.delete("1.0", END)
                    self.text.insert("1.0", translated)
                    self.update_live_preview(translated)
            elif kind == "preview_update":
                chapter, html = payload  # type: ignore[misc]
                if self.active_chapter and chapter.path == self.active_chapter.path:
                    self.text.delete("1.0", END)
                    self.text.insert("1.0", html)
                    self.update_live_preview(html)
            elif kind == "done":
                self.is_busy = False
                self.stop_button.config(state=tk.DISABLED)
                self.status.config(text=str(payload))
            elif kind == "cancelled":
                self.is_busy = False
                self.stop_button.config(state=tk.DISABLED)
                self.status.config(text=str(payload))
            elif kind == "error":
                self.is_busy = False
                self.stop_button.config(state=tk.DISABLED)
                self.status.config(text="Error")
                messagebox.showerror("Translation failed", str(payload))
        self.after(100, self._drain_events)

    def cancel_translation(self) -> None:
        if not self.is_busy:
            return
        self.cancel_event.set()
        self.status.config(text="Stopping after current request...")
        self.stop_button.config(state=tk.DISABLED)

    def load_cache(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.cache.load_from(Path(path))
            self.status.config(text=f"Loaded cache from {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Load cache failed", str(exc))

    def clear_cache(self) -> None:
        if messagebox.askyesno("Clear Cache", "Are you sure you want to delete all cached translations? This cannot be undone."):
            try:
                self.cache.clear()
                self.status.config(text="Cache cleared")
            except Exception as exc:
                messagebox.showerror("Clear cache failed", str(exc))

    def export_epub(self) -> None:
        if not self.book:
            return
            
        original_name = self.book.epub_path.stem
        target_lang = self.target.get().replace(" ", "")
        mode = "Bilingual" if self.mode.get() == "bilingual" else "TranslateOnly"
        default_name = f"{original_name}_{target_lang}_{mode}.epub"
        
        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".epub", 
            filetypes=[("EPUB files", "*.epub")]
        )
        if not path:
            return
        try:
            if self.active_chapter:
                self.book.write_text(self.active_chapter.path, self.text.get("1.0", END))
            self.book.export(path)
            self.status.config(text=f"Saved {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def open_preview(self) -> None:
        html = self.text.get("1.0", END).strip()
        if not html:
            return
        if self.book and self.active_chapter:
            self.book.write_text(self.active_chapter.path, html)
        with NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as handle:
            handle.write(html)
            path = Path(handle.name)
        webbrowser.open(path.as_uri())

    def open_live_preview(self) -> None:
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.lift()
            self.update_live_preview(self.text.get("1.0", END))
            return
        self.preview_window = tk.Toplevel(self)
        self.preview_window.title("Live Translation Preview")
        self.preview_window.geometry("760x640")
        self.preview_window.protocol("WM_DELETE_WINDOW", self.close_live_preview)

        frame = ttk.Frame(self.preview_window, padding=8)
        frame.pack(fill=BOTH, expand=True)
        self.preview_text = create_scrolled_text(frame, wrap="word", state=tk.DISABLED)
        self.update_live_preview(self.text.get("1.0", END))

    def close_live_preview(self) -> None:
        if self.preview_window:
            self.preview_window.destroy()
        self.preview_window = None
        self.preview_text = None

    def on_close(self) -> None:
        try:
            save_config(self.settings())
        except Exception:
            pass
        if self.is_busy:
            self.cancel_event.set()
        self.destroy()

    def update_live_preview(self, html: str) -> None:
        if not self.preview_text or not self.preview_text.winfo_exists():
            return
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", END)
        self.preview_text.insert("1.0", render_preview_text(html))
        self.preview_text.config(state=tk.DISABLED)


def render_preview_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for hidden in soup(["script", "style", "head", "title", "meta", "link"]):
        hidden.decompose()
    blocks = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "figcaption"]):
        text = tag.get_text(" ", strip=True)
        if text:
            prefix = ""
            classes = set(tag.get("class", []))
            if "translation-block" in classes:
                prefix = "Translation: "
            elif tag.get("data-epub-translator-original") == "1":
                prefix = "Original: "
            blocks.append(prefix + text)
    return "\n\n".join(blocks) if blocks else soup.get_text("\n", strip=True)


def create_scrolled_text(parent: tk.Widget, **kwargs: object) -> tk.Text:
    container = ttk.Frame(parent)
    container.pack(fill=BOTH, expand=True, pady=(6, 0))
    scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
    text = tk.Text(container, yscrollcommand=scrollbar.set, **kwargs)
    scrollbar.config(command=text.yview)
    text.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=tk.Y)
    return text


def main() -> None:
    app = TranslatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
