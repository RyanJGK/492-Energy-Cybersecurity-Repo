from __future__ import annotations

import os
import sys
import json
import logging
import psycopg
from typing import Dict, List, Tuple

# Environment variables
# DATABASE_URL: postgres connection string
# ALLOWLIST_JSON: optional JSON list of permitted PII columns

DEFAULT_ALLOWLIST = {
    "public.verification_requests": {"user_id", "email_normalized_hash", "ip", "device_fingerprint"},
    "public.verification_confirmations": {"user_id", "email_normalized_hash", "ip", "device_fingerprint"},
    "public.sign_in_events": {"user_id", "email_normalized_hash", "ip", "device_fingerprint", "mfa_used"},
}

DISALLOWED_PATTERNS = {
    "email_plaintext",
    "phone_number",
    "ssn",
    "credit_card",
    "password",
    "api_key",
    "access_token",
}

logger = logging.getLogger("schema_linter")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def load_allowlist() -> Dict[str, set]:
    raw = os.getenv("ALLOWLIST_JSON")
    if raw:
        try:
            parsed = json.loads(raw)
            return {tbl: set(cols) for tbl, cols in parsed.items()}
        except Exception as exc:
            logger.warning("Invalid ALLOWLIST_JSON; falling back to DEFAULT_ALLOWLIST: %s", exc)
    return {k: set(v) for k, v in DEFAULT_ALLOWLIST.items()}


def fetch_schema(conn) -> List[Tuple[str, str]]:
    # returns list of (table, column)
    sql = """
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY 1,2,3
    """
    rows: List[Tuple[str, str, str]] = []
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return [ (f"{s}.{t}", c) for (s,t,c) in rows ]


def lint() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL env var is required")
        return 2

    allowlist = load_allowlist()

    with psycopg.connect(database_url) as conn:  # type: ignore
        violations: List[str] = []
        findings: List[str] = []
        for table, column in fetch_schema(conn):
            # Disallowed pattern match
            for pat in DISALLOWED_PATTERNS:
                if pat in column:
                    msg = f"Disallowed PII column detected: {table}.{column} matches pattern '{pat}'"
                    violations.append(msg)
                    findings.append(msg)
                    break

            # Allowlist enforcement if table present
            allowed_cols = allowlist.get(table)
            if allowed_cols is not None and column not in allowed_cols:
                msg = f"Column not in allowlist for {table}: {column}"
                violations.append(msg)
                findings.append(msg)

        # Report findings to security team (stdout/CI artifact). Integrate with Slack later.
        report = {"violations": violations, "tables": list(allowlist.keys())}
        print(json.dumps(report, indent=2))

        if violations:
            logger.error("Schema linter found %d violations", len(violations))
            return 1
        logger.info("Schema linter passed with no violations")
        return 0


if __name__ == "__main__":
    sys.exit(lint())
