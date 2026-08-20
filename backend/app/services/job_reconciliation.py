from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.export import ReportExportJob
from app.models.generation import SectionGenerationRun
from app.models.knowledge import KnowledgeIndexRun
from app.models.review import ProfessionalReviewRun


class JobReconciliationService:
    """Marks abandoned in-process jobs failed without blindly replaying them."""

    @staticmethod
    def reconcile(db: Session, *, stale_after_minutes: int = 30) -> dict[str, int]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
        changed = {"generation": 0, "review": 0, "index": 0, "export": 0}
        for model, statuses, key in [
            (SectionGenerationRun, {"pending", "retrieving", "generating", "validating"}, "generation"),
            (ProfessionalReviewRun, {"pending", "running"}, "review"),
            (KnowledgeIndexRun, {"running"}, "index"),
            (ReportExportJob, {"pending", "rendering", "docx_completed", "converting_pdf"}, "export"),
        ]:
            rows = db.scalars(select(model).where(model.status.in_(statuses), model.started_at < cutoff)).all()
            for row in rows:
                row.status = "failed"
                if hasattr(row, "error_message"): row.error_message = "任务超时或 Worker 重启，已由 reconciler 标记失败"
                if hasattr(row, "completed_at"): row.completed_at = datetime.now(timezone.utc)
                changed[key] += 1
        db.commit()
        return changed

