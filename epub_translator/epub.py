from __future__ import annotations

import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET


@dataclass(slots=True)
class Chapter:
    index: int
    idref: str
    path: str
    title: str


class EpubBook:
    def __init__(self, epub_path: Path):
        self.epub_path = Path(epub_path)
        self.files: dict[str, bytes] = {}
        self.opf_path = ""
        self.base_path = ""
        self.manifest: dict[str, str] = {}
        self.spine: list[str] = []
        self.chapters: list[Chapter] = []
        self.original_text: dict[str, str] = {}

    @classmethod
    def load(cls, epub_path: str | Path) -> "EpubBook":
        book = cls(Path(epub_path))
        with zipfile.ZipFile(book.epub_path, "r") as archive:
            book.files = {name: archive.read(name) for name in archive.namelist()}
        book._parse()
        return book

    def read_text(self, path: str) -> str:
        normalized = self._normalize(path)
        data = self.files[normalized]
        text = data.decode("utf-8", errors="replace")
        self.original_text.setdefault(normalized, text)
        return text

    def write_text(self, path: str, text: str) -> None:
        self.files[self._normalize(path)] = text.encode("utf-8")

    def export(self, output_path: str | Path) -> None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w") as archive:
            if "mimetype" in self.files:
                archive.writestr(
                    zipfile.ZipInfo("mimetype"),
                    self.files["mimetype"],
                    compress_type=zipfile.ZIP_STORED,
                )
            for name, data in self.files.items():
                if name == "mimetype":
                    continue
                archive.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)

    def _parse(self) -> None:
        container = self.files.get("META-INF/container.xml")
        if not container:
            raise ValueError("Invalid EPUB: missing META-INF/container.xml")
        container_root = ET.fromstring(container)
        rootfile = find_first(container_root, "rootfile")
        if rootfile is None:
            raise ValueError("Invalid EPUB: missing rootfile in container.xml")
        self.opf_path = rootfile.attrib.get("full-path", "")
        if not self.opf_path or self.opf_path not in self.files:
            raise ValueError(f"Invalid EPUB: missing OPF file {self.opf_path}")
        self.base_path = posixpath.dirname(self.opf_path)

        opf_root = ET.fromstring(self.files[self.opf_path])
        for item in find_all(opf_root, "item"):
            item_id = item.attrib.get("id")
            href = item.attrib.get("href")
            if item_id and href:
                self.manifest[item_id] = unquote(href)
        for itemref in find_all(opf_root, "itemref"):
            idref = itemref.attrib.get("idref")
            if idref:
                self.spine.append(idref)
        self.chapters = self._build_chapters()

    def _build_chapters(self) -> list[Chapter]:
        chapters: list[Chapter] = []
        for index, idref in enumerate(self.spine, start=1):
            href = self.manifest.get(idref)
            if not href:
                continue
            path = self._join(self.base_path, href)
            if path not in self.files:
                continue
            chapters.append(Chapter(index=index, idref=idref, path=path, title=Path(path).name))
        return chapters

    def _join(self, base: str, href: str) -> str:
        joined = posixpath.normpath(posixpath.join(base, href)) if base else posixpath.normpath(href)
        return joined.replace("\\", "/")

    def _normalize(self, path: str) -> str:
        normalized = path.replace("\\", "/")
        if normalized in self.files:
            return normalized
        lowered = normalized.lower()
        for name in self.files:
            if name.lower() == lowered:
                return name
        raise KeyError(f"File not found in EPUB: {path}")


def strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def find_first(root: ET.Element, name: str) -> ET.Element | None:
    for elem in root.iter():
        if strip_ns(elem.tag) == name:
            return elem
    return None


def find_all(root: ET.Element, name: str) -> list[ET.Element]:
    return [elem for elem in root.iter() if strip_ns(elem.tag) == name]
