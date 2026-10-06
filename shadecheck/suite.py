"""Read-only acceptance artifact validation shared by CLI orchestration and dashboard."""
import hashlib
import json
from .core import load_events
from .regression import load_baseline, compare_result, recompute

REQUIRED_RULES = {f"SC-00{i}" for i in range(1, 6)}
FIELDS = {"rule_id", "title", "severity", "observed_behavior", "evidence",
          "possible_privacy_consequence", "affected_component", "suggested_investigation"}
def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_artifacts(root):
    traces = {}
    for path in sorted(root.rglob("events.jsonl")):
        events = load_events(path)
        require(all(e["mode"] in {"upstream", "wallet-adapter"} for e in events),
                f"Fixture evidence cannot satisfy real acceptance: {path}")
        traces[events[-1]["event_hash"]] = (path, events)
    require(traces, "No actual evidence traces")
    baselines = {}
    for path in sorted(root.rglob("*.json")):
        value = json.loads(path.read_text())
        if isinstance(value, dict) and value.get("kind") == "shadecheck-baseline":
            b = load_baseline(path)
            baselines[b["baseline_hash"]] = b
    entries, executed, failures = [], set(), set()
    for path in sorted(root.rglob("*.json")):
        result = json.loads(path.read_text())
        if not isinstance(result, dict) or "correlation_window_seconds" not in result:
            continue
        require(result["evidence_root"] in traces, f"Report lacks source trace: {path}")
        event_path, events = traces[result["evidence_root"]]
        current = recompute(events, result)
        if "baseline_comparison" in result:
            key = result["baseline_comparison"]["baseline_hash"]
            require(key in baselines, f"Comparison lacks portable baseline: {path}")
            current = compare_result(current, baselines[key])
        require(current == result, f"Report differs from re-evaluation: {path}")
        for finding in result["findings"]:
            require(FIELDS.issubset(finding) and finding["evidence"], f"Incomplete finding: {path}")
            by_hash = {e["event_hash"]: e for e in events}
            require(all(by_hash.get(e["event_hash"]) == e for e in finding["evidence"]),
                    f"Finding embeds non-source evidence: {path}")
            failures.add(finding["rule_id"])
        executed.update(r["rule_id"] for r in result["rules"] if r["executed"])
        html_path = path.with_suffix(".html")
        # test-with-baseline duplicates regressed-comparison; it is a CLI-equivalence check.
        if path.name != "test-with-baseline.json":
            require(html_path.exists() and "<html" in html_path.read_text(), f"Missing HTML report: {path}")
        entries.append({"report": str(path.relative_to(root)), "events": str(event_path.relative_to(root)),
                        "status": result["status"], "rules": [r["rule_id"] for r in result["rules"]],
                        "evidence_root": result["evidence_root"], "findings": len(result["findings"])})
    require(executed == REQUIRED_RULES, f"Rule execution missing: {REQUIRED_RULES - executed}")
    require(failures == REQUIRED_RULES, f"Evidence-backed failures missing: {REQUIRED_RULES - failures}")

    def one(pattern):
        paths = list(root.glob(pattern))
        require(len(paths) == 1, f"Expected one current-run artifact for {pattern}")
        return json.loads(paths[0].read_text())

    sync = one("sync-pattern/*/comparison.json")
    require(sync["narrow"]["strict_exit"] == 1 and sync["aligned"]["strict_exit"] == 0, "SC-001 exit comparison failed")
    selective = one("selective-fetch/*/comparison.json")
    require(selective["subset"]["strict_exit"] == 1 and selective["complete"]["strict_exit"] == 0, "SC-003 exit comparison failed")
    payment = one("transparent-fallback/*/comparison.json")
    require(payment["permissive"]["strict_exit"] == 1 and payment["full_privacy"]["strict_exit"] == 0, "SC-004 exit comparison failed")
    require(payment["permissive"]["decoded_structure"]["transparent_outputs"] > 0
            and payment["full_privacy"]["decoded_structure"]["transparent_outputs"] == 0
            and payment["full_privacy"]["decoded_structure"]["transparent_inputs"] == 0, "Payment structure comparison failed")
    regression = one("privacy-regression/*/comparison.json")
    require(regression["unchanged"]["status"] == "PASS" and regression["unchanged"]["regressions"] == 0, "Unchanged baseline did not PASS")
    for key in ["new_failure", "new_behavior", "severity_increase"]:
        require(regression[key]["status"] == "FAIL" and regression[key]["regressions"] > 0, f"SC-005 missing {key}")
    require(regression["known_failure"]["regressions"] == 0, "Known failure mislabeled as regression")
    # Independently inspect the overall report, not just comparison-only status.
    known = one("privacy-regression/*/known-failure.json")
    require(known["status"] == "FAIL", "Baseline incorrectly exempted a strict failure")
    repeat = list(root.glob("regtest/*/backend-proof.json"))
    kinds = [json.loads(p.read_text())["transaction_kind"] for p in repeat]
    require(kinds.count("transparent") == 1 and kinds.count("sapling-shielded") == 2, "Missing actual transparent/shielded repeat proofs")
    for path in root.rglob("backend-proof.json"):
        proof = json.loads(path.read_text())
        if "send_response_code" in proof:
            require(proof["send_response_code"] == 0 and proof["node_mempool_contains_txid"]
                    and proof["node_raw_transaction_matches"], f"Missing node acceptance proof: {path}")
        if "returned_blocks" in proof:
            require(proof["returned_blocks"] and all(b["node_block_hash_matches"] for b in proof["returned_blocks"]), "Block proofs incomplete")
        if "fetches" in proof:
            require(proof["fetches"] and all(f["node_raw_transaction_matches"] and f["confirmed_block_matches"] for f in proof["fetches"]), "Transaction fetch proofs incomplete")
    return entries


def summary_html(value):
    import html
    rows = ''.join('<tr><td>'+html.escape(e['report'])+'</td><td>'+html.escape(', '.join(e['rules']))+'</td><td>'+e['status']+'</td></tr>' for e in value['reports'])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>ShadeCheck acceptance</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:20px}td,th{text-align:left;padding:8px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap}</style><h1>ShadeCheck acceptance: '+value['acceptance_status']+'</h1><p>Acceptance PASS means the checks behaved as required. Expected privacy failures remain FAIL. Passing does not establish anonymity.</p><table><tr><th>Report</th><th>Rules</th><th>Privacy status</th></tr>'+rows+'</table><h2>Limitations</h2><pre>'+html.escape(json.dumps(value['limitations'],indent=2))+'</pre></html>'


def verify(root):
    value = json.loads((root / "suite.json").read_text())
    require(value["acceptance_status"] == "PASS", "Suite did not complete")
    for entry in value["artifacts"]:
        path = (root / entry["path"]).resolve()
        require(path.is_relative_to(root.resolve()), "Artifact path escapes suite")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], f"Artifact changed: {entry['path']}")
    reports = check_artifacts(root)
    require(reports == value["reports"], "Acceptance report index changed")
    print(f"SHADECHECK ACCEPTANCE ARTIFACTS VERIFIED: {root}")


