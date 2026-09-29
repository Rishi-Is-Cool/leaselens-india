-- LeaseLens Phase 3 — PostgreSQL statute knowledge base
-- Own corpus/table, separate from lease clauses and classifier output.

CREATE TABLE IF NOT EXISTS statute_entries (
    id TEXT PRIMARY KEY,
    citation TEXT NOT NULL,
    excerpt_text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    jurisdiction TEXT NOT NULL CHECK (jurisdiction IN ('Maharashtra', 'Delhi', 'Central')),
    topic_tags TEXT[] NOT NULL CHECK (cardinality(topic_tags) > 0),
    last_verified_date DATE NOT NULL,
    CONSTRAINT statute_entries_citation_unique UNIQUE (citation)
);

CREATE INDEX IF NOT EXISTS idx_statute_entries_jurisdiction
    ON statute_entries (jurisdiction);

CREATE INDEX IF NOT EXISTS idx_statute_entries_topic_tags
    ON statute_entries USING GIN (topic_tags);

-- Jurisdiction must be selected before retrieval; retrieval code should filter
-- jurisdiction first, then topic_tags, and only explicitly opt into Central.
