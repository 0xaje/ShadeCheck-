"""Run an unmodified pinned Zingo wallet directly and through the observer.

No synthetic events or transactions. Wallet files/keys stay outside artifacts.
"""
import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

import grpc
import regtest as backend
from shadecheck.core import Recorder, load_events
from shadecheck.generated import service_pb2 as pb
from shadecheck.generated import service_pb2_grpc as rpc
from shadecheck.harness import start_server

COMPOSE = ["docker", "compose", "-f", str(backend.ROOT / "integration/zingo/compose.yml")]
ENDPOINT = "127.0.0.1:19067"


def command(args, timeout=180):
    result = subprocess.run(args, cwd=backend.ROOT, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:] or result.stdout[-6000:] or f"Command exited {result.returncode}")
    return result.stdout


def node(method, *args):
    return json.loads(command(COMPOSE + ["exec", "-T", "zcashd", "zcash-cli",
        "-conf=/etc/zcash/shadecheck.conf", "-datadir=/data", method, *map(str, args)]))


def wait_backend():
    deadline = time.monotonic() + 180
    last = "not ready"
    while time.monotonic() < deadline:
        try:
            chain = node("getblockchaininfo")
            if chain["chain"] != "regtest":
                raise ValueError("Refusing non-regtest node")
            with grpc.insecure_channel(ENDPOINT) as channel:
                info = rpc.CompactTxStreamerStub(channel).GetLightdInfo(pb.Empty(), timeout=5)
            if info.chainName != "regtest":
                raise ValueError("Refusing non-regtest lightwalletd")
            if info.blockHeight == chain["blocks"] and chain["blocks"] >= 110:
                return chain, info
        except (RuntimeError, grpc.RpcError) as error:
            last = str(error)
        time.sleep(2)
    raise RuntimeError(f"Isolated backend not ready: {last}")


def parse_sync_status(output):
    decoder = json.JSONDecoder()
    candidates = []
    for index, char in enumerate(output):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
        except ValueError:
            continue
        if isinstance(value, dict) and "percentage_total_blocks_scanned" in value:
            candidates.append(value)
    if not candidates:
        raise RuntimeError("Zingo did not return a sync status document")
    status = candidates[-1]
    if (status.get("percentage_total_blocks_scanned") != 100
            or status.get("total_blocks_scanned", 0) <= 0):
        raise RuntimeError(f"Zingo did not complete block scanning: {status}")
    return status


def run_wallet(binary, endpoint, wallet_dir, artifacts):
    # Each run gets a new wallet. Never export wallet files, seed phrases or keys.
    wallet_dir.mkdir(parents=True, exist_ok=False)
    args = [str(binary), "--chain", "regtest", "--server", f"http://{endpoint}",
            "--data-dir", str(wallet_dir), "--waitsync", "sync", "status"]
    run = subprocess.run(args, cwd=wallet_dir, capture_output=True, text=True, timeout=180)
    # These commands never ask the client to print a seed/key. Keep diagnostics
    # local on failure; only export the parsed, nonsecret sync status on success.
    if run.returncode:
        (wallet_dir / "failure.log").write_text(run.stdout + "\n" + run.stderr)
        raise RuntimeError(f"Zingo exited {run.returncode}; private diagnostics: {wallet_dir / 'failure.log'}")
    try:
        status = parse_sync_status(run.stdout)
    except RuntimeError:
        (wallet_dir / "failure.log").write_text(run.stdout + "\n" + run.stderr)
        raise RuntimeError(f"Zingo sync validation failed; private diagnostics: {wallet_dir / 'failure.log'}")
    backend.write_json(artifacts / "client-sync.json", {"process_exit": run.returncode, "sync_status": status})
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Pinned upstream checkout with built target/release/zingo-cli")
    args = parser.parse_args()
    pin = json.loads((backend.ROOT / "integration/zingo/client.json").read_text())
    source = args.source.resolve()
    binary = source / "target/release/zingo-cli"
    directory = backend.OUTPUT_ROOT / "zingo" / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    try:
        actual = command(["git", "-C", str(source), "rev-parse", "HEAD"]).strip()
        if actual != pin["revision"] or command(["git", "-C", str(source), "diff", "HEAD", "--"]).strip():
            raise ValueError("Requires the pinned unmodified upstream source checkout")
        binary_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
        version = command([str(binary), "--version"]).strip()
        print("Starting separate Zingo regtest backend (existing MVP volumes are untouched)...", flush=True)
        command(COMPOSE + ["up", "-d", "zcashd"], timeout=600)
        deadline = time.monotonic() + 180
        while True:
            try:
                chain = node("getblockchaininfo")
                if chain["chain"] != "regtest":
                    raise ValueError("Refusing non-regtest node")
                break
            except RuntimeError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(2)
        if chain["blocks"] < 110:
            node("generate", 110 - chain["blocks"])
        subprocess.run(COMPOSE + ["up", "-d", "--build", "lightwalletd"], check=True, timeout=1200)
        chain, info = wait_backend()
        tip = chain["blocks"]
        private = backend.ROOT / ".shadecheck/zingo-wallets" / directory.name
        print("Validating direct upstream wallet synchronization...", flush=True)
        direct = run_wallet(binary, ENDPOINT, private / "direct", directory / "direct")
        print("Validating the same upstream client through ShadeCheck...", flush=True)
        observed = directory / "observed"
        with ExitStack() as stack:
            recorder = Recorder(observed / "events.jsonl", "upstream")
            stack.callback(recorder.close)
            channel = stack.enter_context(grpc.insecure_channel(ENDPOINT))
            server, port = start_server(recorder, upstream=rpc.CompactTxStreamerStub(channel))
            stack.callback(lambda: server.stop(0).wait())
            proxied = run_wallet(binary, f"127.0.0.1:{port}", private / "observed", observed)
        events = load_events(observed / "events.jsonl")
        responses = [e for e in events if e["method"] == "GetBlockRange" and e["phase"] == "response"]
        if not responses:
            raise RuntimeError("No actual wallet block-range responses captured")
        verified = {}
        for event in responses:
            height = event["metadata"]["height"]
            if height not in verified:
                block_hash = node("getblockhash", height)
                if bytes.fromhex(event["metadata"]["block_hash"])[::-1].hex() != block_hash:
                    raise RuntimeError("Wallet received a noncanonical compact block")
                verified[height] = block_hash
        if node("getblockchaininfo")["blocks"] != tip:
            raise RuntimeError("Backend chain changed during comparison")
        config = directory / "policy.json"
        backend.write_json(config, {"schema_version": 1, "sync": {"chunk_size": 20, "alignment_height": 0},
                                   "payment": {"require_shielded": True}})
        report = observed / "report.json"
        gate = subprocess.run([sys.executable, "-m", "shadecheck.cli", "test", "--events", str(observed / "events.jsonl"),
            "--rules", "SC-001", "SC-002", "SC-003", "SC-004", "--config", str(config),
            "--policy", "strict", "--output", str(report)], cwd=backend.ROOT)
        result = json.loads(report.read_text())
        if gate.returncode != {"PASS": 0, "FAIL": 1, "WARN": 2}[result["status"]]:
            raise RuntimeError("Policy status and actual process exit disagree")
        command([sys.executable, "-m", "shadecheck.cli", "report", "--input", str(report),
                 "--format", "html", "--output", str(observed / "report.html")])
        backend.write_json(directory / "integration.json", {
            "integration_status": "VERIFIED", "client": {**pin, "binary_sha256": binary_hash, "version": version},
            "network": "regtest", "node_subversion": node("getnetworkinfo")["subversion"],
            "lightwalletd_revision": info.gitCommit, "chain_height": tip,
            "direct_sync_status": direct, "observed_sync_status": proxied,
            "canonical_blocks_verified": verified,
            "rpc_requests": dict(Counter(e["method"] for e in events if e["phase"] == "request")),
            "rpc_errors": dict(Counter(e["metadata"].get("grpc_code") for e in events if e["phase"] == "error")),
            "privacy_status": result["status"], "strict_exit": gate.returncode, "coverage": result["rules"],
            "evidence_root": result["evidence_root"], "limitations": [
                "Pinned historical release; no claim about latest Zingo, mobile clients, or default production behavior.",
                "Fresh, unfunded wallets on local regtest; no independent-client payment/broadcast tested.",
                "SC-001 uses an explicitly chosen test policy, not a universal Zcash or Zingo requirement.",
                "Chain-tip ranges can violate this fixed-chunk test policy; a finding alone is not a wallet vulnerability.",
                "Compatibility RPC forwarding does not add privacy rule coverage.",
                "No SC-005 comparison in this integration; missing coverage cannot establish anonymity.",
                "An independently developed client integration is not third-party adoption or endorsement."]})
        print(f"INDEPENDENT ZINGO SYNC VERIFIED: direct and observed scanning completed; {len(verified)} canonical blocks. Privacy {result['status']}. Reports: {directory}")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, grpc.RpcError, subprocess.SubprocessError) as error:
        backend.write_json(directory / "integration-error.json", {"integration_status": "FAILED", "error": str(error)})
        print(f"Zingo integration error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
