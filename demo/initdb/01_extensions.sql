-- Enable extensions strongly recommended for better search results.
-- The pg_trgm extension provides fuzzy string matching, and unaccent helps with diacritics.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
