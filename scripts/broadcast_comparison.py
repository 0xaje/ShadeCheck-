"""Real regtest comparison of unified versus separated RPC observer roles."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

# Direct scripts execution supplies this directory on sys.path.
import regtest as backend
import grpc
from shadecheck.core import Recorder, load_events
from shadecheck.generated import service_pb2 as pb
from shadecheck.generated import service_pb2_grpc as rpc
from shadecheck.harness import start_server


def report(directory, recorder_path, expected_exit):
    load_events(recorder_path)
    output = directory / "report.json"
    run = subprocess.run([sys.executable, "-m", "shadecheck.cli", "test",
                          "--events", str(recorder_path), "--policy", "strict",
                          "--output", str(output)], cwd=backend.ROOT)
    if run.returncode != expected_exit:
        raise RuntimeError(f"Unexpected policy exit {run.returncode} for {directory}")
    backend.command([sys.executable, "-m", "shadecheck.cli", "report", "--input", str(output),
                     "--format", "html", "--output", str(directory / "report.html")])
    return json.loads(output.read_text())


def exercise(directory, separated):
    backend.prepare_shielded()
    tx = json.loads(backend.STATE.read_text())
    raw = bytes.fromhex(tx["hex"])
    structure = backend.shielded_structure(backend.node("decoderawtransaction", tx["hex"]))
    if tx["txid"] in backend.node("getrawmempool"):
        raise RuntimeError("Measured transaction already present at verifier")
    read_path = directory / "read-observer" / "events.jsonl"
    broadcast_path = directory / "broadcast-observer" / "events.jsonl" if separated else read_path
    with ExitStack() as stack:
        read_recorder = Recorder(read_path, "upstream")
        stack.callback(read_recorder.close)
        broadcast_recorder = Recorder(broadcast_path, "upstream") if separated else read_recorder
        if separated:
            stack.callback(broadcast_recorder.close)
        upstream = stack.enter_context(grpc.insecure_channel("127.0.0.1:9067"))
        stub = rpc.CompactTxStreamerStub(upstream)
        read_server, read_port = start_server(read_recorder, upstream=stub)
        stack.callback(lambda: read_server.stop(0).wait())
        if separated:
            broadcast_server, broadcast_port = start_server(broadcast_recorder, upstream=stub)
            stack.callback(lambda: broadcast_server.stop(0).wait())
        else:
            broadcast_port = read_port
        read_channel = stack.enter_context(grpc.insecure_channel(f"127.0.0.1:{read_port}"))
        grpc.channel_ready_future(read_channel).result(timeout=5)
        reader = rpc.CompactTxStreamerStub(read_channel)
        tip = reader.GetLatestBlock(pb.ChainSpec(), timeout=15)
        if tip.height != backend.require_regtest()["blocks"]:
            raise RuntimeError("Observed lightwalletd tip does not match actual verifier")
        if separated:
            broadcast_channel = stack.enter_context(grpc.insecure_channel(f"127.0.0.1:{broadcast_port}"))
            grpc.channel_ready_future(broadcast_channel).result(timeout=5)
            broadcaster = rpc.CompactTxStreamerStub(broadcast_channel)
        else:
            broadcaster = reader
        response = broadcaster.SendTransaction(pb.RawTransaction(data=raw), timeout=15)
        if response.errorCode != 0:
            raise RuntimeError(f"Verifier rejected transaction: {response.errorMessage}")
        backend.observe_matching_mempool(reader, raw)
        if separated:
            backend.observe_matching_mempool(broadcaster, raw)
        if tx["txid"] not in backend.node("getrawmempool") or bytes.fromhex(backend.node("getrawtransaction", tx["txid"])) != raw:
            raise RuntimeError("Independent verifier confirmation failed")
        backend.write_json(directory / "backend-proof.json", {
            "txid": tx["txid"], "transaction_kind": tx["transaction_kind"],
            "decoded_structure": structure, "payload_sha256": hashlib.sha256(raw).hexdigest(),
            "send_response_code": response.errorCode, "send_response_message": response.errorMessage,
            "node_mempool_contains_txid": True, "node_raw_transaction_matches": True,
            "construction": tx["construction"], "setup_transactions": tx["setup_transactions"],
            "read_observed_height": tip.height,
            "lightwalletd_revision": backend.lightd_info().gitCommit,
            "node_subversion": backend.node("getnetworkinfo")["subversion"],
        })
    read_report = report(read_path.parent, read_path, 2 if separated else 1)
    broadcast_report = report(broadcast_path.parent, broadcast_path, 1) if separated else read_report
    read_events = load_events(read_path)
    read_sends = [e for e in read_events if e["method"] == "SendTransaction" and e["phase"] == "request"]
    matches = [e for e in read_events if e["method"] == "GetMempoolStream" and e["phase"] == "response"
               and e["metadata"].get("payload_sha256") == hashlib.sha256(raw).hexdigest()]
    reads = [e for e in read_events if e["method"] == "GetLatestBlock" and e["phase"] == "request"]
    if not matches or not reads or (separated and read_sends) or (not separated and not read_sends):
        raise RuntimeError("Captured observer role evidence does not match exercised routing")
    if not separated and reads[0]["session"] != read_sends[0]["session"]:
        raise RuntimeError("Unified read and broadcast did not use the same actual transport session")
    if not any(f["severity"] == "HIGH" for f in broadcast_report["findings"]):
        raise RuntimeError("Broadcast observer lost actual SC-002 coverage")
    return {"read_observer": {"status": read_report["status"], "findings": len(read_report["findings"]),
                              "submission_requests": len(read_sends), "matching_mempool_events": len(matches),
                              "evidence_root": read_report["evidence_root"]},
            "broadcast_observer": {"status": broadcast_report["status"], "findings": len(broadcast_report["findings"]),
                                   "evidence_root": broadcast_report["evidence_root"]}}


def main():
    try:
        backend.require_regtest()
        backend.lightd_info()
        directory = backend.ROOT / "out/comparison" / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
        unified = exercise(directory / "unified", False)
        separated = exercise(directory / "separated", True)
        comparison = {"schema_version": 1, "unified": unified, "separated": separated,
                      "limitations": ["The broadcast observer still links submission bytes to its transport peer.",
                                      "No broadcast at the read observer means missing SC-002 coverage, not PASS.",
                                      "Both local observer roles share one verifier/lightwalletd backend; this is not service independence.",
                                      "Colluding observers or the shared backend can correlate transaction fingerprints and timing.",
                                      "This controlled routing comparison does not establish anonymity or production mitigation."]}
        backend.write_json(directory / "comparison.json", comparison)
        print(json.dumps(comparison, indent=2))
        print(f"REAL OBSERVER-ROLE COMPARISON VERIFIED: {directory}")
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, grpc.RpcError, subprocess.TimeoutExpired) as error:
        print(f"Comparison error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
