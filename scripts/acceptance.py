"""Run and independently audit the defined real regtest acceptance suite."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import regtest as backend
from shadecheck.core import canonical, load_events, evaluate
from shadecheck.suite import REQUIRED_RULES, require, check_artifacts, summary_html, verify

STEPS = [
    ("unit-boundaries", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("backend-startup", ["scripts/regtest.py", "up"]),
    ("transparent-construction", ["scripts/regtest.py", "prepare"]),
    ("transparent-broadcast", ["scripts/regtest.py", "prove"]),
    ("shielded-construction", ["scripts/regtest.py", "prepare-shielded"]),
    ("shielded-broadcast", ["scripts/regtest.py", "prove"]),
    ("repeat-shielded-construction", ["scripts/regtest.py", "prepare-shielded"]),
    ("repeat-shielded-broadcast", ["scripts/regtest.py", "prove"]),
    ("observer-roles", ["scripts/broadcast_comparison.py"]),
    ("selective-fetch", ["scripts/selective_fetch.py"]),
    ("sync-pattern", ["scripts/sync_pattern.py"]),
    ("transparent-fallback", ["scripts/transparent_fallback.py"]),
    ("privacy-regression", ["scripts/privacy_regression.py"]),
]


def run_step(root, name, arguments, env):
    log = root / "logs" / (name + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"Acceptance step: {name}", flush=True)
    with log.open("x", encoding="utf-8") as f:
        run = subprocess.run([sys.executable, *arguments], cwd=backend.ROOT,
                             env=env, stdout=f, stderr=subprocess.STDOUT, timeout=1200)
    if run.returncode:
        print(log.read_text(errors="replace")[-12000:], file=sys.stderr)
        raise RuntimeError(f"Acceptance step {name} failed with exit {run.returncode}; inspect {log}")
    return {"name": name, "command": ["python", *arguments], "exit": run.returncode,
            "log": str(log.relative_to(root))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, help="Revalidate an existing suite; no Docker operation")
    args = parser.parse_args()
    root = None
    try:
        if args.verify:
            verify(args.verify.resolve())
            return 0
        root = backend.ROOT / "out/acceptance" / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
        root.mkdir(parents=True, exist_ok=False)
        env = dict(os.environ, SHADECHECK_OUTPUT_ROOT=str(root), PYTHONUNBUFFERED="1")
        steps = [run_step(root, name, arguments, env) for name, arguments in STEPS]
        for rule in sorted(REQUIRED_RULES):
            steps.append(run_step(root, "explain-" + rule, ["-m", "shadecheck.cli", "explain", rule], env))
        reports = check_artifacts(root)
        # Check the JSON report command itself, separately from file parsing.
        first_report = root / reports[0]["report"]
        rendered = backend.command([sys.executable, "-m", "shadecheck.cli", "report", "--input", str(first_report), "--format", "json"])
        require(json.loads(rendered) == json.loads(first_report.read_text()), "JSON output mismatch")
        info = backend.require_regtest()
        backend.write_json(root / "environment.json", {
            "chain": info["chain"], "node_height": info["blocks"], "node_subversion": backend.node("getnetworkinfo")["subversion"],
            "lightwalletd_revision": backend.lightd_info().gitCommit,
            "images": json.loads(backend.command(["docker", "image", "inspect", "electriccoinco/zcashd:v6.12.2", "shadecheck-regtest-lightwalletd"])),
            "setup": "Existing volumes are preserved; CI starts on a fresh runner. Test spending keys remain in developer-owned local wallet volumes."})
        artifacts = [{"path": str(p.relative_to(root)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(root.rglob("*")) if p.is_file()]
        value = {"schema_version": 1, "acceptance_status": "PASS", "privacy_status": "FAIL" if any(e["status"] == "FAIL" for e in reports) else ("WARN" if any(e["status"] == "WARN" for e in reports) else "PASS"),
                 "rules_executed": sorted(REQUIRED_RULES), "steps": steps, "reports": reports, "artifacts": artifacts,
                 "limitations": [
                     "This is a real local regtest acceptance suite with protocol-authentic clients and an instrumented native wallet; it is not a complete third-party wallet integration.",
                     "Acceptance PASS verifies expected outcomes, including privacy FAIL and missing-coverage WARN; it does not exempt findings or establish anonymity.",
                     "SC-001 tests alignment/size, SC-003 tests observed subset retrieval, SC-004 tests explicit transparent selection; documented broader behaviors remain outside coverage.",
                     "SC-005 severity escalation uses an explicitly labeled actual-event prefix and complete observation; code-change causality is not inferred.",
                     "Node release and lightwalletd source revision are pinned. Upstream lightwalletd base-image tags and package repositories can change; actual image identities are recorded, not claimed fully hermetic.",
                     "Evidence hashes are integrity checks, not author authentication. Node and native wallet adapter evidence depend on trusted local test components."]}
        backend.write_json(root / "suite.json", value)
        (root / "suite.html").write_text(summary_html(value))
        verify(root)
        print(f"SHADECHECK MVP ACCEPTANCE VERIFIED: all five rules; real backend; expected strict failures; JSON/HTML; baselines. Reports: {root}")
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        if root:
            backend.write_json(root / "suite-error.json", {"acceptance_status": "ERROR", "error": str(error)})
        print(f"Acceptance error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
