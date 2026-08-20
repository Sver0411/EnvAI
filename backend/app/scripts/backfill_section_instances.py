"""为 Phase 5 已存在的 DocumentInstance 创建 Phase 6 章节快照。"""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.generation import DocumentInstance, DocumentTemplate
from app.models.workflow import DocumentSectionInstance


def backfill() -> int:
    created = 0
    with SessionLocal() as db:
        instances = list(db.scalars(select(DocumentInstance).where(~DocumentInstance.section_instances.any())))
        for instance in instances:
            template = db.get(DocumentTemplate, instance.template_id)
            if template is None:
                continue
            snapshots: dict[int, DocumentSectionInstance] = {}
            for section in sorted(template.sections, key=lambda item: (item.level, item.sort_order)):
                snapshot = DocumentSectionInstance(document_instance_id=instance.id, template_section_id=section.id, parent_id=snapshots.get(section.parent_id).id if section.parent_id in snapshots else None, section_code=section.section_code, title=section.title, level=section.level, sort_order=section.sort_order, generation_enabled=section.enabled)
                db.add(snapshot); db.flush(); snapshots[section.id] = snapshot; created += 1
            instance.template_version = template.version
        db.commit()
    return created


if __name__ == "__main__":
    print(f"created section snapshots: {backfill()}")
