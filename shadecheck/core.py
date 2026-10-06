"""SC-002 uses observed bytes; SHA-256 here is an evidence fingerprint, not a Zcash txid."""
import hashlib
import json
import threading
import time
from pathlib import Path

LIMITATIONS = [
    "Only SC-002 is implemented in this first milestone.",
    "A transport peer identifies a connection, not a person or wallet.",
    "Local fixture replay is not consensus validation or network acceptance.",
    "Transaction SHA-256 fingerprints are not Zcash transaction IDs.",
    "No violation observed does not establish anonymity.",
]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class Recorder:
    def __init__(self, path, mode):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents mixing runs or accidentally overwriting evidence.
        self.file = self.path.open("x", encoding="utf-8")
        self.lock = threading.Lock()
        self.mode = mode
        self.started = time.monotonic_ns()
        self.sequence = 0
        self.previous = "0" * 64

    def record(self, method, phase, peer, **metadata):
        with self.lock:
            self.sequence += 1
            event = dict(schema_version=1, sequence=self.sequence, mode=self.mode,
                         method=method, phase=phase,
                         timestamp_ns=time.time_ns(),
                         elapsed_ns=time.monotonic_ns() - self.started,
                         session=hashlib.sha256(peer.encode()).hexdigest(),
                         metadata=metadata, previous_hash=self.previous)
            event["event_hash"] = hashlib.sha256(canonical(event).encode()).hexdigest()
            self.previous = event["event_hash"]
            self.file.write(canonical(event) + "\n")
            self.file.flush()
            return event["sequence"]

    def close(self):
        self.file.close()


def load_events(path):
    events = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if not events:
        raise ValueError("Empty evidence: no test was executed")
    previous = "0" * 64
    elapsed = -1
    for sequence, event in enumerate(events, 1):
        unsigned = {k: v for k, v in event.items() if k != "event_hash"}
        if (event["sequence"] != sequence or event["previous_hash"] != previous
                or event["event_hash"] != hashlib.sha256(canonical(unsigned).encode()).hexdigest()
                or event["elapsed_ns"] < elapsed or event["schema_version"] != 1):
            raise ValueError("Invalid evidence sequence, schema, time, or hash chain")
        previous, elapsed = event["event_hash"], event["elapsed_ns"]
    return events


def evaluate(events, policy="strict", window_seconds=30):
    findings = []
    requests = [e for e in events if e["method"] == "SendTransaction" and e["phase"] == "request"
                and e["metadata"].get("payload_size", 0) > 0]
    responses = {e["metadata"].get("request_sequence"): e for e in events
                 if e["method"] == "SendTransaction" and e["phase"] == "response"}
    for event in requests:
        fingerprint = event["metadata"]["payload_sha256"]
        response = responses.get(event["sequence"])
        observations = [e for e in events if e["method"] == "GetMempoolStream"
                        and e["phase"] == "response"
                        and e["metadata"].get("payload_sha256") == fingerprint
                        and 0 <= e["elapsed_ns"] - event["elapsed_ns"] <= window_seconds * 1e9]
        accepted = response is not None and response["metadata"].get("error_code") == 0
        high = accepted and bool(observations) and event["mode"] == "upstream"
        evidence = [event] + ([response] if response else []) + observations
        findings.append({
            "rule_id": "SC-002", "title": "Broadcast payload linked to a transport session",
            "severity": "HIGH" if high else "MEDIUM",
            "observed_behavior": ("Accepted submission and identical mempool bytes observed within the configured window."
                                  if high else "Non-empty submission bytes observed on an identifiable transport connection."),
            "evidence": evidence,
            "possible_privacy_consequence": "The RPC observer can associate these submitted bytes with this connection; this does not identify a person.",
            "affected_component": "lightwalletd broadcast transport",
            "suggested_investigation": "Review the server trust model and whether an independent broadcast path reduces the observer's linkability.",
            "payload_sha256": fingerprint, "network_acceptance_reported": accepted,
        })
    covered = bool(requests)
    if not covered:
        status = "WARN"
    elif findings:
        status = "FAIL" if policy == "strict" else "WARN"
    else:
        status = "PASS"
    return {"schema_version": 1, "policy": policy, "status": status,
            "rules": [{"rule_id": "SC-002", "executed": True,
                       "coverage": "broadcast-observed" if covered else "no-broadcast-observed"}],
            "findings": findings, "limitations": LIMITATIONS,
            "evidence_root": events[-1]["event_hash"],
            "correlation_window_seconds": window_seconds}
