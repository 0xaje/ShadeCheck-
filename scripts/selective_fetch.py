"""Real SC-003 subset-versus-complete compact transaction retrieval test."""
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


def exercise(directory, height, expected_ids, fetch_all):
    events_path = directory / "events.jsonl"
    with ExitStack() as stack:
        recorder = Recorder(events_path, "upstream")
        stack.callback(recorder.close)
        upstream = stack.enter_context(grpc.insecure_channel("127.0.0.1:9067"))
        server, port = start_server(recorder, upstream=rpc.CompactTxStreamerStub(upstream))
        stack.callback(lambda: server.stop(0).wait())
        channel = stack.enter_context(grpc.insecure_channel(f"127.0.0.1:{port}"))
        grpc.channel_ready_future(channel).result(timeout=5)
        client = rpc.CompactTxStreamerStub(channel)
        blocks = list(client.GetBlockRange(pb.BlockRange(start=pb.BlockID(height=height),
                                                        end=pb.BlockID(height=height)), timeout=30))
        if len(blocks) != 1 or blocks[0].height != height:
            raise RuntimeError("Actual compact block delivery did not match requested height")
        block = blocks[0]
        ids = [tx.txid for tx in block.vtx]
        if not expected_ids.issubset(set(ids)) or len(set(ids)) < 2:
            raise RuntimeError("Actual compact block does not contain both real setup transactions")
        canonical_block = backend.node("getblock", backend.node("getblockhash", height))
        if block.hash[::-1].hex() != canonical_block["hash"]:
            raise RuntimeError("Observed compact block differs from verifier canonical block")
        requested = ids if fetch_all else [next(iter(sorted(expected_ids)))]
        proofs = []
        for txid in requested:
            raw = client.GetTransaction(pb.TxFilter(hash=txid), timeout=15)
            text_id = txid[::-1].hex()
            actual_hex = backend.node("getrawtransaction", text_id)
            verbose = backend.node("getrawtransaction", text_id, 1)
            if raw.height != height or bytes.fromhex(actual_hex) != raw.data or verbose["blockhash"] != canonical_block["hash"]:
                raise RuntimeError("Fetched transaction bytes or confirmed block disagrees with node RPC")
            proofs.append({"txid": text_id, "node_raw_transaction_matches": True,
                           "confirmed_block_matches": True, "returned_height": raw.height})
        backend.write_json(directory / "backend-proof.json", {
            "network": "regtest", "block_height": height, "block_hash": canonical_block["hash"],
            "compact_transaction_ids_protocol_order": [x.hex() for x in ids],
            "fetches": proofs, "client_behavior": "fetch-all-compact-transactions" if fetch_all else "fetch-one-compact-transaction",
            "lightwalletd_revision": backend.lightd_info().gitCommit,
        })
    load_events(events_path)
    output = directory / "report.json"
    run = subprocess.run([sys.executable, "-m", "shadecheck.cli", "test", "--events", str(events_path),
                          "--rules", "SC-003", "--policy", "strict", "--output", str(output)], cwd=backend.ROOT)
    report = json.loads(output.read_text())
    expected_exit = 0 if fetch_all else 1
    if run.returncode != expected_exit or (not fetch_all and not any(f["rule_id"] == "SC-003" for f in report["findings"])):
        raise RuntimeError("Actual captured behavior did not produce the expected SC-003 policy result")
    backend.command([sys.executable, "-m", "shadecheck.cli", "report", "--input", str(output),
                     "--format", "html", "--output", str(directory / "report.html")])
    return {"status": report["status"], "strict_exit": run.returncode,
            "findings": len(report["findings"]), "evidence_root": report["evidence_root"]}


def main():
    try:
        backend.require_regtest()
        backend.prepare_shielded()
        first = json.loads(backend.STATE.read_text())
        # Construct a second real shielded-output transaction while keeping the first
        # absent from the verifier until both can be mined together.
        address = backend.node("getnewaddress", service="wallet")
        funding = backend.node("sendtoaddress", address, 1)
        backend.node("generate", 1)
        backend.sync_wallet_chain()
        backend.wait_wallet_confirmation(funding)
        receiver = backend.node("z_getnewaddress", "sapling", service="wallet")
        second_id = backend.wallet_payment(address, receiver, 0.9998, "AllowRevealedSenders")
        second_hex = backend.node("getrawtransaction", second_id, service="wallet")
        if not backend.node("decoderawtransaction", second_hex).get("vShieldedOutput"):
            raise RuntimeError("Second real transaction has no Sapling output")
        for text_id, raw in [(first["txid"], first["hex"]), (second_id, second_hex)]:
            if backend.node("sendrawtransaction", raw) != text_id:
                raise RuntimeError("Verifier failed real setup submission")
        backend.node("generate", 1)
        height = backend.require_regtest()["blocks"]
        expected_ids = {bytes.fromhex(first["txid"])[::-1], bytes.fromhex(second_id)[::-1]}
        # Wait for actual lightwalletd cache readiness without recording setup polling
        # as the measured client scenario.
        deadline = time.monotonic() + 60
        while backend.lightd_info().blockHeight < height:
            if time.monotonic() >= deadline:
                raise RuntimeError("lightwalletd did not reach actual confirmed test block")
            time.sleep(0.5)
        directory = backend.OUTPUT_ROOT / "selective-fetch" / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
        subset = exercise(directory / "subset", height, expected_ids, False)
        complete = exercise(directory / "complete", height, expected_ids, True)
        backend.write_json(directory / "comparison.json", {
            "rule_id": "SC-003", "subset": subset, "complete": complete,
            "setup_transactions": [first["txid"], second_id],
            "limitations": ["Protocol-authentic test client; this is not a full wallet relevance scanner.",
                            "Delivery does not prove internal wallet processing or transaction ownership.",
                            "Complete fetch covers only compact transactions returned in this block, not every chain transaction.",
                            "PASS applies only to SC-003 in this executed finite trace; it does not establish anonymity."]})
        print(f"REAL SC-003 COMPARISON VERIFIED: subset {subset['status']}, complete {complete['status']}. Reports: {directory}")
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, grpc.RpcError, subprocess.TimeoutExpired) as error:
        print(f"Selective fetch error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
