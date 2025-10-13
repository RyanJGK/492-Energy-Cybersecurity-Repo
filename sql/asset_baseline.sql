-- DDL for asset inventory and baseline tables

CREATE TABLE IF NOT EXISTS asset_inventory (
  asset_id text PRIMARY KEY,
  ip inet,
  mac text,
  role text,
  first_seen timestamptz NOT NULL,
  last_seen timestamptz NOT NULL,
  confidence double precision NOT NULL
);

CREATE TABLE IF NOT EXISTS baseline_allowed (
  id bigserial PRIMARY KEY,
  version int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  src inet NOT NULL,
  dst inet NOT NULL,
  protocol text NOT NULL,
  function_codes text[] NOT NULL,
  address_ranges jsonb,
  typical_period_seconds double precision
);

-- Indexes for lookups
CREATE INDEX IF NOT EXISTS idx_baseline_src_dst_proto ON baseline_allowed(src, dst, protocol);
