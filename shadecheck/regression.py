"""Portable, evidence-backed SC-005 baselines; no comparison of incidental IDs."""
import hashlib
import json
from pathlib import Path
from .core import canonical, evaluate, load_events

VERSION = 1
RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def context(result):
    return {"evidence_modes": result["evidence_modes"], "rules": sorted(r["rule_id"] for r in result["rules"] if r["rule_id"] != "SC-005"),
            "correlation_window_seconds": result["correlation_window_seconds"],
            "sync_policy": result.get("sync_policy"), "payment_policy": result.get("payment_policy")}


def recompute(events, result):
    c = context(result)
    return evaluate(events, policy=result["policy"], window_seconds=c["correlation_window_seconds"],
                    rules=c["rules"], sync_policy=c["sync_policy"], payment_policy=c["payment_policy"])


def verified_report(events_path, report_path):
    events = load_events(events_path)
    report = json.loads(Path(report_path).read_text())
    if any(r["rule_id"] == "SC-005" for r in report["rules"]):
        raise ValueError("Use a base-rule report, not a comparison report, for this operation")
    if recompute(events, report) != report:
        raise ValueError("Report does not match recomputed evidence")
    return events, report


def save_baseline(events_path, report_path, output):
    events, result = verified_report(events_path, report_path)
    if not all(r["covered"] for r in result["rules"]):
        raise ValueError("Cannot save a baseline with incomplete rule coverage")
    value = {"schema_version": 1, "kind": "shadecheck-baseline", "evaluation_version": VERSION,
             "events": events, "result": result}
    value["baseline_hash"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        f.write(canonical(value) + "\n")
    return value


def load_baseline(path):
    value = json.loads(Path(path).read_text())
    unsigned = {k: v for k, v in value.items() if k != "baseline_hash"}
    if (value.get("schema_version") != 1 or value.get("kind") != "shadecheck-baseline"
            or value.get("evaluation_version") != VERSION
            or value.get("baseline_hash") != hashlib.sha256(canonical(unsigned).encode()).hexdigest()):
        raise ValueError("Invalid baseline schema, evaluator version, or hash")
    # Reuse the same hash-chain validator without writing an intermediate file.
    from .core import validate_events
    events = validate_events(value["events"])
    if recompute(events, value["result"]) != value["result"]:
        raise ValueError("Baseline result does not match its evidence")
    if not all(r["covered"] for r in value["result"]["rules"]):
        raise ValueError("Baseline has incomplete coverage")
    return value


def behavior(finding):
    rule = finding["rule_id"]
    detail = ""
    if rule == "SC-001":
        detail = "|".join(sorted(finding["violations"]))
    elif rule == "SC-004":
        receipts = [e["metadata"] for e in finding["evidence"] if e["method"] == "WalletTransaction"]
        detail = "transparent-input=" + str(any(m.get("transparent_inputs", 0) > 0 for m in receipts))
        detail += ";transparent-output=" + str(any(m.get("transparent_outputs", 0) > 0 for m in receipts))
    return (rule, finding["affected_component"], detail)


def groups(result):
    grouped = {}
    for f in result["findings"]:
        key = behavior(f)
        if key not in grouped or RANK[f["severity"]] > RANK[grouped[key]["severity"]]:
            grouped[key] = f
    return grouped


def compare_result(current, baseline):
    previous = baseline["result"]
    if context(current) != context(previous):
        raise ValueError("Incompatible comparison: rule selection or test policy changed")
    old, new = groups(previous), groups(current)
    changes, findings = [], []
    for key, f in sorted(new.items()):
        prior = old.get(key)
        change = ("new-failure" if not any(k[0:2] == key[0:2] for k in old) else "new-sensitive-behavior") if prior is None else (
            "severity-increased" if RANK[f["severity"]] > RANK[prior["severity"]] else None)
        if change is None:
            continue
        item = {"change": change, "source_rule": f["rule_id"], "behavior": list(key),
                "previous_severity": prior["severity"] if prior else None, "current_severity": f["severity"]}
        changes.append(item)
        findings.append({"rule_id": "SC-005", "title": "Privacy regression: " + change,
                         "severity": f["severity"], "observed_behavior": f["observed_behavior"],
                         "evidence": f["evidence"], "baseline_evidence": prior["evidence"] if prior else [],
                         "baseline_evidence_root": previous["evidence_root"], "change": item,
                         "possible_privacy_consequence": "A defined privacy-sensitive behavior is newly observed or more severe than the saved baseline.",
                         "affected_component": f["affected_component"],
                         "suggested_investigation": "Inspect the current and baseline evidence and the code or configuration change; restore the tested requirement before accepting a new baseline."})
    covered = all(r["covered"] for r in current["rules"])
    result = dict(current)
    result["findings"] = current["findings"] + findings
    result["rules"] = current["rules"] + [{"rule_id": "SC-005", "executed": True,
                                           "coverage": "compatible-baseline-comparison" if covered else "current-coverage-incomplete",
                                           "covered": covered}]
    result["baseline_comparison"] = {"baseline_hash": baseline["baseline_hash"],
                                     "baseline_evidence_root": previous["evidence_root"],
                                     "changes": changes, "regressions": len(changes),
                                     "resolved_behaviors": [list(k) for k in sorted(old.keys() - new.keys())],
                                     "unchanged_behaviors": len(old.keys() & new.keys()),
                                     "status": "FAIL" if changes and current["policy"] == "strict" else (
                                         "WARN" if changes or not covered else "PASS")}
    # Base-rule strict failures remain failures even if already present in the baseline.
    if findings:
        result["status"] = "FAIL" if current["policy"] == "strict" else "WARN"
    result["limitations"] = current["limitations"] + [
        "SC-005 compares rule/component/behavior categories, not changing transaction IDs, sessions, timestamps, or finding counts.",
        "Baselines include inspectable evidence; hashes detect editing but do not authenticate an author.",
        "Compatible policy and complete coverage are required; a baseline is not a privacy exemption."]
    return result
