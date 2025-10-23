# ICS Security Monitoring System

**Real-time security monitoring for energy sector Industrial Control Systems (ICS) and authentication infrastructure**

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()
[![Compliance](https://img.shields.io/badge/Compliance-NERC_CIP%20%7C%20IEC_62443%20%7C%20NIST_SP_800--82-green.svg)]()

---

## 📘 Overview

This project provides a **production-grade security monitoring platform** designed for critical energy infrastructure. It combines **IT security** (authentication fraud detection) with **OT security** (industrial protocol monitoring) in a unified, Kafka-based event streaming architecture.

### Key Capabilities

- **🔐 Authentication Security Agent** – Detects credential abuse, token reuse, velocity attacks, geo anomalies, and disposable domains
- **⚙️ OT Protocol Monitoring** – Deep packet inspection for Modbus, DNP3, IEC 61850, IEC 104 protocols
- **🚨 Real-time Alerting** – Multi-severity alerts with Slack, PagerDuty, and SIEM integrations
- **📊 SIEM Integration** – Pre-built dashboards and correlation rules for Elastic, Splunk, Sentinel, and Grafana
- **✅ Compliance-Ready** – Enforces NERC CIP, IEC 62443, NIST SP 800-82 requirements including PII retention, audit logging, and data governance

---

## 🧩 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Data Sources                            │
├─────────────────┬────────────────────┬──────────────────────────┤
│  Auth Events    │  OT Network Taps   │  Email Delivery Events   │
│  (Kafka Topic)  │  (PCAP/SPAN)       │  (Database/Kafka)        │
└────────┬────────┴──────────┬─────────┴──────────┬───────────────┘
         │                   │                     │
         ▼                   ▼                     ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Email Verif.    │  │ OT Tracking      │  │ Email Recording  │
│ Agent           │  │ Agent            │  │ Agent            │
│                 │  │                  │  │                  │
│ • Token Reuse   │  │ • New Masters    │  │ • Bounce Detect  │
│ • Velocity      │  │ • Unknown Func   │  │ • Privacy Scan   │
│ • Geo Anomaly   │  │ • Zonal Flow     │  │                  │
│ • Disposables   │  │ • Safety Range   │  │                  │
└────────┬────────┘  └────────┬─────────┘  └────────┬───────────┘
         │                    │                      │
         └────────────────────┴──────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  Alerts Topic   │
                     │  (Kafka)        │
                     └────────┬────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌───────────┐  ┌────────────┐  ┌──────────────┐
       │  Elastic  │  │   Splunk   │  │   Grafana    │
       │ Detection │  │ Correlation│  │  Dashboards  │
       └───────────┘  └────────────┘  └──────────────┘
```

---

## ⚙️ Installation

### Prerequisites

- **Python 3.13+**
- **Docker & docker-compose** (for lab environment)
- **Kafka cluster** (or use local Docker)
- **PostgreSQL 16+** (for state persistence)

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd ics-security-monitoring
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the template configuration and fill in secrets:

```bash
cp config.yaml config.local.yaml
# Edit config.local.yaml with your environment-specific settings
# Use Vault or secret manager references instead of inline passwords
```

### 3. Set Up Infrastructure (Lab Mode)

For local testing with Docker:

```bash
docker compose -f docker-compose.lab.yml up -d --build
```

This starts:
- Kafka + Zookeeper
- PostgreSQL with schema initialization
- Schema Registry
- Email verification agent
- OT collector

### 4. Initialize Kafka Topics

```bash
docker exec -it $(docker ps -q -f name=kafka) kafka-topics \
  --bootstrap-server kafka:9092 \
  --create --topic auth-verification-events \
  --partitions 12 --replication-factor 1

docker exec -it $(docker ps -q -f name=kafka) kafka-topics \
  --bootstrap-server kafka:9092 \
  --create --topic ot-network-events \
  --partitions 24 --replication-factor 1
```

See `kafka_topics.yaml` for full topic configuration across environments.

---

## 🚀 Usage

### Running the Email Verification Agent

```python
from email_verification.agent import EmailVerificationAgent
from email_verification.rules.velocity import VelocityRule
from email_verification.rules.token_reuse import TokenReuseRule
from email_verification.context import KVStore

rules = [VelocityRule(), TokenReuseRule()]
cfg = {
    "policy": {
        "ip_rate_limits": {"window_seconds": 300, "max_auth_requests": 50}
    }
}

agent = EmailVerificationAgent(
    consumer=kafka_consumer,  # Your Kafka consumer
    rules=rules,
    cfg=cfg,
    kv=KVStore()
)

agent.run()  # Runs indefinitely until SIGTERM/SIGINT
```

### Running the OT Tracking Agent

```python
from ot_collector.ot_tracking_agent import OTTrackingAgent
from schemas import OTProtocolFrame

agent = OTTrackingAgent()
agent.load_baseline([
    ("10.10.0.2", "10.10.0.10", "modbus", ["3", "4", "6"])
])

# Ingest live frames
for frame in live_pcap_stream():
    alerts = agent.ingest_frame(frame)
    for alert in alerts:
        publish_to_kafka(alert)
```

### Demo Scripts

**Email Verification Demo** (processes CSV of auth events):
```bash
python scripts/demo.py email --csv data/auth_events.csv
```

**OT Protocol Demo** (synthetic Modbus frames):
```bash
python scripts/demo.py ot
```

**Replay Auth Events from CSV**:
```bash
python scripts/replay_auth_csv.py data/auth_events.csv
```

**Run OT Collector on PCAP**:
```bash
PCAP_PATH=pcaps/sample_modbus.pcap python scripts/run_ot_collector.py
```

---

## 🧱 Project Structure

```
/workspace
├── config/
│   └── zones.yaml                  # OT network zone definitions
├── config.yaml                     # Main system configuration template
├── kafka_topics.yaml               # Kafka topic definitions per environment
├── schemas.py                      # Event schemas (AuthVerificationRequested, OTProtocolFrame, etc.)
│
├── email_verification/             # Authentication fraud detection agent
│   ├── agent.py                    # Main agent loop with Kafka consumer
│   ├── rule_engine.py              # Rule executor framework
│   ├── context.py                  # KVStore, Metrics, Alert abstractions
│   └── rules/
│       ├── velocity.py             # Rate limiting & burst detection
│       ├── token_reuse.py          # Replay attack detection
│       ├── token_expiry.py         # Expired token usage
│       ├── geo_anomaly.py          # Impossible travel detection
│       ├── disposable_domain.py    # Temporary email domain blocking
│       └── dmarc_compliance.py     # Email authentication compliance
│
├── ot_collector/                   # OT protocol monitoring
│   ├── ot_tracking_agent.py        # Main OT agent with zone enforcement
│   ├── asset_manager.py            # Asset inventory and baseline learning
│   ├── safety_controls.py          # Safety system interlocks
│   └── dissectors/
│       ├── modbus.py               # Modbus/TCP parser
│       ├── dnp3.py                 # DNP3 parser
│       ├── iec104.py               # IEC 60870-5-104 parser
│       └── iec61850.py             # IEC 61850 MMS parser
│
├── email_recording/                # Email delivery event recorder
│   ├── db.py                       # PostgreSQL persistence layer
│   └── schema_linter.py            # PII detection & redaction
│
├── scripts/
│   ├── demo.py                     # Standalone demo runner
│   ├── replay_auth_csv.py          # Kafka producer from CSV
│   ├── run_ot_collector.py         # PCAP file ingest
│   └── privacy_scan.py             # Log file PII scanner
│
├── sql/
│   ├── asset_baseline.sql          # OT asset baseline queries
│   └── verification_audit.sql      # Auth event audit views
│
├── dashboards/
│   └── grafana_dashboard.json      # Pre-built Grafana dashboard
│
├── elastic/
│   └── detections.ndjson           # Elastic SIEM detection rules
│
├── splunk/
│   └── correlation_savedsearches.conf  # Splunk correlation searches
│
├── sentinel/
│   └── analytics_rules.json        # Azure Sentinel analytics rules
│
├── playbooks/
│   └── high_severity_playbooks.yaml    # Incident response playbooks
│
├── docs/
│   ├── lab_runbook.md              # Lab deployment guide
│   ├── ot_collector_placement.md   # OT collector installation guide
│   └── service_accounts_and_secrets.md  # Secrets management guide
│
├── docker-compose.lab.yml          # Lab environment orchestration
└── requirements.txt                # Python dependencies
```

---

## 🔧 Configuration

### Main Configuration (`config.yaml`)

Key sections:

- **`database`** – PostgreSQL connection strings with Vault secret references
- **`kafka`** – Brokers per environment (lab, staging, limited-prod, full-prod)
- **`alerts`** – Slack, PagerDuty routing by severity
- **`policy`** – Rate limits, token expiry, velocity windows
- **`compliance`** – PII retention, hashing, audit logging (NERC CIP, IEC 62443, NIST SP 800-82)
- **`services`** – Consumer groups, topic mappings

### Kafka Topics (`kafka_topics.yaml`)

Defines partitioning, retention, replication for:

- **`auth-verification-events`** – 30-day retention, partitioned by `user_id`
- **`email-delivery-events`** – 14-day retention, partitioned by domain
- **`ot-network-events`** – 7-day retention (high volume), partitioned by protocol

### Zone Configuration (`config/zones.yaml`)

Define OT network zones and allowed flows:

```yaml
zones:
  - name: control
    cidrs: ["10.10.0.0/24"]
  - name: safety
    cidrs: ["10.20.0.0/24"]
  - name: corporate
    cidrs: ["192.168.0.0/16"]

allowed_flows:
  - src_zone: control
    dst_zone: safety
  - src_zone: control
    dst_zone: historians
```

---

## 🧪 Development

### Running Tests

```bash
pytest tests/
```

### Privacy Scanning

Ensure no PII leaks in logs:

```bash
python scripts/privacy_scan.py logs/agent.log logs/ot_consumer.log
```

### Adding a New Detection Rule

**For Email Verification:**

1. Create `email_verification/rules/my_rule.py`
2. Extend the `Rule` base class
3. Implement `evaluate(event, context)` method
4. Add to agent initialization in `scripts/demo.py`

**For OT Tracking:**

1. Create a new rule in `ot_collector/ot_tracking_agent.py`
2. Extend the `Rule` base class
3. Implement `evaluate(frame, agent)` method
4. Add to `OTTrackingAgent.rules` list

### Tuning False Positive Rate

See `docs/lab_runbook.md` for FP tuning recommendations. Key levers:

- **VelocityRule**: Adjust `max_auth_requests` threshold
- **GeoAnomalyRule**: Change speed threshold (default 1000 km/h)
- **UnknownFunctionCodeRule**: Set to WARN for warmup period
- **OutOfRangeValueRule**: Customize per asset/tag learned ranges

---

## 🧑‍💻 Technologies Used

| Category | Technologies |
|----------|-------------|
| **Languages** | Python 3.13+ |
| **Event Streaming** | Apache Kafka (Confluent Platform 7.7.1), Schema Registry |
| **Database** | PostgreSQL 16 |
| **Packet Analysis** | dpkt (Python PCAP parsing) |
| **SIEM** | Elastic, Splunk, Azure Sentinel, Grafana |
| **Orchestration** | Docker, docker-compose |
| **Compliance** | NERC CIP, IEC 62443, NIST SP 800-82 |
| **Protocols** | Modbus/TCP, DNP3, IEC 60870-5-104, IEC 61850, OPC UA |

### Python Dependencies

- **`confluent-kafka>=2.5.0`** – Kafka producer/consumer
- **`psycopg[binary]>=3.2.1`** – PostgreSQL adapter
- **`PyYAML>=6.0.1`** – Configuration parsing
- **`dpkt>=1.9.8`** – PCAP packet dissection

---

## 📚 Documentation

- **[Lab Runbook](docs/lab_runbook.md)** – Step-by-step guide for lab deployment
- **[OT Collector Placement](docs/ot_collector_placement.md)** – Network tap/SPAN configuration
- **[Service Accounts & Secrets](docs/service_accounts_and_secrets.md)** – Vault integration guide

---

## 🚨 Security & Compliance

### Data Governance

- **PII Handling**: Email addresses are hashed (SHA-256 with salt) before storage
- **Retention Policies**:
  - Auth events: 30 days
  - Email events: 14 days
  - OT events: 7 days (with export to cold storage)
- **Redaction**: Passwords, tokens, authorization headers excluded from logs
- **Audit**: All access to sensitive topics/tables logged to S3

### Compliance Standards

This system is designed to satisfy:

- **NERC CIP-005**: Electronic Security Perimeter monitoring
- **NERC CIP-007**: System Security Management (event logging)
- **IEC 62443-3-3**: System security requirements and security levels
- **NIST SP 800-82**: Guide to ICS Security

---

## 🤝 Contributing

This is a proprietary system for energy sector critical infrastructure. Contributions are limited to authorized personnel.

### Development Workflow

1. Create a feature branch: `git checkout -b feature/my-rule`
2. Implement changes and add tests
3. Run linters and tests: `pytest tests/ && python scripts/privacy_scan.py`
4. Submit a pull request with detailed description
5. Ensure CI passes (linting, tests, privacy scan)

---

## 📞 Support

For issues or questions:

- **SOC Team**: soc@energyco.example
- **OT Security Team**: otsec@energyco.example

---

## 📄 License

**Proprietary** – Unauthorized use, distribution, or modification is prohibited.

---

## 🔮 Roadmap

- [ ] Add OPC UA dissector support
- [ ] Implement ML-based anomaly detection for OT baselines
- [ ] MITRE ATT&CK for ICS mapping for alerts
- [ ] Real-time risk scoring dashboard
- [ ] Integration with SOAR platforms (Cortex XSOAR, Splunk Phantom)
- [ ] Automated incident response playbooks

---

**Built with ❤️ for critical infrastructure protection**
