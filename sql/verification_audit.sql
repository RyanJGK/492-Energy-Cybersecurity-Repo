-- Verification audit queries for daily job
-- 1. Detect reused tokens
-- Provided pattern: count token confirmations per token hash

-- Example schema assumptions:
-- table verification_requests(token_hash text, user_id text, requested_at timestamptz, ip inet, email text)
-- table verification_confirmations(token_hash text, user_id text, confirmed_at timestamptz, ip inet, email text)

-- Reused tokens: same token_hash confirmed more than once within 24h window
WITH confirmations AS (
  SELECT token_hash, COUNT(*) AS confirmations_count,
         MIN(confirmed_at) AS first_confirmed_at,
         MAX(confirmed_at) AS last_confirmed_at
  FROM verification_confirmations
  WHERE confirmed_at >= NOW() - INTERVAL '24 hours'
  GROUP BY token_hash
)
SELECT * FROM confirmations WHERE confirmations_count > 1;

-- 2. Orphaned confirmations with no matching request
SELECT c.*
FROM verification_confirmations c
LEFT JOIN verification_requests r ON r.token_hash = c.token_hash
WHERE r.token_hash IS NULL
  AND c.confirmed_at >= NOW() - INTERVAL '24 hours';

-- 3. IP/domain velocity bursts (5-minute window)
-- Per IP
SELECT ip, COUNT(*) AS requests_5m
FROM verification_requests
WHERE requested_at >= NOW() - INTERVAL '5 minutes'
GROUP BY ip
HAVING COUNT(*) > 50
ORDER BY requests_5m DESC;

-- Per email domain
SELECT split_part(email, '@', 2) AS domain, COUNT(*) AS requests_5m
FROM verification_requests
WHERE requested_at >= NOW() - INTERVAL '5 minutes'
GROUP BY domain
HAVING COUNT(*) > 200
ORDER BY requests_5m DESC;

-- 4. Unconfirmed tokens older than 24 hours (likely expired)
SELECT r.*
FROM verification_requests r
LEFT JOIN verification_confirmations c ON c.token_hash = r.token_hash
WHERE c.token_hash IS NULL
  AND r.requested_at < NOW() - INTERVAL '24 hours';

-- 5. Log findings to audit_events table for dashboard visibility
-- Example schema: audit_events(id bigserial, created_at timestamptz default now(), category text, severity text, details jsonb)
-- Insert summaries
INSERT INTO audit_events(category, severity, details)
SELECT 'verification_audit', 'medium', jsonb_build_object(
  'reused_tokens', (SELECT COUNT(*) FROM (
      SELECT token_hash FROM verification_confirmations
      WHERE confirmed_at >= NOW() - INTERVAL '24 hours'
      GROUP BY token_hash HAVING COUNT(*) > 1
  ) t),
  'orphaned_confirmations', (SELECT COUNT(*) FROM (
      SELECT c.token_hash FROM verification_confirmations c
      LEFT JOIN verification_requests r ON r.token_hash = c.token_hash
      WHERE r.token_hash IS NULL AND c.confirmed_at >= NOW() - INTERVAL '24 hours'
  ) t),
  'ip_velocity_bursts', (SELECT COUNT(*) FROM (
      SELECT ip FROM verification_requests WHERE requested_at >= NOW() - INTERVAL '5 minutes' GROUP BY ip HAVING COUNT(*) > 50
  ) t),
  'domain_velocity_bursts', (SELECT COUNT(*) FROM (
      SELECT split_part(email, '@', 2) AS domain FROM verification_requests WHERE requested_at >= NOW() - INTERVAL '5 minutes' GROUP BY domain HAVING COUNT(*) > 200
  ) t),
  'unconfirmed_older_24h', (SELECT COUNT(*) FROM (
      SELECT r.token_hash FROM verification_requests r LEFT JOIN verification_confirmations c ON c.token_hash = r.token_hash WHERE c.token_hash IS NULL AND r.requested_at < NOW() - INTERVAL '24 hours'
  ) t)
);
