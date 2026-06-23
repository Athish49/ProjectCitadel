-- Migration 005: Add damage_classification column to evidence table.
-- Used by the classify_damage tool (Doc 03 §5.2) to read the pre-classified
-- damage label assigned during evidence ingestion / CarDD classification.
ALTER TABLE evidence
    ADD COLUMN IF NOT EXISTS damage_classification VARCHAR(30);
