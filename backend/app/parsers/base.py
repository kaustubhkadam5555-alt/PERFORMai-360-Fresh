from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Dict, Optional


@dataclass
class ParsedDocument:
    text: str
    snippet: str
    word_count: int
    char_count: int
    page_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, stream: BinaryIO, filename: str) -> ParsedDocument:
        """
        Safely parse content from binary stream into ParsedDocument.
        Must never execute code or allow unbounded memory allocation.
        """
        pass
