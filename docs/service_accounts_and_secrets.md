# Service Accounts and Secret Management

This document defines service accounts, their permissions, and how secrets are managed and rotated in alignment with NERC CIP, IEC 62443, and NIST SP 800-82 principles.

## Service Accounts

### email-verification-agent
- Purpose: Correlate authentication verification events and raise alerts
- Permissions:
  - Kafka: Read `auth-verification-events`
  - Kafka: Write `alerts`
  - Config: Read-only access to policy thresholds and compliance settings
- Authentication: SASL/SCRAM credentials stored in secret manager
- Consumer Group: `{env}.email-verification-agent.v1`

### email-recording-agent
- Purpose: Ingest historical verification/sign-in records from Postgres for reconciliation
- Permissions:
  - Postgres: Read-only on tables `verification_events`, `sign_in_events`
  - Kafka (optional): Write to `email-delivery-events` if required
- Authentication: DB user with `SELECT` only; no DDL/DML
- Consumer Group: `{env}.email-recording-agent.v1`

### ot-tracking-agent
- Purpose: Observe OT SPAN/TAP traffic and publish normalized frames
- Permissions:
  - Network: Read-only access to SPAN/TAP port traffic
  - Kafka: Write `ot-network-events`
- Authentication: Kafka SASL/SCRAM producer credentials only
- Consumer Group: `{env}.ot-tracking-agent.v1`

## Secret Storage and Access

Preferred secret managers (choose per environment):
- HashiCorp Vault (recommended for lab/staging and on-prem):
  - KV v2 for static secrets
  - Database secrets engine for dynamic DB creds
  - Transit engine for envelope encryption and hashing
- AWS Secrets Manager (cloud environments):
  - Rotation via Lambda
  - KMS CMKs for encryption at rest

### Secret References

- Use URI-like references in configs, e.g. `vault:secret/data/ics/app_db_write` or `aws-sm:prod/ics/slack_webhook`.
- Applications resolve references at startup using sidecar or SDK. Do not store plaintext secrets in repo.

## Rotation Policies

- Database credentials:
  - Dynamic creds (preferred) with TTL 24h; otherwise rotate static creds every 90 days
- Kafka SASL credentials:
  - Rotate every 180 days; decommission old principals after 14-day overlap
- Webhooks and API tokens (Slack/PagerDuty):
  - Rotate every 180 days or upon personnel changes
- PII hashing salt (Transit or secret):
  - Rotate annually with rehash-on-read strategy for live data

## Access Controls and Audit

- Enforce least privilege and environment isolation (lab/staging/prod)
- RBAC: Separate OT, IT, and SOC roles
- Mandatory audit logging of secret reads and config accesses
- Use short-lived tokens (JWT or Vault tokens) for app auth to secret manager

## Compliance Considerations

- PII retention:
  - Auth events: 30 days
  - Email events: 14 days
  - OT events: 7 days
- Encryption:
  - At rest: DB TDE/KMS; Kafka at-rest (disk) where supported
  - In transit: TLS for DB, Kafka (SASL_SSL), secret manager
- Data minimization:
  - Hash PII (emails, user_ids) where possible using `sha256` with salt from secret manager
