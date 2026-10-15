import io
import os
import uuid
from datetime import date
from typing import BinaryIO, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.evidence import Evidence, EvidenceAccessPolicy, EvidenceSourceType
from app.parsers.factory import detect_and_validate_format
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.evidence import (
    EvidenceCompletenessResponse,
    EvidenceCreate,
    EvidenceUpdate,
)


class EvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_evidence_by_id(
        self,
        evidence_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> Evidence:
        evidence = await EvidenceRepository.get_by_id(self.db, evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        cycle = await ReviewCycleRepository.get_by_id(self.db, evidence.cycle_id)

        if not self._is_evidence_accessible_to_viewer(evidence, cycle, viewer_id, viewer_role):
            # PRD Section 11: Return 404 when resource disclosure policy requires hiding existence
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        return evidence

    async def list_evidence(
        self,
        cycle_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Evidence]:
        cycle = None
        if cycle_id:
            cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
            if not cycle:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Review cycle with ID '{cycle_id}' not found",
                )

        if employee_id:
            emp = await UserRepository.get_by_id(self.db, employee_id)
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID '{employee_id}' not found",
                )

        items = await EvidenceRepository.list_evidence(
            self.db,
            cycle_id=cycle_id,
            employee_id=employee_id,
            source_type=source_type,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
        )

        # Enforce access policy filtering
        accessible_items = [
            item for item in items if self._is_evidence_accessible_to_viewer(item, cycle, viewer_id, viewer_role)
        ]
        return accessible_items

    async def create_evidence(self, cycle_id: uuid.UUID, evidence_in: EvidenceCreate) -> Evidence:
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        if evidence_in.uploader_id is not None:
            uploader = await UserRepository.get_by_id(self.db, evidence_in.uploader_id)
            if not uploader:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Uploader user with ID '{evidence_in.uploader_id}' not found",
                )

        if evidence_in.employee_id is not None:
            emp = await UserRepository.get_by_id(self.db, evidence_in.employee_id)
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID '{evidence_in.employee_id}' not found",
                )
            if evidence_in.employee_id != cycle.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Employee ID '{evidence_in.employee_id}' does not match review cycle employee ID '{cycle.employee_id}'",
                )

        return await EvidenceRepository.create(self.db, cycle_id, evidence_in)

    async def upload_and_process_file(
        self,
        cycle_id: uuid.UUID,
        upload_file: UploadFile,
        title: Optional[str] = None,
        source_type: Optional[str] = None,
        access_policy: str = EvidenceAccessPolicy.INTERNAL.value,
        source_date: Optional[date] = None,
        uploader_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
    ) -> Evidence:
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        if employee_id is not None:
            emp = await UserRepository.get_by_id(self.db, employee_id)
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID '{employee_id}' not found",
                )
            if employee_id != cycle.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Supplied employee ID '{employee_id}' does not match review cycle employee ID '{cycle.employee_id}'",
                )

        if uploader_id is not None:
            uploader = await UserRepository.get_by_id(self.db, uploader_id)
            if not uploader:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Uploader user with ID '{uploader_id}' not found",
                )

        # Sanitize client filename against path traversal
        raw_filename = upload_file.filename or "uploaded_document"
        filename = os.path.basename(raw_filename).strip() or "uploaded_document"

        # Stream file in chunks while enforcing size limit to prevent memory exhaustion
        total_size = 0
        chunks = []
        chunk_size = 64 * 1024  # 64 KB chunks

        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"File exceeds maximum upload size limit of {settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024):.1f} MB",
                )
            chunks.append(chunk)

        full_content = b"".join(chunks)
        if len(full_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Uploaded file is empty (0 bytes)",
            )

        # Detect format & validate magic bytes
        header_sample = full_content[:1024]
        try:
            detected_format, parser = detect_and_validate_format(
                filename=filename,
                mime_type=upload_file.content_type,
                header_bytes=header_sample,
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(err),
            )

        # Parse document safely using stream
        stream: BinaryIO = io.BytesIO(full_content)
        try:
            parsed_doc = parser.parse(stream, filename=filename)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(err),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Failed to parse document: {exc}",
            )

        # Prepare safe disk storage path under uploads/{cycle_id}/
        cycle_upload_dir = os.path.abspath(os.path.join(settings.UPLOAD_DIR, str(cycle_id)))
        os.makedirs(cycle_upload_dir, exist_ok=True)

        evidence_uuid = uuid.uuid4()
        allowed_extensions = {".pdf", ".docx", ".txt", ".csv", ".md"}
        extracted_ext = os.path.splitext(filename)[1].lower()
        file_ext = extracted_ext if extracted_ext in allowed_extensions else ".bin"
        safe_disk_filename = f"{evidence_uuid}{file_ext}"
        storage_path = os.path.abspath(os.path.join(cycle_upload_dir, safe_disk_filename))

        # Enforce upload directory containment (Path Traversal Protection)
        upload_root = os.path.abspath(settings.UPLOAD_DIR)
        if not storage_path.startswith(upload_root):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid storage destination path",
            )

        # Write file to isolated disk storage
        try:
            with open(storage_path, "wb") as f:
                f.write(full_content)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not persist file to storage: {exc}",
            )

        # Determine title and source_type
        evidence_title = title or parsed_doc.metadata.get("title") or filename
        effective_source_type = source_type or EvidenceSourceType.DOCUMENT_UPLOAD.value

        metadata = {
            "original_filename": filename,
            "detected_format": detected_format,
            "mime_type": upload_file.content_type,
            "file_size_bytes": total_size,
            "word_count": parsed_doc.word_count,
            "char_count": parsed_doc.char_count,
            "page_count": parsed_doc.page_count,
            "snippet": parsed_doc.snippet,
            "parser_metadata": parsed_doc.metadata,
        }

        evidence_create = EvidenceCreate(
            cycle_id=cycle_id,
            employee_id=cycle.employee_id,
            title=evidence_title,
            source_type=effective_source_type,
            storage_reference=storage_path,
            source_date=source_date or date.today(),
            uploader_id=uploader_id,
            metadata_json=metadata,
            access_policy=access_policy,
        )

        try:
            evidence_record = await EvidenceRepository.create(self.db, cycle_id, evidence_create)
            return evidence_record
        except Exception as exc:
            # Clean up orphaned file on disk if DB creation fails
            if os.path.exists(storage_path):
                os.remove(storage_path)
            raise exc

    def _resolve_physical_path(self, storage_reference: Optional[str]) -> Optional[str]:
        if not storage_reference:
            return None
        if os.path.exists(storage_reference):
            return os.path.abspath(storage_reference)
        abs_cwd = os.path.abspath(storage_reference)
        if os.path.exists(abs_cwd):
            return abs_cwd
        upload_root = os.path.abspath(settings.UPLOAD_DIR)
        nested = os.path.join(upload_root, storage_reference.lstrip("/\\"))
        if os.path.exists(nested):
            return nested
        return None

    async def get_evidence_file_path(
        self,
        evidence_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> str:
        evidence = await self.get_evidence_by_id(evidence_id, viewer_id=viewer_id, viewer_role=viewer_role)
        file_path = self._resolve_physical_path(evidence.storage_reference)
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file does not exist on storage for this evidence record",
            )
        return file_path

    async def get_evidence_content_info(
        self,
        evidence_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        evidence = await self.get_evidence_by_id(evidence_id, viewer_id=viewer_id, viewer_role=viewer_role)
        file_path = self._resolve_physical_path(evidence.storage_reference)
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file does not exist on storage for this evidence record",
            )
        metadata = evidence.metadata_json or {}
        original_filename = metadata.get("original_filename", f"{evidence.id}.bin")
        mime_type = metadata.get("mime_type") or metadata.get("detected_mime") or "application/octet-stream"
        return file_path, original_filename, mime_type

    async def get_cycle_evidence_completeness(
        self,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> EvidenceCompletenessResponse:
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        all_items = await EvidenceRepository.list_all_for_cycle(self.db, cycle_id)
        accessible_items = [
            item for item in all_items if self._is_evidence_accessible_to_viewer(item, cycle, viewer_id, viewer_role)
        ]

        total_count = len(accessible_items)
        distribution: Dict[str, int] = {}
        dated_items: List[date] = []
        out_of_period_count = 0

        for item in accessible_items:
            distribution[item.source_type] = distribution.get(item.source_type, 0) + 1
            if item.source_date:
                dated_items.append(item.source_date)
                if item.source_date < cycle.period_start or item.source_date > cycle.period_end:
                    out_of_period_count += 1

        earliest_date = min(dated_items) if dated_items else None
        latest_date = max(dated_items) if dated_items else None

        period_span_days = max(1, (cycle.period_end - cycle.period_start).days + 1)
        evidence_span_days = (latest_date - earliest_date).days + 1 if (earliest_date and latest_date) else 0

        # Detect gaps and recency concentration risks
        detected_gaps: List[str] = []
        has_recency_bias = False

        if total_count == 0:
            detected_gaps.append("No evidence records attached to this review cycle")
        else:
            # Check for code/PR delivery evidence
            has_code = any(
                st in distribution
                for st in (
                    EvidenceSourceType.PULL_REQUEST.value,
                    EvidenceSourceType.PR.value,
                    EvidenceSourceType.COMMIT.value,
                    EvidenceSourceType.COMMIT_SUMMARY.value,
                    EvidenceSourceType.TICKET.value,
                )
            )
            if not has_code:
                detected_gaps.append("Missing code delivery records (no pull requests, commits, or tickets)")

            # Check for design docs / RFCs
            has_design = any(
                st in distribution
                for st in (
                    EvidenceSourceType.DESIGN_DOC.value,
                    EvidenceSourceType.DOCUMENT.value,
                    EvidenceSourceType.DOCUMENT_UPLOAD.value,
                )
            )
            if not has_design:
                detected_gaps.append("Missing technical design documentation or architecture RFCs")

            # Check out of period dates
            if out_of_period_count > 0:
                detected_gaps.append(
                    f"{out_of_period_count} evidence items are dated outside the review cycle period ({cycle.period_start} to {cycle.period_end})"
                )

            # Check for recency concentration (if all dated evidence is strictly in the last 25% of the cycle)
            if earliest_date and period_span_days > 30:
                cutoff_start = cycle.period_start + (cycle.period_end - cycle.period_start) * 0.75
                if earliest_date >= cutoff_start:
                    has_recency_bias = True
                    detected_gaps.append(
                        "Recency concentration risk: all dated evidence falls exclusively within the final 25% of the review period"
                    )

        # Calculate a normalized completeness score (0.0 to 1.0)
        score = 0.0
        if total_count > 0:
            score += 0.3  # Base evidence presence
            if len(distribution) >= 2:
                score += 0.3  # Diversity of sources
            elif len(distribution) == 1:
                score += 0.15
            if not has_recency_bias and evidence_span_days > (period_span_days * 0.3):
                score += 0.2  # Temporal coverage across the cycle
            if out_of_period_count == 0:
                score += 0.2  # Well-scoped dates
        score = round(min(1.0, max(0.0, score)), 2)

        return EvidenceCompletenessResponse(
            cycle_id=cycle_id,
            employee_id=cycle.employee_id,
            period_start=cycle.period_start,
            period_end=cycle.period_end,
            total_evidence_count=total_count,
            source_distribution=distribution,
            earliest_evidence_date=earliest_date,
            latest_evidence_date=latest_date,
            period_span_days=period_span_days,
            evidence_span_days=evidence_span_days,
            detected_gaps=detected_gaps,
            has_recency_bias_risk=has_recency_bias,
            completeness_score=score,
        )

    async def update_evidence(
        self,
        evidence_id: uuid.UUID,
        evidence_in: EvidenceUpdate,
        viewer_id: Optional[uuid.UUID] = None,
    ) -> Evidence:
        evidence = await EvidenceRepository.get_by_id(self.db, evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        if viewer_id is not None and evidence.uploader_id is not None and evidence.uploader_id != viewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the uploader or an authorized reviewer may update this evidence",
            )

        return await EvidenceRepository.update(self.db, evidence, evidence_in)

    async def delete_evidence(
        self,
        evidence_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
    ) -> None:
        evidence = await EvidenceRepository.get_by_id(self.db, evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        if viewer_id is not None and evidence.uploader_id is not None and evidence.uploader_id != viewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the uploader or an authorized reviewer may delete this evidence",
            )

        # Unlink physical file if present
        if evidence.storage_reference and os.path.exists(evidence.storage_reference):
            try:
                os.remove(evidence.storage_reference)
            except OSError:
                pass

        await EvidenceRepository.delete(self.db, evidence)

    @staticmethod
    def _is_evidence_accessible_to_viewer(
        evidence: Evidence,
        cycle: Optional[object],
        viewer_id: Optional[uuid.UUID],
        viewer_role: Optional[str],
    ) -> bool:
        # Administrator can inspect all evidence
        if viewer_role in {"admin", "administrator"}:
            return True

        # Uploader can always access their uploaded evidence
        if viewer_id is not None and evidence.uploader_id == viewer_id:
            return True

        # Manager role can inspect evidence within managerial scope
        if viewer_role == "manager":
            return True

        # Cycle owner (manager / reviewer) can inspect evidence
        if cycle is not None and hasattr(cycle, "owner_id") and cycle.owner_id == viewer_id:
            return True

        # If evidence is manager-only, restricted, or confidential, employee/public viewer cannot access
        if evidence.access_policy != EvidenceAccessPolicy.INTERNAL.value:
            return False

        # For INTERNAL evidence:
        # If viewer_id is specified, strictly enforce cycle participant / cross-employee isolation
        if viewer_id is not None and cycle is not None:
            # Must be the subject employee or cycle owner or uploader
            if cycle.employee_id == viewer_id or getattr(cycle, "owner_id", None) == viewer_id:
                return True
            # Cross-employee access: unrelated employee has no access
            return False

        # If no viewer_id specified, allow internal evidence (backward compatibility for unauthenticated queries)
        return True
