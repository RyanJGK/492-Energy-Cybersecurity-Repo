# ICS Security Monitoring Lab

A reference lab for identity/email verification analytics and OT (Industrial Control Systems) network tracking. This repository includes a lightweight rules engine for email verification abuse/fraud signals and an OT traffic collector plus tracking agent that normalizes industrial protocol frames and evaluates baseline/zoning policies. It ships with runnable demos, a docker-compose lab, and example dashboards/detections for SIEM/SOAR.

### Features
- **Email verification analytics**: Token reuse, token expiry, velocity throttling, disposable domain detection, geo-impossible travel, and DMARC alignment checks.
- **OT network tracking**: PCAP-based OT collector (Modbus/DNP3/IEC104/IEC61850) that normalizes frames to `OTProtocolFrame` and streams to Kafka.
- **Behavioral rules for OT**: New master detection, unknown function codes vs baseline, off-schedule writes, out-of-range value alerts, and unauthorized inter-zone flows.
- **Asset and flow baselining**: Simple asset inference and flow statistics to derive polling periods and function/address baselines.
- **Demos and tooling**: CSV replay, synthetic demos, and a privacy scanner for secrets/PII leakage.
- **Docs and integrations**: Lab runbook, service account/secret guidance, example dashboards and detections for Grafana, Elastic, Sentinel, and Splunk.

---

### Installation

Prerequisites:
- Python 3.10+
- Linux: librdkafka for `confluent-kafka`

```bash
# Ubuntu/Debian (for confluent-kafka)
sudo apt-get update && sudo apt-get install -y librdkafka-dev

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
# (Optional) test tools
pip install pytest
```

Docker-based lab (Kafka, Zookeeper, Postgres, Schema Registry, agents):
```bash
docker compose -f docker-compose.lab.yml up -d --build
```

---

### Usage

Run the local demos (no Kafka required):
```bash
# Email verification demo over CSV (prints JSON alerts)
python scripts/demo.py email --csv data/auth_events.csv

# OT tracking synthetic demo (prints JSON alerts)
python scripts/demo.py ot
```

Kafka flows (lab or your cluster):
```bash
# 1) Replay auth verification events from CSV to Kafka
env KAFKA_BROKERS=localhost:9092 \
  python scripts/replay_auth_csv.py data/auth_events.csv

# 2) Run OT collector against a PCAP (publishes OTProtocolFrame)
PCAP_PATH=pcaps/sample_modbus.pcap \
  KAFKA_BROKERS=localhost:9092 \
  python scripts/run_ot_collector.py

# 3) Consume and analyze OT frames (prints alerts)
KAFKA_BROKERS=localhost:9092 \
  python scripts/run_ot_tracking_consumer.py
```

Privacy/secret scanner for log/artifact files:
```bash
python scripts/privacy_scan.py path/to/file1 path/to/file2
```

---

### Configuration and Environment

Environment variables:
- **KAFKA_BROKERS**: Kafka bootstrap servers (default: `localhost:9092`).
- **OT_TOPIC**: Topic for OT frames (default: `ot-network-events`).
- **IFACE**: Network interface for live capture (stubbed; default: `eth0`).
- **PCAP_PATH**: Path to PCAP file for the OT collector (if provided, used instead of live capture).
- **OT_AGENT_DISABLED**: Set to `1` to activate the OT agent kill switch (safety control stub).
- (Optional) **DATABASE_URL**: Used by `email_recording/db.py` if integrating with Postgres.
- (Optional) **ALLOWLIST_JSON**: Used by `email_recording/schema_linter.py` for schema allowlisting.

Config files:
- `config/zones.yaml`: Defines network zones and allowed flows for OT zonal policy (used by demos/agents to flag unauthorized flows).
- `config.yaml`: Example system configuration (kafka, policy thresholds, compliance). Reference for deployment design; not required by demo scripts.
- `kafka_topics.yaml`: Example topic sizing, retention, and naming conventions per environment.

Policy knobs used by the email verification rules (when provided in `cfg`):
- `policy.ip_rate_limits.window_seconds` and `policy.ip_rate_limits.max_auth_requests`
- `policy.token_expiry.email_verification_minutes`

---

### Folder Structure

```text
.
├─ scripts/                     # CLI entry points (demos, replayers, tools)
│  ├─ demo.py                   # Email + OT synthetic demos
│  ├─ replay_auth_csv.py        # Publish CSV auth events to Kafka
│  ├─ run_ot_collector.py       # Run OT collector (PCAP-driven)
│  └─ run_ot_tracking_consumer.py # Consume OT frames and alert
├─ email_verification/          # Rules engine for email verification analytics
│  ├─ agent.py                  # Agent loop and batching
│  ├─ context.py                # Metrics and KV store abstraction
│  ├─ rule_engine.py            # Rule interface and executor
│  └─ rules/                    # TokenReuse, TokenExpiry, Velocity, DisposableDomain, GeoAnomaly, DMARC
├─ ot_collector/                # OT collector + tracking agent
│  ├─ ot_collector.py           # Packet parsing (dpkt) and normalization
│  ├─ ot_tracking_agent.py      # Asset/baseline mgmt + OT rules
│  ├─ asset_manager.py          # Asset inference and flow stats
│  └─ dissectors/               # Modbus, DNP3, IEC104, IEC61850
├─ data/                        # Sample datasets (e.g., auth_events.csv)
├─ config/                      # Example zone config (zones.yaml)
├─ dashboards/                  # Grafana dashboards (example)
├─ elastic/                     # Elastic detections (example)
├─ sentinel/                    # Microsoft Sentinel analytics rules (example)
├─ splunk/                      # Splunk saved searches (example)
├─ sql/                         # DB init or audit query examples
├─ docs/                        # Runbook and deployment guidance
├─ requirements.txt             # Python dependencies
├─ docker-compose.lab.yml       # Lab stack: Kafka/ZK/Postgres/Schema Registry + services
└─ tests/                       # Minimal unit tests for rules/agent
```

---

### Development and Contribution

Run tests locally:
```bash
pip install pytest
pytest -q
```

Code style: readable, typed Python; prefer small, testable units. For substantial changes, include tests in `tests/`.

Contributions: open issues and PRs with a clear problem statement, rationale, and test/usage notes.

---

### Technologies Used
- **Python**: core logic and CLI scripts
- **Kafka**: event streaming (`confluent-kafka` client)
- **dpkt**: packet/PCAP parsing for OT collector
- **PostgreSQL**: example data source for email recording (via `psycopg`)
- **Grafana / Elastic / Sentinel / Splunk**: example dashboards and detections
- **Docker Compose**: reproducible lab environment

---

### Additional Documentation
- Lab runbook: `docs/lab_runbook.md`
- OT collector placement and safety: `docs/ot_collector_placement.md`
- Service accounts and secret management: `docs/service_accounts_and_secrets.md`

### Safety and Data Handling
- OT collection is designed as passive, read-only; no writes back into ICS.
- Follow `docs/service_accounts_and_secrets.md` and `config.yaml` guidance for secrets, PII minimization, and retention.

