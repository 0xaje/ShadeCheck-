"""Real SC-001 comparison of narrow and fixed-size aligned block retrieval."""
from contextlib import ExitStack
import json
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

SYNC_POLICY = {"chunk_size": 20, "alignment_height": 0}


def exercise(directory, start, end, config_path, expected_exit):
    path = directory / "events.jsonl"
    proofs = []
    with ExitStack() as stack:
        recorder = Recorder(path, "upstream")
        stack.callback(recorder.close)
        upstream = stack.enter_context(grpc.insecure_channel("127.0.0.1:9067"))
        server, port = start_server(recorder, upstream=rpc.CompactTxStreamerStub(upstream))
        stack.callback(lambda: server.stop(0).wait())
        channel = stack.enter_context(grpc.insecure_channel(f"127.0.0.1:{port}"))
        grpc.channel_ready_future(channel).result(timeout=5)
        client = rpc.CompactTxStreamerStub(channel)
        blocks = list(client.GetBlockRange(
            pb.BlockRange(start=pb.BlockID(height=start), end=pb.BlockID(height=end)), timeout=30))
        if [b.height for b in blocks] != list(range(start, end + 1)):
            raise RuntimeError("Actual delivered block sequence differs from requested range")
        for block in blocks:
            actual_hash = backend.node("getblockhash", block.height)
            if block.hash[::-1].hex() != actual_hash:
                raise RuntimeError("Delivered compact block differs from canonical verifier block")
            proofs.append({"height": block.height, "block_hash": actual_hash,
                           "node_block_hash_matches": block.hash[::-1].hex() == actual_hash})
        backend.write_json(directory / "backend-proof.json", {
            "network": "regtest", "requested_start": start, "requested_end": end,
            "returned_blocks": proofs, "sync_policy": SYNC_POLICY,
            "lightwalletd_revision": backend.lightd_info().gitCommit,
            "node_subversion": backend.node("getnetworkinfo")["subversion"],
        })
    load_events(path)
    output = directory / "report.json"
    run = subprocess.run([sys.executable, "-m", "shadecheck.cli", "test",
                          "--events", str(path), "--rules", "SC-001",
                          "--config", str(config_path), "--policy", "strict",
                          "--output", str(output)], cwd=backend.ROOT)
    result = json.loads(output.read_text())
    if run.returncode != expected_exit or (expected_exit == 1 and not any(
            f["rule_id"] == "SC-001" for f in result["findings"])):
        raise RuntimeError("Actual recorded sync trace did not produce the expected policy outcome")
    backend.command([sys.executable, "-m", "shadecheck.cli", "report", "--input", str(output),
                     "--format", "html", "--output", str(directory / "report.html")])
    return {"status": result["status"], "strict_exit": run.returncode,
            "findings": len(result["findings"]), "requested_start": start, "requested_end": end,
            "delivered_blocks": len(blocks), "evidence_root": result["evidence_root"]}


def main():
    try:
        tip = backend.require_regtest()["blocks"]
        info = backend.lightd_info()
        available = min(tip, info.blockHeight)
        chunk = SYNC_POLICY["chunk_size"]
        start = ((available + 1) // chunk - 1) * chunk
        if start < 1:
            raise RuntimeError("Actual chain lacks a complete non-genesis policy chunk; run regtest.py up")
        directory = backend.OUTPUT_ROOT / "sync-pattern" / (
            time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
        config_path = directory / "policy.json"
        backend.write_json(config_path, {"schema_version": 1, "sync": SYNC_POLICY})
        narrow = exercise(directory / "narrow", start + 3, start + 9, config_path, 1)
        aligned = exercise(directory / "aligned", start, start + chunk - 1, config_path, 0)
        backend.write_json(directory / "comparison.json", {
            "rule_id": "SC-001", "sync_policy": SYNC_POLICY, "narrow": narrow, "aligned": aligned,
            "limitations": [
                "Protocol-authentic test client, not a full wallet synchronization algorithm.",
                "This declared policy is a test requirement, not a universal Zcash requirement.",
                "Actual range boundaries and sizes are observable; wallet state and identity are not proven.",
                "The test uses a completed historical chunk; live chain-tip handling remains outside coverage.",
                "Timing fingerprinting and repeated sync history are not implemented in this rule.",
                "PASS applies only to the declared SC-001 policy and executed trace, not anonymity.",
            ]})
        print(f"REAL SC-001 COMPARISON VERIFIED: narrow {narrow['status']}, aligned {aligned['status']}. Reports: {directory}")
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, grpc.RpcError, subprocess.TimeoutExpired) as error:
        print(f"Sync pattern error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
