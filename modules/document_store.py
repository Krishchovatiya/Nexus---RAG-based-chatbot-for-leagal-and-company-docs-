"""
modules/document_store.py
In-memory document store and knowledge base builder.
Handles storage, retrieval, and compilation of ingested documents.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
import config
from modules.pdf_parser import extract_text_pypdf


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Document:
    name: str
    ext: str
    size: int           # bytes
    content: str        # extracted/raw text
    ingested: bool = False

    def size_label(self) -> str:
        if self.size < 1024:
            return f"{self.size} B"
        if self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        return f"{self.size / (1024**2):.1f} MB"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ext": self.ext,
            "size": self.size,
            "size_label": self.size_label(),
            "ingested": self.ingested,
            "preview": self.content[:120] + "…" if len(self.content) > 120 else self.content,
        }


# ── Store singleton ───────────────────────────────────────────────────────────

class DocumentStore:
    """Thread-unsafe in-memory store (fine for single-user local use)."""

    def __init__(self) -> None:
        self._documents: list[Document] = []
        self._knowledge_base: str = ""
        self._is_ingested: bool = False

    # ── Add ───────────────────────────────────────────────────────────────────

    def add(self, name: str, data: bytes) -> tuple[bool, str]:
        """
        Parse and store a new document from raw bytes.
        Returns (success, message).
        """
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""

        if ext not in config.SUPPORTED_EXTS:
            return False, f"Unsupported file type: {ext}"

        if any(d.name == name for d in self._documents):
            return False, f"Already uploaded: {name}"

        size = len(data)

        # Extract text based on type
        if ext == ".pdf":
            content = extract_text_pypdf(data, name, config.MAX_DOC_CHARS)
        else:
            try:
                content = data.decode("utf-8", errors="replace")
            except Exception:
                content = data.decode("latin-1", errors="replace")
            content = content[:config.MAX_DOC_CHARS]

        doc = Document(name=name, ext=ext, size=size, content=content)
        self._documents.append(doc)
        self._is_ingested = False   # require re-ingest after new upload

        return True, f"Added: {name}"

    # ── Remove ────────────────────────────────────────────────────────────────

    def remove(self, name: str) -> tuple[bool, str]:
        before = len(self._documents)
        self._documents = [d for d in self._documents if d.name != name]
        if len(self._documents) < before:
            self._is_ingested = False
            self._knowledge_base = ""
            return True, f"Removed: {name}"
        return False, f"Not found: {name}"

    # ── Ingest ────────────────────────────────────────────────────────────────

    def ingest(self) -> tuple[bool, str]:
        """Compile all documents into the knowledge base string."""
        if not self._documents:
            return False, "No documents to ingest"

        parts = []
        for doc in self._documents:
            header = "\n".join([
                "━" * 50,
                f"DOCUMENT : {doc.name}",
                f"FORMAT   : {doc.ext.upper()}   SIZE: {doc.size_label()}",
                "━" * 50,
                "",
            ])
            parts.append(header + doc.content + "\n")

        self._knowledge_base = "\n".join(parts)
        self._is_ingested = True

        for doc in self._documents:
            doc.ingested = True

        count = len(self._documents)
        return True, f"{count} document{'s' if count != 1 else ''} ingested"

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def knowledge_base(self) -> str:
        return self._knowledge_base

    @property
    def is_ingested(self) -> bool:
        return self._is_ingested

    @property
    def documents(self) -> list[Document]:
        return list(self._documents)

    def to_list(self) -> list[dict]:
        return [d.to_dict() for d in self._documents]

    def clear(self) -> None:
        self._documents.clear()
        self._knowledge_base = ""
        self._is_ingested = False


# Global singleton
store = DocumentStore()
