import re
from typing import BinaryIO

from app.parsers.base import DocumentParser, ParsedDocument

MAX_TEXT_CHARS = 50_000


class TextParser(DocumentParser):
    def parse(self, stream: BinaryIO, filename: str) -> ParsedDocument:
        raw_bytes = stream.read()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1", errors="replace")

        # Strip null bytes and non-printable control characters (except newline, tab, cr)
        cleaned_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # Truncate text if it exceeds maximum limit
        is_truncated = len(cleaned_text) > MAX_TEXT_CHARS
        if is_truncated:
            cleaned_text = cleaned_text[:MAX_TEXT_CHARS]

        words = len(cleaned_text.split())
        snippet = cleaned_text[:500].strip()

        return ParsedDocument(
            text=cleaned_text,
            snippet=snippet,
            word_count=words,
            char_count=len(cleaned_text),
            page_count=None,
            metadata={
                "format": "txt",
                "filename": filename,
                "is_truncated": is_truncated,
            },
        )
