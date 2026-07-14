-- Enriches adversarial_attack_logs with payload text, category taxonomy,
-- and full 7-layer pipeline verdict recorded after SSE stream consumption.
ALTER TABLE adversarial_attack_logs
  ADD COLUMN IF NOT EXISTS payload               TEXT,
  ADD COLUMN IF NOT EXISTS attack_category       VARCHAR(100),
  ADD COLUMN IF NOT EXISTS attack_category_group VARCHAR(100),
  ADD COLUMN IF NOT EXISTS pipeline_verdict      VARCHAR(20),
  ADD COLUMN IF NOT EXISTS blocked_by_layer      VARCHAR(50),
  ADD COLUMN IF NOT EXISTS blocked_by_pattern    VARCHAR(20);
