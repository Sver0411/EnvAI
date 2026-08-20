"""Seed a complete local demo project and an export-ready report instance."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.export import ReportTemplate, ReportTemplateMapping
from app.models.generation import (
    DocumentInstance,
    DocumentTemplate,
    GenerationSource,
    SectionCitation,
    SectionDraft,
    SectionDraftVersion,
    SectionGenerationRun,
)
from app.models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.review import ProfessionalReviewRun, QualityScoreResult
from app.models.structured_data import EnvironmentalFacility, ExtractionRun, Product, ProductionEquipment, RawMaterial
from app.models.user import User
from app.models.workflow import DocumentSectionInstance, SectionReview


PROJECT_ID = 6
INSTANCE_ID = 8
USER_ID = 2


SECTION_CONTENT = {
    "1": """本项目建设单位为江苏清源新材料有限公司，项目名称为年产 2 万吨水性树脂及配套环保设施提升项目。项目位于江苏省苏州市吴中区环保产业园清源路 18 号，占地面积 18,600 m²，建筑面积 12,400 m²。项目主要产品为水性丙烯酸树脂和水性聚氨酯树脂，设计年产量为 20,000 t/a。\n\n项目所在园区具备道路、供水、供电和污水集中处理等基础条件。建设内容包括生产车间、原料仓库、成品仓库、废气治理区、污水处理站和危废暂存间。企业已确认本项目按环保设施与主体工程同时设计、同时施工、同时投产的原则组织建设。""",
    "2": """项目生产工艺包括原辅材料配料、反应、冷却、过滤和灌装。主要生产设备包括反应釜 6 台、过滤器 4 台、灌装线 2 条和冷却系统 1 套。丙烯酸、异氰酸酯和乙酸乙酯分别储存在甲类仓库 A、B、C 区，最大储存量分别为 2.0 t、1.5 t 和 3.0 t。\n\n生产过程中产生的主要污染物包括有机废气、设备清洗废水、废活性炭、废包装材料和设备噪声。生产废水经厂内污水处理站预处理后接管园区污水处理厂；一般固废分类收集，危险废物暂存于危废库并委托有资质单位处置。""",
    "3": """项目所在区域环境空气、地表水和声环境执行现行环境质量标准。项目周边以工业企业和园区道路为主，最近居民敏感点位于项目东南侧约 420 m。企业应在施工和运营阶段加强厂界噪声、废气收集和污水接管管理，避免对周边环境保护目标产生不利影响。\n\n本项目环境保护目标包括区域环境空气质量、园区污水处理系统、周边地表水体以及东南侧居民点。后续监测应按照排污许可和环评批复要求执行，并保存原始监测记录。""",
    "4": """有机废气通过密闭投料、反应釜呼吸口和灌装点收集，收集系统保持负压运行，废气经活性炭吸附浓缩与催化燃烧装置处理后通过 15 m 排气筒排放。该措施与项目有机废气产生环节相匹配，能够减少无组织排放。\n\n生产废水经厂内污水处理站预处理后接管园区污水处理厂。污水站处理能力为 300 m³/d，企业应建立 pH、流量和运行药剂台账。废活性炭、废包装材料和其他危险废物分类暂存，危废库采取防渗、防雨和防扩散措施。综合分析，项目拟采取的污染防治措施具有技术可行性和管理可操作性。""",
    "5": """项目环境风险物质主要包括丙烯酸、异氰酸酯、乙酸乙酯和天然气。风险类型包括泄漏、火灾、爆炸、腐蚀和有毒有害物质扩散。甲类仓库设置分区储存、围堰、禁火和防静电措施，天然气管道设置可燃气体报警和紧急切断装置。\n\n发生泄漏时，应立即停止相关作业并切断物料来源，设置警戒区，由经过培训的人员佩戴防护装备使用吸附棉和堵漏工具处置。发生火灾爆炸时，应启动消防和人员疏散程序，切断气源和电源，并根据风向和影响范围向园区管委会报告。企业配置 600 m³ 消防水池、应急物资柜和应急通讯设备，建议每年组织至少一次综合演练。""",
    "6": """综上，本项目建设内容、生产工艺和污染防治设施与企业确认的项目资料基本一致。通过落实废气收集处理、污水预处理、危险废物规范化管理和环境风险防控措施，项目正常运行对区域环境的影响可控制在可接受范围内。\n\n建议企业持续完善环保设施运行台账、危废转移联单和应急演练记录，定期检查废气治理设施、污水处理站、仓库围堰和可燃气体报警装置。项目投产前应完成相关环保手续和岗位培训，投产后按规定开展自行监测和环境管理。""",
}


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    db = SessionLocal()
    try:
        project = db.get(Project, PROJECT_ID)
        instance = db.get(DocumentInstance, INSTANCE_ID)
        user = db.get(User, USER_ID)
        if not project or not instance or not user:
            raise RuntimeError("演示项目、报告实例或 admin 用户不存在")

        project.status = "reviewing"
        instance.status = "ready_for_export"

        # Confirmed structured facts used by report tables and readiness checks.
        if not db.scalar(select(Product).where(Product.project_id == PROJECT_ID)):
            db.add_all([
                Product(project_id=PROJECT_ID, name="水性丙烯酸树脂", annual_capacity=Decimal("12000"), unit="t/a", specification="工业级", verification_status="user_verified", updated_by=USER_ID),
                Product(project_id=PROJECT_ID, name="水性聚氨酯树脂", annual_capacity=Decimal("8000"), unit="t/a", specification="工业级", verification_status="user_verified", updated_by=USER_ID),
            ])
        if not db.scalar(select(ProductionEquipment).where(ProductionEquipment.project_id == PROJECT_ID)):
            db.add_all([
                ProductionEquipment(project_id=PROJECT_ID, name="反应釜", model="R-5000", quantity=Decimal("6"), unit="台", power=Decimal("45"), power_unit="kW", location="生产车间", verification_status="user_verified", updated_by=USER_ID),
                ProductionEquipment(project_id=PROJECT_ID, name="过滤器", model="F-200", quantity=Decimal("4"), unit="台", power=Decimal("7.5"), power_unit="kW", location="生产车间", verification_status="user_verified", updated_by=USER_ID),
            ])
        if not db.scalar(select(RawMaterial).where(RawMaterial.project_id == PROJECT_ID)):
            db.add_all([
                RawMaterial(project_id=PROJECT_ID, name="丙烯酸", annual_usage=Decimal("1800"), annual_usage_unit="t/a", max_storage=Decimal("2.0"), storage_unit="t", storage_location="甲类仓库 A 区", cas_number="79-10-7", physical_state="液体", hazardous=True, risk_material=True, verification_status="user_verified", updated_by=USER_ID),
                RawMaterial(project_id=PROJECT_ID, name="异氰酸酯", annual_usage=Decimal("1200"), annual_usage_unit="t/a", max_storage=Decimal("1.5"), storage_unit="t", storage_location="甲类仓库 B 区", physical_state="液体", hazardous=True, risk_material=True, verification_status="user_verified", updated_by=USER_ID),
                RawMaterial(project_id=PROJECT_ID, name="乙酸乙酯", annual_usage=Decimal("900"), annual_usage_unit="t/a", max_storage=Decimal("3.0"), storage_unit="t", storage_location="甲类仓库 C 区", cas_number="141-78-6", physical_state="液体", hazardous=True, risk_material=True, verification_status="user_verified", updated_by=USER_ID),
            ])
        if not db.scalar(select(EnvironmentalFacility).where(EnvironmentalFacility.project_id == PROJECT_ID)):
            db.add_all([
                EnvironmentalFacility(project_id=PROJECT_ID, name="活性炭吸附浓缩与催化燃烧装置", facility_type="waste_gas", quantity=Decimal("1"), unit="套", treatment_target="有机废气", capacity=Decimal("12000"), capacity_unit="m³/h", location="废气治理区", verification_status="user_verified", updated_by=USER_ID),
                EnvironmentalFacility(project_id=PROJECT_ID, name="厂内污水处理站", facility_type="wastewater", quantity=Decimal("1"), unit="套", treatment_target="生产废水", capacity=Decimal("300"), capacity_unit="m³/d", location="厂区东侧", verification_status="user_verified", updated_by=USER_ID),
            ])
        db.flush()

        # Mark the two uploaded source documents as parsed facts in the UI.
        files = list(db.scalars(select(ProjectFile).where(ProjectFile.project_id == PROJECT_ID).order_by(ProjectFile.id)))
        if files:
            extraction = db.scalar(select(ExtractionRun).where(ExtractionRun.project_id == PROJECT_ID).order_by(ExtractionRun.id.desc()))
            if extraction is None:
                extraction = ExtractionRun(project_id=PROJECT_ID, status="completed", schema_version="v1", files_count=len(files), facts_count=12, conflicts_count=0, extractor_version="demo-seed-v1", prompt_version="structured-v1", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc), started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc))
                db.add(extraction)

        # Small private knowledge set, with traceable chunks for the report appendix.
        kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.name == "清源项目演示依据库", KnowledgeBase.created_by == USER_ID))
        if kb is None:
            kb = KnowledgeBase(name="清源项目演示依据库", description="用于演示本地 RAG 检索与报告引用。", scope="private", status="active", created_by=USER_ID, organization_id=project.organization_id)
            db.add(kb)
            db.flush()
        docs = list(db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb.id).order_by(KnowledgeDocument.id)))
        if not docs:
            docs = [
                KnowledgeDocument(knowledge_base_id=kb.id, title="建设项目环境保护管理条例（演示摘录）", document_type="regulation", document_number="DEMO-ENV-001", issuing_authority="演示依据库", version="2026", status="active", original_file_name="demo-regulation.txt", storage_path="knowledge/demo-regulation.txt", mime_type="text/plain", file_size=500, sha256=sha("demo-regulation"), language="zh", country="中国", province="江苏省", city="苏州市", source_authority="user", parser_status="parsed", index_status="indexed", parser_name="demo-seed", parser_version="v1", parsed_text="建设项目应落实污染防治设施和环境风险防控要求。", created_by=USER_ID),
                KnowledgeDocument(knowledge_base_id=kb.id, title="挥发性有机物治理技术要求（演示摘录）", document_type="technical_guideline", document_number="DEMO-HJ-002", issuing_authority="演示依据库", version="2026", status="active", original_file_name="demo-voc-guideline.txt", storage_path="knowledge/demo-voc-guideline.txt", mime_type="text/plain", file_size=500, sha256=sha("demo-voc-guideline"), language="zh", country="中国", province="江苏省", city="苏州市", source_authority="user", parser_status="parsed", index_status="indexed", parser_name="demo-seed", parser_version="v1", parsed_text="有机废气应优先采用密闭收集和高效治理设施。", created_by=USER_ID),
            ]
            db.add_all(docs)
            db.flush()
            for index, document in enumerate(docs):
                text = document.parsed_text or ""
                db.add(KnowledgeChunk(knowledge_document_id=document.id, chunk_index=0, content=text, content_type="paragraph", section_title="演示条款", section_level=1, section_path=["演示条款"], article_number="1", token_count=len(text), character_count=len(text), content_hash=sha(text), chunk_fingerprint=sha(f"{document.id}:{text}"), embedding_status="embedded"))
            db.flush()
        chunks = list(db.scalars(select(KnowledgeChunk).join(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb.id).order_by(KnowledgeChunk.id)))

        # Create approved section drafts and review records.
        sections = list(db.scalars(select(DocumentSectionInstance).where(DocumentSectionInstance.document_instance_id == INSTANCE_ID).order_by(DocumentSectionInstance.sort_order)))
        for section in sections:
            draft = db.scalar(select(SectionDraft).where(SectionDraft.document_instance_id == INSTANCE_ID, SectionDraft.section_id == section.template_section_id))
            if draft is None:
                run = SectionGenerationRun(project_id=PROJECT_ID, document_instance_id=INSTANCE_ID, section_id=section.template_section_id, status="completed", ai_provider="openai_compatible", model="deepseek-v4-flash", prompt_version="section-v1", input_tokens=1250, output_tokens=420, project_fact_count=18, project_source_count=2, knowledge_source_count=2, generation_ms=8200, total_duration_ms=9000, started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc))
                db.add(run)
                db.flush()
                citations = [
                    {"source_id": "P001", "claim": "企业名称和项目地址来自已确认企业资料。"},
                    {"source_id": "F001", "claim": "项目生产工艺和环保管理要求来自企业资料汇编。"},
                    {"source_id": "K001", "claim": "污染防治和环境管理要求来自演示依据库。"},
                ]
                draft = SectionDraft(project_id=PROJECT_ID, document_instance_id=INSTANCE_ID, template_id=instance.template_id, section_id=section.template_section_id, generation_run_id=run.id, content=SECTION_CONTENT.get(section.section_code, "本章节暂无内容。"), ai_original_content=SECTION_CONTENT.get(section.section_code, "本章节暂无内容。"), status="approved", version=1, citations=citations, missing_information=[], warnings=[], generation_metadata={"provider": "openai_compatible", "model": "deepseek-v4-flash", "prompt_version": "section-v1", "demo_seed": True}, created_by=USER_ID)
                db.add(draft)
                db.flush()
                version = SectionDraftVersion(draft_id=draft.id, version=1, content=draft.content, status="approved", saved_by=USER_ID)
                db.add(version)
                db.flush()
                for order, (source_type, source_id, context_id, claim) in enumerate((("project_fact", 1, "P001", "企业确认的基本信息"), ("project_document", files[0].id if files else 0, "F001", "企业资料汇编"), ("knowledge_chunk", chunks[0].id if chunks else 0, "K001", "演示依据库条款")), 1):
                    if source_id:
                        db.add(SectionCitation(section_draft_id=draft.id, generation_run_id=run.id, source_type=source_type, source_id=source_id, context_source_id=context_id, claim_text=claim, citation_order=order))
                section.current_draft_id = draft.id
                section.approved_version_id = version.id
                section.status = "approved"
                section.blocked_reason = None
                db.add(SectionReview(section_instance_id=section.id, draft_version_id=version.id, reviewer_id=USER_ID, status="approved", comment="演示项目已完成专业审核。"))
            else:
                section.status = "approved"
        db.flush()

        review = db.scalar(select(ProfessionalReviewRun).where(ProfessionalReviewRun.document_instance_id == INSTANCE_ID).order_by(ProfessionalReviewRun.id.desc()))
        if review is None:
            review = ProfessionalReviewRun(document_instance_id=INSTANCE_ID, status="completed", review_mode="full", rule_set_version="v1", issues_count=0, critical_count=0, major_count=0, minor_count=0, ai_calls=0, started_by=USER_ID, started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc))
            db.add(review)
            db.flush()
        score = db.scalar(select(QualityScoreResult).where(QualityScoreResult.document_instance_id == INSTANCE_ID, QualityScoreResult.review_run_id == review.id))
        if score is None:
            db.add(QualityScoreResult(document_instance_id=INSTANCE_ID, review_run_id=review.id, overall_score=96, data_integrity_score=98, citation_score=95, coverage_score=96, completeness_score=95, consistency_score=96, critical_issue_count=0, major_issue_count=0, quality_passed=True))
        db.commit()
        print(f"demo_project_id={PROJECT_ID} demo_instance_id={INSTANCE_ID} knowledge_base_id={kb.id} sections={len(sections)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
