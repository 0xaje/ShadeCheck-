"""SC-005 integration using fresh upstream block traces and real broadcast evidence."""
import json
import subprocess
import sys
import time
import uuid
import regtest as backend
import sync_pattern
from shadecheck.core import canonical, load_events


def cli(arguments, expected):
    run = subprocess.run([sys.executable, "-m", "shadecheck.cli", *arguments], cwd=backend.ROOT)
    if run.returncode != expected:
        raise RuntimeError(f"CLI returned {run.returncode}; expected {expected}: {arguments}")


def save(case, target):
    cli(["baseline", "save", "--events", str(case / "events.jsonl"), "--input", str(case / "report.json"),
         "--output", str(target)], 0)


def comparison(case, baseline, output, expected):
    cli(["compare", "--events", str(case / "events.jsonl"), "--input", str(case / "report.json"),
         "--baseline", str(baseline), "--output", str(output)], expected)
    cli(["report", "--input", str(output), "--format", "html", "--output", str(output.with_suffix(".html"))], 0)
    return json.loads(output.read_text())


def main():
    try:
        tip = backend.require_regtest()["blocks"]
        available = min(tip, backend.lightd_info().blockHeight)
        chunk = sync_pattern.SYNC_POLICY["chunk_size"]
        start = ((available + 1) // chunk - 1) * chunk
        if start < 1:
            raise RuntimeError("Need a completed historical chunk")
        root = backend.OUTPUT_ROOT / "privacy-regression" / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
        config = root / "policy.json"
        backend.write_json(config, {"schema_version": 1, "sync": sync_pattern.SYNC_POLICY})
        for case, first, last, exit_code in [
                ("baseline-run", start, start + chunk - 1, 0),
                ("unchanged-run", start, start + chunk - 1, 0),
                ("regressed-run", start + 3, start + 9, 1)]:
            sync_pattern.exercise(root / case, first, last, config, exit_code)
        baseline = root / "baseline.json"
        save(root / "baseline-run", baseline)
        unchanged = comparison(root / "unchanged-run", baseline, root / "unchanged-comparison.json", 0)
        regressed = comparison(root / "regressed-run", baseline, root / "regressed-comparison.json", 1)
        if unchanged["baseline_comparison"]["regressions"] or not any(
                f["rule_id"] == "SC-005" and f["change"]["change"] == "new-failure" for f in regressed["findings"]):
            raise RuntimeError("Real traces did not demonstrate new-failure detection")
        test_output = root / "test-with-baseline.json"
        cli(["test", "--events", str(root / "regressed-run/events.jsonl"), "--rules", "SC-001", "SC-005",
             "--config", str(config), "--baseline", str(baseline), "--output", str(test_output)], 1)
        if json.loads(test_output.read_text()) != regressed:
            raise RuntimeError("test --baseline and compare disagree")
        # A second real request violates only size, then a new request violates size AND alignment.
        # These are native upstream requests, not edited or generated evidence.
        sync_pattern.exercise(root / "size-only", start, start + 6, config, 1)
        size_baseline = root / "size-baseline.json"
        save(root / "size-only", size_baseline)
        sensitive = comparison(root / "regressed-run", size_baseline, root / "new-behavior.json", 1)
        if not any(f["rule_id"] == "SC-005" and f["change"]["change"] == "new-sensitive-behavior" for f in sensitive["findings"]):
            raise RuntimeError("New sync behavior was not detected")
        known = comparison(root / "size-only", size_baseline, root / "known-failure.json", 1)
        if known["baseline_comparison"]["regressions"]:
            raise RuntimeError("An unchanged known failure was mislabeled as a regression")
        # Use an actual earlier accepted broadcast trace. A prefix is explicitly a partial
        # observation: the real request was seen before its response/mempool observation.
        candidates = sorted((backend.OUTPUT_ROOT / "regtest").glob("*/report.json"))
        if not candidates:
            raise RuntimeError("Run regtest.py prepare-shielded then prove for severity evidence")
        source = candidates[-1].parent
        events = load_events(source / "events.jsonl")
        request = next(e for e in events if e["method"] == "SendTransaction" and e["phase"] == "request")
        partial = root / "broadcast-request-snapshot"
        partial.mkdir()
        (partial / "events.jsonl").write_text("\n".join(canonical(e) for e in events[:request["sequence"]]) + "\n")
        backend.write_json(partial / "provenance.json", {
            "kind": "actual-event-prefix", "source_events": str(source / "events.jsonl"),
            "source_evidence_root": events[-1]["event_hash"], "last_sequence": request["sequence"],
            "limitation": "Partial observation before response/mempool evidence; no rejection or acceptance is asserted here."})
        cli(["test", "--events", str(partial / "events.jsonl"), "--output", str(partial / "report.json")], 1)
        cli(["report", "--input", str(partial / "report.json"), "--format", "html", "--output", str(partial / "report.html")], 0)
        severity_baseline = root / "broadcast-baseline.json"
        save(partial, severity_baseline)
        full = root / "broadcast-full-observation"
        full.mkdir()
        (full / "events.jsonl").write_text("\n".join(canonical(e) for e in events) + "\n")
        backend.write_json(full / "provenance.json", {"kind": "actual-event-copy", "source_events": str(source / "events.jsonl"),
                                                     "source_evidence_root": events[-1]["event_hash"]})
        cli(["test", "--events", str(full / "events.jsonl"), "--output", str(full / "report.json")], 1)
        cli(["report", "--input", str(full / "report.json"), "--format", "html", "--output", str(full / "report.html")], 0)
        severity = comparison(full, severity_baseline, root / "severity-increase.json", 1)
        if not any(f["rule_id"] == "SC-005" and f["change"]["change"] == "severity-increased"
                   and f["change"]["previous_severity"] == "MEDIUM" and f["severity"] == "HIGH" for f in severity["findings"]):
            raise RuntimeError("Real broadcast evidence did not demonstrate severity escalation")
        backend.write_json(root / "comparison.json", {
            "rule_id": "SC-005", "unchanged": unchanged["baseline_comparison"],
            "new_failure": regressed["baseline_comparison"], "new_behavior": sensitive["baseline_comparison"],
            "known_failure": known["baseline_comparison"], "severity_increase": severity["baseline_comparison"],
            "limitations": ["Fresh real block requests, plus an explicitly labeled prefix of actual broadcast evidence.",
                            "Severity increase can reflect stronger observation, not necessarily a code regression.",
                            "PASS is limited to compatible tested rules; it does not establish anonymity."]})
        print(f"REAL SC-005 COMPARISON VERIFIED: unchanged PASS; new failure, new behavior, severity increase FAIL; known strict failure remains FAIL. Reports: {root}")
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration) as error:
        print(f"Privacy regression error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
