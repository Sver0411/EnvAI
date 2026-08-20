from app.db.base import Base  # noqa: F401  确保所有模型注册到 metadata

# 导入模型模块，使表被注册到 Base.metadata
from app.models.company_profile import CompanyProfile  # noqa: F401
from app.models.parsed_document import ParsedDocument  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.project_file import ProjectFile  # noqa: F401
from app.models.structured_data import (  # noqa: F401
    DataConflict,
    EnvironmentalFacility,
    ExtractedFact,
    ExtractionRun,
    Product,
    ProductionEquipment,
    RawMaterial,
)
from app.models.knowledge import (  # noqa: F401
    DocumentRelation,
    KnowledgeBase,
    KnowledgeCategory,
    KnowledgeChunk,
    KnowledgeChunkEmbedding,
    KnowledgeDocument,
    KnowledgeDocumentCategory,
    KnowledgeIndexRun,
)
from app.models.generation import (  # noqa: F401
    DocumentInstance,
    DocumentTemplate,
    GenerationSource,
    SectionCitation,
    SectionDraft,
    SectionDraftVersion,
    SectionGenerationConfig,
    SectionGenerationRun,
    TemplateSection,
)
from app.models.workflow import (  # noqa: F401
    AuditEvent,
    BatchGenerationItem,
    BatchGenerationRun,
    DocumentSectionInstance,
    DocumentValidationIssue,
    DocumentValidationRun,
    SectionDependency,
    SectionReview,
)
from app.models.review import (  # noqa: F401
    ProfessionalReviewRun,
    ProfessionalRule,
    QualityScoreResult,
    ReviewChecklist,
    ReviewChecklistResult,
    ReviewIssue,
    ReviewRuleSet,
    ReviewTask,
)
from app.models.export import (  # noqa: F401
    ExportArtifact,
    ReportExportJob,
    ReportFigure,
    ReportSnapshot,
    ReportTemplate,
    ReportTemplateMapping,
)
from app.models.user import User  # noqa: F401
from app.models.tenant import Organization, OrganizationInvitation, OrganizationMember, Plan, ProjectMember, UsageEvent  # noqa: F401
from app.models.commercial import (  # noqa: F401
    AIModelPricing, BillingAccount, FeatureFlag, OrganizationSubscription, Order,
    PaymentAttempt, PlatformAuditEvent, QuotaAdjustment, SystemAnnouncement, UsageCost,
)
