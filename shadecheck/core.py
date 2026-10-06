"""SC-002 uses observed bytes; SHA-256 here is an evidence fingerprint, not a Zcash txid."""
import hashlib
import json
import threading
import time
from pathlib import Path
from .payment_rule import evaluate_payment

LIMITATIONS = [
    "SC-001 through SC-004 are implemented; SC-005 remains.",
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

    def record(self, method, phase, peer, source_mode=None, **metadata):
        if source_mode is not None and source_mode not in {"upstream", "wallet-adapter", "protocol-fixture"}:
            raise ValueError("Unknown evidence source mode")
        with self.lock:
            self.sequence += 1
            event = dict(schema_version=1, sequence=self.sequence, mode=source_mode or self.mode,
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


def evaluate(events, policy="strict", window_seconds=30, rules=("SC-002",), sync_policy=None, payment_policy=None):
    if not rules or set(rules) - {"SC-001", "SC-002", "SC-003", "SC-004"}:
        raise ValueError("Select implemented rules SC-001 through SC-004")
    if not events:
        raise ValueError("Empty evidence: no test was executed")
    findings = []
    requests = [e for e in events if e["method"] == "SendTransaction" and e["phase"] == "request"
                and e["metadata"].get("payload_size", 0) > 0]
    responses = {e["metadata"].get("request_sequence"): e for e in events
                 if e["method"] == "SendTransaction" and e["phase"] == "response"}
    for event in requests if "SC-002" in rules else []:
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
    coverage = []
    if "SC-001" in rules:
        if not isinstance(sync_policy, dict) or set(sync_policy) != {"chunk_size", "alignment_height"}:
            raise ValueError("SC-001 requires chunk_size and alignment_height in the sync policy")
        chunk = sync_policy["chunk_size"]
        alignment = sync_policy["alignment_height"]
        if type(chunk) is not int or chunk <= 0 or type(alignment) is not int or alignment < 0:
            raise ValueError("Sync policy needs a positive integer chunk size and nonnegative alignment height")
        ranges = [e for e in events if e["method"] == "GetBlockRange" and e["phase"] == "request"
                  and e["mode"] == "upstream"]
        complete = []
        for request in ranges:
            start = request["metadata"].get("start_height")
            end = request["metadata"].get("end_height")
            if type(start) is not int or type(end) is not int or start < 0 or end < start:
                raise ValueError("Invalid block range in SC-001 evidence")
            delivered = [e for e in events if e["method"] == "GetBlockRange" and e["phase"] == "response"
                         and e["session"] == request["session"]
                         and e["metadata"].get("request_sequence") == request["sequence"]]
            heights = {e["metadata"]["height"] for e in delivered}
            size = end - start + 1
            fully_delivered = (len(heights) == size and min(heights, default=-1) == start
                               and max(heights, default=-1) == end)
            complete.append(fully_delivered)
            violations = []
            if start < alignment or (start - alignment) % chunk:
                violations.append("start height is not aligned to the configured boundary")
            if size != chunk:
                violations.append("inclusive request size differs from the configured chunk size")
            if violations:
                findings.append({
                    "rule_id": "SC-001", "title": "Block range violates configured sync disclosure policy",
                    "severity": "MEDIUM",
                    "observed_behavior": f"Requested heights {start} through {end} ({size} blocks): " + "; ".join(violations) + ".",
                    "evidence": [request] + delivered,
                    "possible_privacy_consequence": "The service observes the connection's exact scan boundary and request size. These can depend on local sync state, but wallet history or identity is not proven.",
                    "affected_component": "lightwalletd block-range synchronization",
                    "suggested_investigation": "Review fixed-size aligned retrieval, local filtering, and chain-tip handling against the declared policy; evaluate extra bandwidth and other privacy tradeoffs.",
                    "sync_policy": dict(sync_policy), "request_size": size,
                    "violations": violations, "complete_range_delivered": fully_delivered,
                })
        coverage.append({"rule_id": "SC-001", "executed": True,
                         "coverage": "complete-range-delivery" if ranges and all(complete) else "incomplete-range-delivery",
                         "covered": bool(ranges) and all(complete)})
    if "SC-002" in rules:
        coverage.append({"rule_id": "SC-002", "executed": True,
                         "coverage": "broadcast-observed" if requests else "no-broadcast-observed",
                         "covered": bool(requests)})
    if "SC-003" in rules:
        blocks = [e for e in events if e["method"] == "GetBlockRange" and e["phase"] == "response"
                  and len(set(e["metadata"].get("transaction_ids", []))) >= 2 and e["mode"] == "upstream"]
        fetches = [e for e in events if e["method"] == "GetTransaction" and e["phase"] == "request"]
        for block in blocks:
            ids = set(block["metadata"]["transaction_ids"])
            selected = [e for e in fetches if e["session"] == block["session"]
                        and e["metadata"].get("transaction_id") in ids
                        and 0 <= e["elapsed_ns"] - block["elapsed_ns"] <= window_seconds * 1e9]
            requested = {e["metadata"]["transaction_id"] for e in selected}
            if not requested or requested == ids:
                continue
            sequences = {e["sequence"] for e in selected}
            replies = [e for e in events if e["method"] == "GetTransaction"
                       and e["phase"] in {"response", "error"}
                       and e["metadata"].get("request_sequence") in sequences]
            findings.append({
                "rule_id": "SC-003", "title": "Subset of delivered compact transactions fetched by ID",
                "severity": "MEDIUM",
                "observed_behavior": f"The same transport session requested {len(requested)} of {len(ids)} delivered compact transaction IDs within the configured window.",
                "evidence": [block] + sorted(selected + replies, key=lambda e: e["sequence"]),
                "possible_privacy_consequence": "The service can associate selected transaction IDs with this connection; relevance to a wallet or person is not proven.",
                "affected_component": "lightwalletd transaction retrieval",
                "suggested_investigation": "Review transaction-specific fetches, local caching, and broader retrieval for the tested block; evaluate bandwidth and other privacy tradeoffs.",
                "block_height": block["metadata"]["height"],
                "requested_transaction_ids": sorted(requested),
                "delivered_transaction_count": len(ids),
                "first_fetch_delta_ns": min(e["elapsed_ns"] for e in selected) - block["elapsed_ns"],
            })
        coverage.append({"rule_id": "SC-003", "executed": True,
                         "coverage": "multi-transaction-block-delivered" if blocks else "no-multi-transaction-block-delivered",
                         "covered": bool(blocks)})
    if "SC-004" in rules:
        payment_findings, payment_coverage = evaluate_payment(events, payment_policy)
        findings.extend(payment_findings)
        coverage.append(payment_coverage)
    if findings:
        status = "FAIL" if policy == "strict" else "WARN"
    else:
        status = "PASS" if all(r["covered"] for r in coverage) else "WARN"
    return {"schema_version": 1, "policy": policy, "status": status,
            "rules": coverage,
            "findings": findings, "limitations": LIMITATIONS,
            "evidence_root": events[-1]["event_hash"],
            "correlation_window_seconds": window_seconds,
            "sync_policy": sync_policy if "SC-001" in rules else None,
            "payment_policy": payment_policy if "SC-004" in rules else None}
