import csv
import io
from typing import BinaryIO

from app.parsers.base import DocumentParser, ParsedDocument

MAX_CSV_ROWS = 5_000
MAX_CSV_COLS = 50
MAX_CSV_CHARS = 50_000

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class CSVParser(DocumentParser):
    def parse(self, stream: BinaryIO, filename: str) -> ParsedDocument:
        raw_bytes = stream.read()
        try:
            content_str = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content_str = raw_bytes.decode("latin-1", errors="replace")

        # Strip null bytes
        content_str = content_str.replace("\x00", "")

        string_io = io.StringIO(content_str, newline="")
        reader = csv.reader(string_io)

        sanitized_rows = []
        row_count = 0
        col_count = 0
        total_chars = 0
        truncated = False
        formula_sanitized = False

        for row in reader:
            if row_count >= MAX_CSV_ROWS:
                truncated = True
                break
            row_count += 1
            col_count = max(col_count, len(row))

            sanitized_row = []
            for cell in row[:MAX_CSV_COLS]:
                cell_raw = str(cell)
                # Neutralize spreadsheet formula injection including tab and carriage return exploits
                if cell_raw.startswith(("\t", "\r")) or cell_raw.lstrip().startswith(("=", "+", "-", "@")):
                    cell_str = f"'{cell_raw.strip()}"
                    formula_sanitized = True
                else:
                    cell_str = cell_raw.strip()
                sanitized_row.append(cell_str)

            row_line = ", ".join(sanitized_row)
            total_chars += len(row_line) + 1
            sanitized_rows.append(row_line)

            if total_chars >= MAX_CSV_CHARS:
                truncated = True
                break

        full_text = "\n".join(sanitized_rows)
        words = len(full_text.split())
        snippet = full_text[:500].strip()

        return ParsedDocument(
            text=full_text,
            snippet=snippet,
            word_count=words,
            char_count=len(full_text),
            page_count=None,
            metadata={
                "format": "csv",
                "filename": filename,
                "row_count": row_count,
                "col_count": col_count,
                "is_truncated": truncated,
                "formula_injection_sanitized": formula_sanitized,
            },
        )
