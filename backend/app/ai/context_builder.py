import os
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.evidence import Evidence
from app.models.review_cycle import ReviewCycle
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.user_repository import UserRepository
from app.services.evidence_service import EvidenceService


@dataclass
class EvidenceContext:
    cycle: ReviewCycle
    employee_name: str
    evidence_items: List[Evidence]
    valid_evidence_ids: Set[uuid.UUID]
    source_distribution: Dict[str, int]
    completeness_score: float
    detected_gaps: List[str]
    prompt_context_text: str
    total_characters: int
    truncated: bool = False
    metadata: Dict[str, object] = field(default_factory=dict)


class EvidenceContextBuilder:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.evidence_service = EvidenceService(db)

    async def build_context(
        self,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        source_type_filter: Optional[str] = None,
        max_items: Optional[int] = None,
        max_chars: Optional[int] = None,
    ) -> EvidenceContext:
        limit_items = max_items or settings.LLM_MAX_EVIDENCE_ITEMS
        limit_chars = max_chars or settings.LLM_MAX_CONTEXT_CHARS

        # 1. Validate Review Cycle existence
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        # 2. Validate Employee existence and association
        employee = await UserRepository.get_by_id(self.db, cycle.employee_id)
        employee_name = employee.full_name if employee else "Subject Employee"

        # 3. Retrieve all evidence items strictly for this cycle
        all_cycle_evidence = await EvidenceRepository.list_all_for_cycle(self.db, cycle_id)

        # 4. Enforce viewer access policies and cross-employee isolation
        accessible_items = [
            item
            for item in all_cycle_evidence
            if self.evidence_service._is_evidence_accessible_to_viewer(item, cycle, viewer_id, viewer_role)
        ]

        # 5. Apply optional source_type filter
        if source_type_filter:
            accessible_items = [
                item for item in accessible_items if item.source_type.lower() == source_type_filter.lower()
            ]

        # 6. Compute completeness metrics & gap detection via EvidenceService
        completeness = await self.evidence_service.get_cycle_evidence_completeness(
            cycle_id=cycle_id,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
        )

        # 7. Bound items to prevent unbounded context
        scoped_items = accessible_items[:limit_items]
        valid_ids: Set[uuid.UUID] = {item.id for item in scoped_items}

        # 8. Construct formatted prompt blocks with prompt-injection isolation
        document_blocks: List[str] = []
        total_chars = 0
        is_truncated = len(accessible_items) > limit_items

        for item in scoped_items:
            doc_snippet = ""
            meta = item.metadata_json or {}
            # Prioritize snippet or text extracted during Phase 4 parsing
            if "snippet" in meta and meta["snippet"]:
                doc_snippet = meta["snippet"]
            elif "text_snippet" in meta and meta["text_snippet"]:
                doc_snippet = meta["text_snippet"]
            elif getattr(item, "summary", None):
                doc_snippet = getattr(item, "summary")
            else:
                # If physical file exists and is text, read bounded sample safely
                if item.storage_reference and os.path.exists(item.storage_reference):
                    try:
                        with open(item.storage_reference, "r", encoding="utf-8", errors="replace") as f:
                            doc_snippet = f.read(1000)
                    except Exception:
                        doc_snippet = f"[Storage reference: {os.path.basename(item.storage_reference)}]"
                else:
                    doc_snippet = f"[Evidence registered: {item.title}]"

            # Clean snippet of control characters
            clean_snippet = doc_snippet.replace("<", "&lt;").replace(">", "&gt;").strip()
            block_text = (
                f'<untrusted_evidence_document id="{item.id}" source="{item.source_type}" '
                f'date="{item.source_date or "unknown"}" title="{item.title}">\n'
                f"{clean_snippet}\n"
                f"</untrusted_evidence_document>"
            )

            if total_chars + len(block_text) > limit_chars:
                is_truncated = True
                break

            document_blocks.append(block_text)
            total_chars += len(block_text)

        formatted_context_text = "\n\n".join(document_blocks)

        return EvidenceContext(
            cycle=cycle,
            employee_name=employee_name,
            evidence_items=scoped_items,
            valid_evidence_ids=valid_ids,
            source_distribution=completeness.source_distribution,
            completeness_score=completeness.completeness_score,
            detected_gaps=completeness.detected_gaps,
            prompt_context_text=formatted_context_text,
            total_characters=total_chars,
            truncated=is_truncated,
            metadata={
                "total_accessible": len(accessible_items),
                "included_in_context": len(document_blocks),
                "period_start": cycle.period_start.isoformat(),
                "period_end": cycle.period_end.isoformat(),
            },
        )
