from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.parsers.base import DocumentParser, ParsedDocument

MAX_PDF_PAGES = 100
MAX_PDF_CHARS = 50_000


class PDFParser(DocumentParser):
    def parse(self, stream: BinaryIO, filename: str) -> ParsedDocument:
        try:
            reader = PdfReader(stream)
        except (PdfReadError, Exception) as exc:
            raise ValueError(f"Corrupted or invalid PDF file: {exc}") from exc

        if reader.is_encrypted:
            raise ValueError("Encrypted or password-protected PDF files are not supported")

        total_pages = len(reader.pages)
        pages_to_process = min(total_pages, MAX_PDF_PAGES)
        extracted_pages = []
        total_chars = 0
        truncated = total_pages > MAX_PDF_PAGES

        for page_idx in range(pages_to_process):
            try:
                page = reader.pages[page_idx]
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            page_text = page_text.strip()
            if page_text:
                extracted_pages.append(page_text)
                total_chars += len(page_text)

            if total_chars >= MAX_PDF_CHARS:
                truncated = True
                break

        full_text = "\n\n".join(extracted_pages)
        if len(full_text) > MAX_PDF_CHARS:
            full_text = full_text[:MAX_PDF_CHARS]
            truncated = True

        words = len(full_text.split())
        snippet = full_text[:500].strip()

        # Extract basic PDF metadata if available
        meta = {}
        if reader.metadata:
            meta["title"] = reader.metadata.title or ""
            meta["author"] = reader.metadata.author or ""
            meta["creator"] = reader.metadata.creator or ""

        return ParsedDocument(
            text=full_text,
            snippet=snippet,
            word_count=words,
            char_count=len(full_text),
            page_count=total_pages,
            metadata={
                "format": "pdf",
                "filename": filename,
                "total_pages": total_pages,
                "processed_pages": pages_to_process,
                "is_truncated": truncated,
                **meta,
            },
        )
