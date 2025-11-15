# Generated migration for unified JSON storage
# This migration creates a unified table for all JSON documents

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward migration - create unified table
            sql="""
            -- Create unified JSON documents table
            CREATE TABLE IF NOT EXISTS json_documents (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(100) UNIQUE NOT NULL,
                admin_id VARCHAR(100) NOT NULL,
                document_name VARCHAR(255),
                tags TEXT[],
                data JSONB NOT NULL,
                metadata JSONB,
                file_size_bytes BIGINT DEFAULT 0,
                record_count INTEGER DEFAULT 1,
                is_compressed BOOLEAN DEFAULT FALSE,
                compression_ratio FLOAT,
                database_type VARCHAR(20) DEFAULT 'sql',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Indexes for fast queries
            CREATE INDEX IF NOT EXISTS idx_json_docs_doc_id ON json_documents(doc_id);
            CREATE INDEX IF NOT EXISTS idx_json_docs_admin_id ON json_documents(admin_id);
            CREATE INDEX IF NOT EXISTS idx_json_docs_created_at ON json_documents(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_json_docs_db_type ON json_documents(database_type);
            CREATE INDEX IF NOT EXISTS idx_json_docs_tags ON json_documents USING GIN (tags);
            CREATE INDEX IF NOT EXISTS idx_json_docs_data ON json_documents USING GIN (data jsonb_path_ops);

            -- Full-text search support
            ALTER TABLE json_documents ADD COLUMN IF NOT EXISTS search_vector tsvector;
            CREATE INDEX IF NOT EXISTS idx_json_docs_search ON json_documents USING GIN (search_vector);

            -- Function to update search vector
            CREATE OR REPLACE FUNCTION json_documents_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english', COALESCE(NEW.data::text, ''));
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            -- Trigger to auto-update search vector
            DROP TRIGGER IF EXISTS json_documents_search_vector_trigger ON json_documents;
            CREATE TRIGGER json_documents_search_vector_trigger
            BEFORE INSERT OR UPDATE ON json_documents
            FOR EACH ROW EXECUTE FUNCTION json_documents_search_vector_update();

            -- Function to update updated_at timestamp
            CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS trigger AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            -- Trigger to auto-update updated_at
            DROP TRIGGER IF EXISTS update_json_documents_updated_at ON json_documents;
            CREATE TRIGGER update_json_documents_updated_at
            BEFORE UPDATE ON json_documents
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

            COMMENT ON TABLE json_documents IS 'Unified storage for all JSON documents with full-text search support';
            COMMENT ON COLUMN json_documents.data IS 'JSONB column with GIN index for fast queries';
            COMMENT ON COLUMN json_documents.search_vector IS 'Full-text search vector auto-generated from data';
            COMMENT ON COLUMN json_documents.tags IS 'Array of tags for categorization';
            """,

            # Reverse migration - drop table
            reverse_sql="""
            DROP TRIGGER IF EXISTS update_json_documents_updated_at ON json_documents;
            DROP TRIGGER IF EXISTS json_documents_search_vector_trigger ON json_documents;
            DROP FUNCTION IF EXISTS update_updated_at_column();
            DROP FUNCTION IF EXISTS json_documents_search_vector_update();
            DROP TABLE IF EXISTS json_documents CASCADE;
            """
        ),
    ]
