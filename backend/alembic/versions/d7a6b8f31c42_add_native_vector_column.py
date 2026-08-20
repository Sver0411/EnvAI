"""store embeddings in native pgvector when the extension is available

Revision ID: d7a6b8f31c42
Revises: c4f1a9e72d10
"""
from alembic import op

revision = "d7a6b8f31c42"
down_revision = "c4f1a9e72d10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
            ALTER TABLE knowledge_chunk_embeddings ADD COLUMN IF NOT EXISTS embedding_vector vector(64);
            CREATE INDEX IF NOT EXISTS ix_knowledge_chunk_embeddings_vector_hnsw
                ON knowledge_chunk_embeddings USING hnsw (embedding_vector vector_cosine_ops);
        END IF;
    END $$;""")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunk_embeddings_vector_hnsw")
    op.execute("ALTER TABLE knowledge_chunk_embeddings DROP COLUMN IF EXISTS embedding_vector")
