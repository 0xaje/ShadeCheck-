"""Real SC-004 permissive recipient versus enforced FullPrivacy comparison."""
from contextlib import ExitStack
import hashlib
import json
import re
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

POLICY = {"require_shielded": True}
ADAPTER = "local-wallet-adapter; not a passive transport peer"


def record(recorder, method, phase, **metadata):
    # Preserve exact decimal RPC values as strings in canonical JSON evidence.
    normalized = json.loads(json.dumps(metadata, default=str))
    return recorder.record(method, phase, ADAPTER, source_mode="wallet-adapter", **normalized)


def fund_source():
    backend.prepare_shielded()
    setup = json.loads(backend.STATE.read_text())
    if backend.node("sendrawtransaction", setup["hex"]) != setup["txid"]:
        raise RuntimeError("Verifier rejected the real shielded setup payment")
    backend.node("generate", 1)
    backend.sync_wallet_chain()
    backend.wait_wallet_confirmation(setup["txid"])
    return setup["receiver_address"], setup["txid"]


def wallet_attempt(recorder, flow, sender, receiver, privacy):
    validation = backend.node("validateaddress", receiver, service="wallet")
    if validation.get("isvalid"):
        kind = "transparent"
    else:
        validation = backend.node("z_validateaddress", receiver, service="wallet")
        if not validation.get("isvalid"):
            raise RuntimeError("Actual wallet RPC did not validate the selected receiver")
        kind = "shielded"
    seq = record(recorder, "WalletPayment", "request", flow_id=flow,
                 receiver=receiver, receiver_type=kind, receiver_validation=validation,
                 privacy_policy=privacy, amount="0.1", fee="0.0002",
                 source_rpc="z_sendmany", require_shielded=POLICY["require_shielded"])
    operation = None
    try:
        operation = backend.node("z_sendmany", sender, [{"address": receiver, "amount": 0.1}],
                                 1, 0.0002, privacy, service="wallet")
    except RuntimeError as error:
        code_match = re.search(r"error code:\s*(-?\d+)", str(error))
        record(recorder, "WalletPayment", "error", flow_id=flow, request_sequence=seq,
               error=str(error), error_code=int(code_match.group(1)) if code_match else None,
               source_rpc="z_sendmany")
        return None, seq, str(error)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        states = backend.node("z_getoperationstatus", [operation], service="wallet")
        if not states:
            raise RuntimeError("Wallet lost the measured asynchronous operation")
        state = states[0]
        if state["status"] == "success":
            txid = state["result"]["txid"]
            record(recorder, "WalletPayment", "response", flow_id=flow, request_sequence=seq,
                   operation_result=state, txid=txid, source_rpc="z_getoperationstatus")
            return txid, seq, None
        if state["status"] in {"failed", "cancelled"}:
            error = state.get("error", state)
            record(recorder, "WalletPayment", "error", flow_id=flow, request_sequence=seq,
                   error=error, error_code=error.get("code") if isinstance(error, dict) else None,
                   operation_result=state, source_rpc="z_getoperationstatus")
            return None, seq, str(error)
        time.sleep(0.5)
    raise RuntimeError("Measured wallet operation timed out")


def exercise(directory, config_path, hardened):
    sender, setup_txid = fund_source()
    transparent_receiver = backend.node("getnewaddress")
    path = directory / "events.jsonl"
    flow = uuid.uuid4().hex
    with ExitStack() as stack:
        recorder = Recorder(path, "upstream")
        stack.callback(recorder.close)
        privacy = "FullPrivacy" if hardened else "AllowRevealedRecipients"
        txid, seq, error = wallet_attempt(recorder, flow, sender, transparent_receiver, privacy)
        if hardened:
            if txid is not None or "privacy" not in str(error).lower():
                raise RuntimeError("FullPrivacy did not reject the actual transparent recipient for a privacy reason")
            receiver = backend.node("z_getnewaddress", "sapling", service="wallet")
            txid, seq, error = wallet_attempt(recorder, flow, sender, receiver, "FullPrivacy")
        if txid is None:
            raise RuntimeError(f"Wallet did not construct the measured payment: {error}")
        raw_hex = backend.node("getrawtransaction", txid, service="wallet")
        decoded = backend.node("decoderawtransaction", raw_hex)
        if decoded["txid"] != txid:
            raise RuntimeError("Actual node decoder disagrees with measured wallet txid")
        structure = {"transparent_inputs": len(decoded["vin"]), "transparent_outputs": len(decoded["vout"]),
                     "sapling_spends": len(decoded.get("vShieldedSpend", [])),
                     "sapling_outputs": len(decoded.get("vShieldedOutput", []))}
        if hardened:
            backend.shielded_structure(decoded)
        elif not structure["sapling_spends"] or not structure["transparent_outputs"]:
            raise RuntimeError("Permissive path did not create an actual Sapling-to-transparent transaction")
        raw = bytes.fromhex(raw_hex)
        if txid in backend.node("getrawmempool"):
            raise RuntimeError("Measured transaction already exists at verifier")
        record(recorder, "WalletTransaction", "response", flow_id=flow, request_sequence=seq,
               source_rpc="decoderawtransaction", txid=txid,
               payload_sha256=hashlib.sha256(raw).hexdigest(), **structure)
        upstream = stack.enter_context(grpc.insecure_channel("127.0.0.1:9067"))
        server, port = start_server(recorder, upstream=rpc.CompactTxStreamerStub(upstream))
        stack.callback(lambda: server.stop(0).wait())
        channel = stack.enter_context(grpc.insecure_channel(f"127.0.0.1:{port}"))
        grpc.channel_ready_future(channel).result(timeout=5)
        client = rpc.CompactTxStreamerStub(channel)
        response = client.SendTransaction(pb.RawTransaction(data=raw), timeout=15)
        if response.errorCode != 0:
            raise RuntimeError(f"Verifier rejected payment bytes: {response.errorMessage}")
        backend.observe_matching_mempool(client, raw)
        in_pool = txid in backend.node("getrawmempool")
        matches = bytes.fromhex(backend.node("getrawtransaction", txid)) == raw
        if not in_pool or not matches:
            raise RuntimeError("Independent verifier confirmation failed")
        backend.write_json(directory / "backend-proof.json", {
            "network": "regtest", "setup_transaction": setup_txid, "txid": txid,
            "decoded_transaction": decoded, "decoded_structure": structure,
            "payment_policy": POLICY, "wallet_privacy_policy": privacy,
            "node_mempool_contains_txid": in_pool, "node_raw_transaction_matches": matches,
            "send_response_code": response.errorCode, "send_response_message": response.errorMessage,
            "payload_sha256": hashlib.sha256(raw).hexdigest(),
            "construction": "real local zcashd wallet, locally accepted before first verifier submission",
            "lightwalletd_revision": backend.lightd_info().gitCommit,
        })
    load_events(path)
    output = directory / "report.json"
    run = subprocess.run([sys.executable, "-m", "shadecheck.cli", "test", "--events", str(path),
                          "--rules", "SC-004", "--config", str(config_path),
                          "--policy", "strict", "--output", str(output)], cwd=backend.ROOT)
    result = json.loads(output.read_text())
    expected = 0 if hardened else 1
    if run.returncode != expected or (not hardened and not any(
            f["rule_id"] == "SC-004" and f["severity"] == "HIGH" for f in result["findings"])):
        raise RuntimeError("Real payment evidence did not produce the expected SC-004 result")
    backend.command([sys.executable, "-m", "shadecheck.cli", "report", "--input", str(output),
                     "--format", "html", "--output", str(directory / "report.html")])
    return {"status": result["status"], "strict_exit": run.returncode,
            "findings": len(result["findings"]), "decoded_structure": structure,
            "evidence_root": result["evidence_root"]}


def main():
    try:
        backend.require_regtest()
        backend.lightd_info()
        directory = backend.OUTPUT_ROOT / "transparent-fallback" / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
        config = directory / "policy.json"
        backend.write_json(config, {"schema_version": 1, "payment": POLICY})
        weak = exercise(directory / "permissive", config, False)
        hardened = exercise(directory / "full-privacy", config, True)
        comparison = {"rule_id": "SC-004", "payment_policy": POLICY,
                      "permissive": weak, "full_privacy": hardened,
                      "limitations": ["Instrumented native-wallet payment adapter, not passive receiver inference.",
                                      "Tests an explicit transparent recipient path; automatic Unified Address fallback is not implemented.",
                                      "Wallet adapter receipts depend on the trusted local test driver and node RPC.",
                                      "PASS is scoped to the shielded requirement in this executed flow, not anonymity."]}
        backend.write_json(directory / "comparison.json", comparison)
        print(json.dumps(comparison, indent=2))
        print(f"REAL SC-004 COMPARISON VERIFIED: permissive {weak['status']}, FullPrivacy {hardened['status']}. Reports: {directory}")
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, grpc.RpcError, subprocess.TimeoutExpired) as error:
        print(f"Transparent fallback error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
