# Lab Deployment Runbook

## Prereqs
- Docker + docker-compose
- PCAP samples placed in `./pcaps`
- CSV auth dump in `./data/auth_events.csv`

## Bring up stack
```bash
docker compose -f docker-compose.lab.yml up -d --build
```

## Create topics (if auto-create disabled)
```bash
docker exec -it $(docker ps -q -f name=kafka) kafka-topics --bootstrap-server kafka:9092 --create --topic auth-verification-events --partitions 12 --replication-factor 1
docker exec -it $(docker ps -q -f name=kafka) kafka-topics --bootstrap-server kafka:9092 --create --topic ot-network-events --partitions 24 --replication-factor 1
```

## Replay auth logs
```bash
python scripts/replay_auth_csv.py data/auth_events.csv
```

## Run OT collector against PCAP
```bash
PCAP_PATH=pcaps/sample_modbus.pcap python scripts/run_ot_collector.py
```

## Run OT tracking consumer
```bash
python scripts/run_ot_tracking_consumer.py
```

## Tuning FP rate (<2%)
- Start with `VelocityRule` thresholds: increase `max_auth_requests` if bursty but benign
- Use `DisposableDomainRule` as LOW severity initially; escalate if abuse confirmed
- In OT, adjust `UnknownFunctionCodeRule` to WARN for first week, flip to MEDIUM later

## Privacy validation
- Ensure `email_normalized_hash` used, not plaintext emails
- Run privacy scanner
```bash
python scripts/privacy_scan.py logs/agent.log logs/ot_consumer.log
```
