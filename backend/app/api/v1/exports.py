from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.models.export import ReportSnapshot, ReportTemplate
from app.models.generation import DocumentInstance
from app.models.user import User
from app.schemas.common import Resp
from app.schemas.export import ExportArtifactOut, ExportPreflightOut, ExportStartIn, ReportExportJobOut, ReportFigureIn, ReportFigureOut, ReportSnapshotOut, ReportTemplateOut, SnapshotCreateIn
from app.services import export_service, storage, workflow_service


router = APIRouter(tags=["exports"])


@router.get("/report-templates", response_model=Resp[list[ReportTemplateOut]])
def list_report_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ReportTemplateOut]]:
    return Resp(data=[ReportTemplateOut.model_validate(item) for item in export_service.list_templates(db, current_user)])


@router.post("/report-templates", response_model=Resp[ReportTemplateOut])
def upload_report_template(name: str = Form(...), code: str = Form(...), document_type: str = Form(...), version: str = Form("v1"), document_template_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReportTemplateOut]:
    if Path(file.filename or "").suffix.lower() != ".docx":
        raise ValidationError("报告模板只允许 .docx，禁止 .docm")
    backend = storage.get_storage()
    rel_path = f"report_templates/{current_user.id}/{uuid.uuid4().hex}.docx"
    size = backend.save(rel_path, file, max_bytes=settings.max_report_template_size_mb * 1024 * 1024)
    try:
        template = export_service.create_template(db, name=name, code=code.strip(), document_type=document_type, version=version.strip(), document_template_id=document_template_id, original_file_name=file.filename or "template.docx", stored_path=rel_path, file_size=size, user=current_user)
    except Exception:
        backend.delete(rel_path)
        raise
    return Resp(data=ReportTemplateOut.model_validate(template))


@router.get("/report-templates/{template_id}", response_model=Resp[ReportTemplateOut])
def get_report_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReportTemplateOut]:
    return Resp(data=ReportTemplateOut.model_validate(export_service.get_template(db, template_id, current_user)))


@router.post("/report-templates/{template_id}/validate", response_model=Resp[list[str]])
def validate_report_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[str]]:
    template = export_service.get_template(db, template_id, current_user)
    return Resp(data=export_service.validate_template_file(storage.get_storage().resolve_path(template.storage_path)))


@router.post("/document-instances/{instance_id}/export-preflight", response_model=Resp[ExportPreflightOut])
def run_export_preflight(instance_id: int, report_template_id: int | None = None, is_draft_export: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ExportPreflightOut]:
    return Resp(data=ExportPreflightOut.model_validate(export_service.export_preflight(db, instance_id, current_user, report_template_id, draft=is_draft_export)))


@router.post("/document-instances/{instance_id}/snapshots", response_model=Resp[ReportSnapshotOut])
def create_report_snapshot(instance_id: int, data: SnapshotCreateIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReportSnapshotOut]:
    return Resp(data=ReportSnapshotOut.model_validate(export_service.create_snapshot(db, instance_id, current_user, draft=data.is_draft_export)))


@router.get("/document-instances/{instance_id}/snapshots", response_model=Resp[list[ReportSnapshotOut]])
def list_report_snapshots(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ReportSnapshotOut]]:
    return Resp(data=[ReportSnapshotOut.model_validate(item) for item in export_service.list_snapshots(db, instance_id, current_user)])


@router.get("/report-snapshots/{snapshot_id}", response_model=Resp[ReportSnapshotOut])
def get_report_snapshot(snapshot_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReportSnapshotOut]:
    return Resp(data=ReportSnapshotOut.model_validate(export_service.get_snapshot(db, snapshot_id, current_user)))


@router.post("/report-snapshots/{snapshot_id}/exports", response_model=Resp[ReportExportJobOut])
def start_report_export(snapshot_id: int, data: ExportStartIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReportExportJobOut]:
    return Resp(data=ReportExportJobOut.model_validate(export_service.start_export(db, snapshot_id, data.report_template_id, data.formats, current_user)))


@router.get("/report-export-jobs/{job_id}", response_model=Resp[ReportExportJobOut])
def get_report_export_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReportExportJobOut]:
    return Resp(data=ReportExportJobOut.model_validate(export_service.get_export_job(db, job_id, current_user)))


@router.get("/report-export-jobs/{job_id}/artifacts", response_model=Resp[list[ExportArtifactOut]])
def list_export_artifacts(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ExportArtifactOut]]:
    return Resp(data=[ExportArtifactOut.model_validate(item) for item in export_service.list_artifacts(db, job_id, current_user)])


@router.get("/export-artifacts/{artifact_id}/download")
def download_export_artifact(artifact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> FileResponse:
    artifact = export_service.get_artifact(db, artifact_id, current_user)
    path = storage.get_storage().resolve_path(artifact.storage_path)
    if not path.is_file(): raise NotFoundError("导出文件实体不存在")
    job = export_service.get_export_job(db, artifact.export_job_id, current_user)
    snapshot = db.get(ReportSnapshot, job.report_snapshot_id)
    instance = db.get(DocumentInstance, snapshot.document_instance_id) if snapshot else None
    workflow_service.audit(db, current_user, "artifact_downloaded", instance, metadata={"export_job_id": job.id, "artifact_id": artifact.id})
    db.commit()
    return FileResponse(path, filename=artifact.file_name, media_type=artifact.mime_type)


@router.post("/document-instances/{instance_id}/report-figures", response_model=Resp[ReportFigureOut])
def add_report_figure(instance_id: int, data: ReportFigureIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReportFigureOut]:
    return Resp(data=ReportFigureOut.model_validate(export_service.add_figure(db, instance_id, project_file_id=data.project_file_id, section_instance_id=data.section_instance_id, caption=data.caption, sort_order=data.sort_order, width_inches=data.width_inches, user=current_user)))


@router.get("/document-instances/{instance_id}/report-figures", response_model=Resp[list[ReportFigureOut]])
def list_report_figures(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ReportFigureOut]]:
    return Resp(data=[ReportFigureOut.model_validate(item) for item in export_service.list_figures(db, instance_id, current_user)])
