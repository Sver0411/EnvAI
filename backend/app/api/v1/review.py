from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.generation import DocumentInstance, DocumentTemplate
from app.models.review import ProfessionalReviewRun, QualityScoreResult, ReviewChecklist, ReviewChecklistResult, ReviewIssue, ReviewRuleSet, ReviewTask
from app.models.user import User
from app.schemas.common import Resp
from app.schemas.review import ChecklistCompleteIn, DismissIssueIn, ProfessionalReviewRunOut, QualityGateOut, QualityScoreOut, ReviewChecklistItemOut, ReviewIssueOut, ReviewStartIn
from app.services import generation_service, review_service

router = APIRouter(tags=["review"])

@router.post("/document-instances/{instance_id}/reviews", response_model=Resp[ProfessionalReviewRunOut])
def start_review(instance_id: int, data: ReviewStartIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ProfessionalReviewRunOut]:
    run = review_service.start_review(db, instance_id, current_user, data.mode)
    return Resp(data=ProfessionalReviewRunOut.model_validate(run))

@router.get("/document-instances/{instance_id}/reviews", response_model=Resp[list[ProfessionalReviewRunOut]])
def list_reviews(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ProfessionalReviewRunOut]]:
    instance = generation_service.get_instance(db, instance_id, current_user)
    rows = list(db.scalars(select(ProfessionalReviewRun).where(ProfessionalReviewRun.document_instance_id == instance.id).order_by(ProfessionalReviewRun.id.desc())))
    return Resp(data=[ProfessionalReviewRunOut.model_validate(row) for row in rows])

@router.get("/professional-review-runs/{run_id}", response_model=Resp[ProfessionalReviewRunOut])
def get_review_run(run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ProfessionalReviewRunOut]:
    run = db.scalar(select(ProfessionalReviewRun).join(DocumentInstance).where(ProfessionalReviewRun.id == run_id, DocumentInstance.created_by == current_user.id))
    if run is None: raise NotFoundError("专业审核运行不存在")
    return Resp(data=ProfessionalReviewRunOut.model_validate(run))

@router.get("/document-instances/{instance_id}/review-issues", response_model=Resp[list[ReviewIssueOut]])
def list_review_issues(instance_id: int, severity: str | None = Query(default=None), status: str | None = Query(default=None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ReviewIssueOut]]:
    instance = generation_service.get_instance(db, instance_id, current_user)
    query = select(ReviewIssue).where(ReviewIssue.document_instance_id == instance.id)
    if severity: query = query.where(ReviewIssue.severity == severity)
    if status: query = query.where(ReviewIssue.status == status)
    return Resp(data=[ReviewIssueOut.model_validate(item) for item in db.scalars(query.order_by(ReviewIssue.id.desc()))])

@router.get("/review-issues/{issue_id}", response_model=Resp[ReviewIssueOut])
def get_review_issue(issue_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReviewIssueOut]:
    issue = db.scalar(select(ReviewIssue).join(DocumentInstance).where(ReviewIssue.id == issue_id, DocumentInstance.created_by == current_user.id))
    if issue is None: raise NotFoundError("审核问题不存在")
    return Resp(data=ReviewIssueOut.model_validate(issue))

@router.post("/review-issues/{issue_id}/dismiss", response_model=Resp[ReviewIssueOut])
def dismiss_review_issue(issue_id: int, data: DismissIssueIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReviewIssueOut]:
    return Resp(data=ReviewIssueOut.model_validate(review_service.dismiss_issue(db, issue_id, current_user, data.reason)))

@router.get("/document-instances/{instance_id}/quality-score", response_model=Resp[QualityScoreOut | None])
def quality_score(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[QualityScoreOut | None]:
    instance = generation_service.get_instance(db, instance_id, current_user)
    score = db.scalar(select(QualityScoreResult).where(QualityScoreResult.document_instance_id == instance.id).order_by(QualityScoreResult.id.desc()))
    return Resp(data=QualityScoreOut.model_validate(score) if score else None)

@router.get("/document-instances/{instance_id}/quality-gate", response_model=Resp[QualityGateOut])
def quality_gate(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[QualityGateOut]:
    return Resp(data=QualityGateOut.model_validate(review_service.quality_gate(db, instance_id, current_user)))

@router.get("/document-instances/{instance_id}/review-checklist", response_model=Resp[list[ReviewChecklistItemOut]])
def review_checklist(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ReviewChecklistItemOut]]:
    instance = generation_service.get_instance(db, instance_id, current_user)
    rule_set = db.get(ReviewRuleSet, instance.template.review_rule_set_id) if instance.template.review_rule_set_id else db.scalar(select(ReviewRuleSet).where(ReviewRuleSet.status == "active").order_by(ReviewRuleSet.id))
    if not rule_set: return Resp(data=[])
    latest = db.scalar(select(ProfessionalReviewRun).where(ProfessionalReviewRun.document_instance_id == instance.id).order_by(ProfessionalReviewRun.id.desc()))
    task = db.scalar(select(ReviewTask).where(ReviewTask.review_run_id == latest.id, ReviewTask.scope_type == "document")) if latest else None
    results = {item.check_code: item for item in db.scalars(select(ReviewChecklistResult).where(ReviewChecklistResult.review_task_id == task.id))} if task else {}
    items = list(db.scalars(select(ReviewChecklist).where(ReviewChecklist.rule_set_id == rule_set.id).order_by(ReviewChecklist.sort_order)))
    return Resp(data=[ReviewChecklistItemOut(id=item.id, code=item.code, name=item.name, required=item.required, status=results[item.code].status if item.code in results else "needs_review", message=results[item.code].message if item.code in results else None, reviewed_at=results[item.code].reviewed_at if item.code in results else None) for item in items])

@router.post("/review-checklist-items/{checklist_id}/complete", response_model=Resp[ReviewChecklistItemOut])
def complete_review_checklist(checklist_id: int, data: ChecklistCompleteIn, document_instance_id: int | None = Query(default=None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReviewChecklistItemOut]:
    checklist = db.get(ReviewChecklist, checklist_id)
    if checklist is None: raise NotFoundError("审核清单不存在")
    # 通过最近一次审核运行绑定人工清单；不存在运行时要求先启动审核。
    if document_instance_id is not None:
        instance = generation_service.get_instance(db, document_instance_id, current_user)
        if instance.template.review_rule_set_id != checklist.rule_set_id:
            raise NotFoundError("审核清单不属于该文档")
    else:
        # Backwards-compatible fallback for older clients. New clients should
        # always pass document_instance_id to avoid ambiguity when a user has
        # multiple documents using the same rule set.
        instance = db.scalar(select(DocumentInstance).join(DocumentTemplate, DocumentTemplate.id == DocumentInstance.template_id).join(ProfessionalReviewRun, ProfessionalReviewRun.document_instance_id == DocumentInstance.id).where(DocumentTemplate.review_rule_set_id == checklist.rule_set_id, DocumentInstance.created_by == current_user.id).order_by(ProfessionalReviewRun.id.desc()))
    if instance is None: raise NotFoundError("尚未启动专业审核")
    latest = db.scalar(select(ProfessionalReviewRun).where(ProfessionalReviewRun.document_instance_id == instance.id).order_by(ProfessionalReviewRun.id.desc()))
    if latest is None: raise NotFoundError("尚未启动专业审核")
    task = db.scalar(select(ReviewTask).where(ReviewTask.review_run_id == latest.id, ReviewTask.scope_type == "document"))
    if task is None:
        task = ReviewTask(review_run_id=latest.id, scope_type="document", review_type="human_checklist", status="completed", completed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)); db.add(task); db.flush()
    result = db.scalar(select(ReviewChecklistResult).where(ReviewChecklistResult.review_task_id == task.id, ReviewChecklistResult.check_code == checklist.code))
    if result is None: result = ReviewChecklistResult(review_task_id=task.id, checklist_id=checklist.id, check_code=checklist.code); db.add(result)
    result.status = data.status; result.message = data.message; result.reviewed_by = current_user.id; result.reviewed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc); db.commit()
    return Resp(data=ReviewChecklistItemOut(id=checklist.id, code=checklist.code, name=checklist.name, required=checklist.required, status=result.status, message=result.message, reviewed_at=result.reviewed_at))
