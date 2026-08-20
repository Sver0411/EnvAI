from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parsed_document import ParsedDocument


class ParsedDocumentRepository:
    @staticmethod
    def get(db: Session, project_file_id: int, *, for_update: bool = False) -> ParsedDocument | None:
        query = select(ParsedDocument).where(ParsedDocument.project_file_id == project_file_id)
        if for_update:
            query = query.with_for_update()
        return db.scalar(query)

    @staticmethod
    def get_or_create(db: Session, project_file_id: int) -> ParsedDocument:
        document = ParsedDocumentRepository.get(db, project_file_id, for_update=True)
        if document is None:
            document = ParsedDocument(project_file_id=project_file_id)
            db.add(document)
            db.flush()
        return document
