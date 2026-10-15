import json
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from app.ai.base import LLMProvider
from app.ai.context_builder import EvidenceContext
from app.core.config import settings


class MockLLMProvider(LLMProvider):
    """
    Deterministic in-memory mock LLM provider for zero-cost testing and local offline execution.
    Extracts grounded findings directly from the authorized EvidenceContext.
    """

    def __init__(self, context: Optional[EvidenceContext] = None):
        self.context = context

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-eval-engine-v1"

    @property
    def is_available(self) -> bool:
        return True

    async def generate_analysis(
        self,
        prompt: str,
        system_instruction: str,
    ) -> Dict[str, Any]:
        evidence_items = self.context.evidence_items if self.context else []
        strengths: List[Dict[str, Any]] = []
        improvements: List[Dict[str, Any]] = []
        contradictions: List[Dict[str, Any]] = []
        questions: List[Dict[str, Any]] = []
        limitations: List[str] = []

        if not evidence_items:
            return {
                "strengths": [],
                "improvement_opportunities": [],
                "contradictions": [],
                "suggested_discussion_questions": [
                    {
                        "category": "growth",
                        "question": "What key engineering projects or technical milestones did you achieve during this cycle?",
                        "context": "No evidence was attached to this cycle, requiring direct exploratory sync.",
                    }
                ],
                "overall_limitations": ["No evidence documents or work records were available for evaluation."],
            }

        # 1. Generate grounded strengths from available evidence items
        code_items = [
            e for e in evidence_items if e.source_type in {"pr", "pull_request", "commit", "commit_summary", "ticket"}
        ]
        doc_items = [e for e in evidence_items if e.source_type in {"design_doc", "document", "document_upload"}]
        other_items = [e for e in evidence_items if e not in code_items and e not in doc_items]

        if code_items:
            sample = code_items[0]
            strengths.append(
                {
                    "title": f"Technical Delivery & Implementation: {sample.title[:60]}",
                    "description": (
                        f"Demonstrated consistent technical contributions through verified deliverables. "
                        f"Delivered work recorded under '{sample.title}' with active reviewer collaboration."
                    ),
                    "supporting_evidence_ids": [str(sample.id)],
                    "excerpts": [(sample.metadata_json or {}).get("snippet", sample.title)[:200]],
                    "confidence": "high",
                    "limitations": [],
                }
            )

        if doc_items:
            sample_doc = doc_items[0]
            strengths.append(
                {
                    "title": f"System Design & Architecture: {sample_doc.title[:60]}",
                    "description": (
                        f"Authored technical specifications and architectural documentation under '{sample_doc.title}'. "
                        f"Established clear technical design references for team implementation."
                    ),
                    "supporting_evidence_ids": [str(sample_doc.id)],
                    "excerpts": [(sample_doc.metadata_json or {}).get("snippet", sample_doc.title)[:200]],
                    "confidence": "high",
                    "limitations": [],
                }
            )

        if other_items and len(strengths) < 3:
            sample_other = other_items[0]
            strengths.append(
                {
                    "title": f"Operational & Collaborative Initiatives: {sample_other.title[:60]}",
                    "description": (
                        f"Contributed to project execution and engineering initiatives recorded under '{sample_other.title}'."
                    ),
                    "supporting_evidence_ids": [str(sample_other.id)],
                    "excerpts": [sample_other.title],
                    "confidence": "medium",
                    "limitations": ["Relies on single summary record"],
                }
            )

        # 2. Generate improvement opportunities from detected gaps
        if self.context and self.context.detected_gaps:
            for gap in self.context.detected_gaps[:2]:
                if "Missing technical design" in gap:
                    improvements.append(
                        {
                            "title": "Technical Documentation & RFC Contribution",
                            "gap_observed": "No formal architecture specifications or design RFCs were recorded in this review cycle.",
                            "supporting_evidence_ids": [str(code_items[0].id)] if code_items else [],
                            "missing_context": "Design work may have occurred on internal whiteboards or unlinked wikis.",
                            "development_suggestion": "Author an architecture design proposal or technical RFC for upcoming major features.",
                        }
                    )
                elif "Missing code delivery" in gap:
                    improvements.append(
                        {
                            "title": "Verifiable Code Delivery Breadth",
                            "gap_observed": "Few or no pull request records were linked to this review cycle.",
                            "supporting_evidence_ids": [str(doc_items[0].id)] if doc_items else [],
                            "missing_context": "Engineering contributions may have been focused on team mentoring, reviews, or operational support.",
                            "development_suggestion": "Ensure completed merge requests and commits are actively linked to review cycle evidence.",
                        }
                    )
                elif "Recency concentration" in gap:
                    improvements.append(
                        {
                            "title": "Continuous Evidence Logging Throughout Cycle",
                            "gap_observed": "Available evidence records are clustered predominantly in the final portion of the review period.",
                            "supporting_evidence_ids": [str(e.id) for e in evidence_items[:2]],
                            "missing_context": "Work performed earlier in the cycle may not have been cataloged in this repository.",
                            "development_suggestion": "Establish quarterly evidence syncs to document milestones continuously rather than only at cycle close.",
                        }
                    )

        if not improvements:
            improvements.append(
                {
                    "title": "Cross-Functional Architecture Knowledge Sharing",
                    "gap_observed": "Work evidence demonstrates strong localized delivery, with opportunity for broader multi-team technical impact.",
                    "supporting_evidence_ids": [str(evidence_items[0].id)],
                    "missing_context": "Cross-team impact may not be captured in individual repository commits.",
                    "development_suggestion": "Lead a tech talk or cross-team engineering deep-dive on core system design patterns.",
                }
            )

        # 3. Discussion Questions
        questions = [
            {
                "category": "architecture",
                "question": "Which technical decisions or architectural tradeoffs in your recent work provided the greatest long-term value?",
                "context": "Grounds the review in concrete engineering design judgment.",
            },
            {
                "category": "delivery",
                "question": "What systemic roadblocks or dependency bottlenecks impacted technical momentum this period?",
                "context": "Identifies organizational constraints vs individual engineering performance.",
            },
            {
                "category": "growth",
                "question": "Which complex technologies, systems, or leadership domains do you aim to tackle next quarter?",
                "context": "Aligns upcoming engineering goals with professional growth.",
            },
        ]

        if self.context and self.context.completeness_score < 0.6:
            limitations.append(
                f"Evidence completeness score is {self.context.completeness_score:.2f}/1.00. Additional review inputs recommended."
            )

        return {
            "strengths": strengths,
            "improvement_opportunities": improvements,
            "contradictions": contradictions,
            "suggested_discussion_questions": questions,
            "overall_limitations": limitations,
        }


class OpenAILLMProvider(LLMProvider):
    """OpenAI API provider implementation with JSON schema mode."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.base_url = settings.OPENAI_BASE_URL or "https://api.openai.com/v1"

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate_analysis(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        if not self.is_available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI LLM provider is not configured (missing OPENAI_API_KEY)",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
            except httpx.TimeoutException as exc:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"OpenAI LLM provider timed out after {settings.LLM_TIMEOUT_SECONDS}s",
                ) from exc
            except (httpx.HTTPStatusError, Exception) as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"OpenAI LLM inference error: {exc}",
                ) from exc


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate_analysis(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        if not self.is_available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anthropic LLM provider is not configured (missing ANTHROPIC_API_KEY)",
            )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_instruction,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                raw_text = data["content"][0]["text"]
                # Strip markdown json backticks if present
                clean_json = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                return json.loads(clean_json)
            except httpx.TimeoutException as exc:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Anthropic LLM provider timed out after {settings.LLM_TIMEOUT_SECONDS}s",
                ) from exc
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Anthropic LLM inference error: {exc}",
                ) from exc


class OllamaLLMProvider(LLMProvider):
    """Local Ollama provider for local open-weights inference."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def is_available(self) -> bool:
        return True

    async def generate_analysis(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["message"]["content"]
                return json.loads(content)
            except httpx.TimeoutException as exc:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Ollama local provider timed out after {settings.LLM_TIMEOUT_SECONDS}s",
                ) from exc
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Ollama local inference error: {exc}",
                ) from exc


class DisabledLLMProvider(LLMProvider):
    """Fallback provider when AI analysis is explicitly unconfigured or disabled."""

    @property
    def name(self) -> str:
        return "none"

    @property
    def model_name(self) -> str:
        return "none"

    @property
    def is_available(self) -> bool:
        return False

    async def generate_analysis(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI review analysis is currently disabled or unconfigured (LLM_PROVIDER='none')",
        )


def get_llm_provider(
    provider_override: Optional[str] = None,
    context: Optional[EvidenceContext] = None,
) -> LLMProvider:
    provider_name = (provider_override or settings.LLM_PROVIDER).lower()

    if provider_name == "mock":
        return MockLLMProvider(context=context)
    elif provider_name == "openai":
        return OpenAILLMProvider()
    elif provider_name == "anthropic":
        return AnthropicLLMProvider()
    elif provider_name == "ollama":
        return OllamaLLMProvider()
    elif provider_name in {"none", "disabled"}:
        return DisabledLLMProvider()
    else:
        # Default safely to MockLLMProvider for robustness
        return MockLLMProvider(context=context)
