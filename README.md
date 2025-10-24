# Agentic AI for Energy Defense

##### Table of Contents
[Features] (###Features)
[Istallation, Usage and Environment] (###Installation)
[Folder Structure] (### Folder Struture)
[Technologies Used] (### Technologies Used)
[Stakeholder Interviews] (# Stakeholder Interviews)
[Student Feedback Summary] (# Student Feedback LLM Summary)



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

# Stakeholder Interviews

**Google Doc with Real + Synthetic Interviews and Prompts:**  
[Doc File](https://docs.google.com/document/d/1RnQuQxmN26TGWpf7Kb0vvmAiG7csEasHnDN-DLE-pmE/edit?usp=sharing)

 ## Below is just the Real Interview Responses

**Question:**  
From your perspective, does this design align with general cybersecurity compliance best practices?

**Responses:**
- We do something similar, there is already a check process.  
- Assess if it is the correct person.  
- Seems realistic.

---

### Initial Concerns or Red Flags

**Question:**  
What are your initial concerns or red flags when you see this design?

**Concerns:**
- Getting bombarded with more emails, notifications, and other things to jump through to make things work and function.
- **Q:** If there is only one point of access to the job (laptop), but I only have one point of access, how would I be able to get access to the system?  
  Seems like I'm locked out until this verification takes place.  
  Contractors usually only have 1 POA.
- **Q:** IT swap situation — how will this accommodate for changing devices?
- Sometimes we use access to VPN to get to the system.
- Has a firewall and the work we do is safe.

---

### Stronger Access Control, Auditing, or Encryption

**Question:**  
Are there any parts of this system where stronger access control, auditing, or encryption would be necessary?

**Responses:**
- We need to make sure the people who are ok to come in are able to come in.  
- There is a balancing act where we need to be selective about who we are inviting.  
- Energy sector has massive damage potential → high necessity.  
- This is the nature of the grid across the board — they are connected to others, that affects the entire grid.  
- The backups from one utility are from neighboring utility companies.  
- Mentions FERC/NERC?  
- There are no competitors — we are all on the same level going towards the same goal.

---

### Threat-Sharing Systems

**Question:**  
Are there current threat-sharing systems? Would companies want to share that information?

**Responses:**
- IDK what exists in the system.  
- I would have a guess that there is some sort of reporting requirement — that there is a reporting system that goes up to NERC that diagnoses and resolves the issue.  
- There may exist a more auto-system.  
- Being in the energy sector, it would be easier to do sharing than others.  
- We are considered a regulated monopoly.  
- **Regulated monopoly:**  
  - We cannot control prices — those are controlled through government processes.  
  - We have systems that are bureaucratic red tapes.

**Additional Notes:**
- We are given monopoly power over a region of territory.  
- We are the only ones in control of the territory, but we share and partner with other utilities.  
  - **Examples:** EPA (federal major entity), Seattle City Light (public), Tacoma Power (public).  
- Don’t compete because we all deal with separate customer bases.  
- That allows us to coordinate and work together instead of compete.  
- We are a team that works together to protect the grid and the customers.

---

### Scalability from a Compliance Perspective

**Question:**  
How scalable is this design from a compliance perspective as regulations evolve?

**Responses:**
- I don’t know.  
- The role is the end-user.  
- **Q:** What do you mean by scalability?  
- **Private vs. public.**  
- **Large vs. small.**  
- **P:** Scalability meaning how easy will it be to meet changes in cyber requirements. Any thoughts?  
- Part of it is going to be based on what the federal government wants us to do.  
- There is a component where NERC has the most up-to-date requirements and we have to follow.  
- From my perspective it is entirely up to this independent but public agency (NERC) to set the regulations.  
- Also subject to their own game of politics.  
- Up to how modern these policymakers are in their regulations and the flexibility within these policies.  
- Usually looks at if it fits within the scope.

---

### Communication and Coordination

**Question:**  
What is the main way of communicating with other companies?

**Responses:**
- Tech related — he doesn’t know.  
- As employees, regular communication.  
- Outlook work email.  
- Only communications through work devices.  
- Regulations exist here.  

**Notes:**
- **Paired substations:**  
  - Substations next to each other.  
  - Allow the electrons to flow to different grids.  
- Meters are always being read.  
- Lots of sharing information.  
- Not a competitive nature.

---


# Student Feedback LLM Summary

Our peers valued these overarching themes, as evident from the feedback given for the demos:

Clear Focus and Scope
Strong Technical Foundations 
Explanability
Professionalism in Presentation

