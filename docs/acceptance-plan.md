# EnvAI MVP RC1 Acceptance Plan

## Hard release blockers

- Cross-tenant leakage, key identity error, key numeric modification, fabricated regulation citation and exported internal source marker must each be zero.
- P0 and P1 bugs must be zero.
- Recent PostgreSQL and storage backup restore drill must be recorded.
- Real release configuration must not use Mock AI/Payment, weak secrets or unrestricted CORS.

## Required evidence before external trial

1. 3–10 controlled deidentified projects with expert-confirmed ground truth.
2. Curated and rights-cleared core regulations with verified metadata/version/jurisdiction.
3. Expert scoring sheets for extraction, retrieval, generation, review and Word/PDF output.
4. A manual Microsoft Word/PDF validation record for each active template.
5. Tenant isolation, billing-state and production-security regression reports.
6. Tested alert notification chain, durable queue/worker recovery decision, malware-scanning decision and Platform Admin MFA risk decision.

## Severity

| Severity | Meaning |
|---|---|
| P0 | Cross-tenant leak, irreversible loss, permission bypass or unsafe critical report data |
| P1 | A primary workflow, regulatory grounding or formal export cannot be used |
| P2 | Non-blocking workflow defect with documented workaround |
| P3 | Cosmetic or wording defect |

## Expert score sheet

Score 1–5 with mandatory notes: enterprise facts, terminology, regulation relevance/version, citation support, missing-data behavior, review findings, editable Word quality and overall usability. Mark each item `must change`, `recommended`, `acceptable` or `discussion required`.

