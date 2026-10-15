from typing import Optional, Tuple

from app.parsers.base import DocumentParser
from app.parsers.csv_parser import CSVParser
from app.parsers.docx_parser import DocxParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.text_parser import TextParser

# Magic byte signatures
PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"  # Base ZIP signature used by OOXML (.docx)
EXECUTABLE_MAGICS = [
    b"MZ",  # Windows PE Executable
    b"\x7fELF",  # Linux ELF Executable
    b"\xca\xfe\xba\xbe",  # Mach-O fat binary / Java class
    b"\xce\xfa\xed\xfe",  # Mach-O binary
    b"\xcf\xfa\xed\xfe",  # Mach-O 64-bit
]


def detect_and_validate_format(
    filename: str,
    mime_type: Optional[str],
    header_bytes: bytes,
) -> Tuple[str, DocumentParser]:
    """
    Validate magic bytes and extension to detect file format.
    Guarantees that files cannot masquerade with false extensions.
    """
    lower_filename = filename.lower()

    # Reject dangerous executable formats immediately regardless of filename
    for magic in EXECUTABLE_MAGICS:
        if header_bytes.startswith(magic):
            raise ValueError("Executable binaries are strictly prohibited")

    # Reject shell script / python execution attempts
    if header_bytes.startswith(b"#!"):
        raise ValueError("Script files with shebang headers are strictly prohibited")

    # 1. PDF Validation
    if lower_filename.endswith(".pdf"):
        if not header_bytes.startswith(PDF_MAGIC):
            raise ValueError("File has .pdf extension but does not contain a valid PDF signature")
        return "pdf", PDFParser()

    # 2. DOCX Validation
    if lower_filename.endswith(".docx"):
        if not header_bytes.startswith(ZIP_MAGIC):
            raise ValueError("File has .docx extension but does not contain a valid OOXML/ZIP signature")
        return "docx", DocxParser()

    # 3. CSV Validation
    if lower_filename.endswith(".csv"):
        # Ensure it is not binary data
        if b"\x00" in header_bytes[:512]:
            raise ValueError("File has .csv extension but contains binary null bytes")
        return "csv", CSVParser()

    # 4. Plain Text Validation (.txt, .md, .text)
    if lower_filename.endswith((".txt", ".md", ".text")):
        if b"\x00" in header_bytes[:512]:
            raise ValueError("File has text extension but contains binary null bytes")
        return "txt", TextParser()

    # Detect by magic bytes if extension is generic or missing
    if header_bytes.startswith(PDF_MAGIC):
        return "pdf", PDFParser()
    if header_bytes.startswith(ZIP_MAGIC) and lower_filename.endswith(".docx"):
        return "docx", DocxParser()

    raise ValueError(
        f"Unsupported file format for '{filename}'. Supported formats are: PDF (.pdf), DOCX (.docx), CSV (.csv), and TXT (.txt, .md)."
    )
