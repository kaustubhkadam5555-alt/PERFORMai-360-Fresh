from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMUnavailableError(Exception):
    """Raised when the configured LLM provider is unavailable, disabled, or fails connectivity."""

    pass


class LLMValidationError(Exception):
    """Raised when LLM output cannot be parsed into the required structured schema."""

    pass


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'mock', 'openai', 'anthropic', 'ollama')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the provider is configured and available for inference."""
        pass

    @abstractmethod
    async def generate_analysis(
        self,
        prompt: str,
        system_instruction: str,
    ) -> Dict[str, Any]:
        """
        Execute single-pass analysis against the provider.
        Must return a validated dictionary adhering to the analysis schema.
        Must raise an appropriate exception if execution fails or timeouts occur.
        """
        pass
