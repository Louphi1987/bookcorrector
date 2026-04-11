from __future__ import annotations

import html
import io
import pathlib
import zipfile
from xml.etree import ElementTree

from docx import Document


SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".docx", ".odt"}


def load_uploaded_document(filename: str, raw_bytes: bytes) -> str:
    extension = pathlib.Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Format non pris en charge. Utilise un fichier .txt, .md, .docx ou .odt."
        )

    if extension in {".txt", ".md", ".markdown"}:
        return _decode_text(raw_bytes)
    if extension == ".docx":
        return _read_docx(raw_bytes)
    if extension == ".odt":
        return _read_odt(raw_bytes)

    raise ValueError("Format non pris en charge.")


def _decode_text(raw_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Impossible de decoder ce fichier texte.")


def _read_docx(raw_bytes: bytes) -> str:
    document = Document(io.BytesIO(raw_bytes))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n\n".join(paragraphs)


def _read_odt(raw_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        document = archive.read("content.xml")
    root = ElementTree.fromstring(document)
    paragraphs: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}p"):
            value = "".join(node.itertext()).strip()
            if value:
                paragraphs.append(html.unescape(value))
    return "\n\n".join(paragraphs)
