CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS telemetry (
  device_id TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL
);

SELECT create_hypertable('telemetry', 'ts', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_ts ON telemetry (device_id, ts DESC);
