"""Drive the dedicated Docker regtest node. Never accepts a public RPC URL."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

import grpc
from shadecheck.core import Recorder, load_events
from shadecheck.generated import service_pb2 as pb
from shadecheck.generated import service_pb2_grpc as rpc
from shadecheck.harness import start_server

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "integration/compose.yml")]
STATE = ROOT / ".shadecheck/regtest/transaction.json"


def command(args, timeout=180):
    run = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if run.returncode:
        raise RuntimeError(run.stderr.strip() or run.stdout.strip() or f"Command failed: {args[0]}")
    return run.stdout.strip()


def compose(*args, timeout=180):
    return command(COMPOSE + list(args), timeout)


def node(method, *params, service="zcashd"):
    if service not in {"zcashd", "wallet"}:
        raise ValueError("Unknown dedicated regtest service")
    encoded = [json.dumps(p, separators=(",", ":")) if isinstance(p, (dict, list, bool))
               else str(p) for p in params]
    result = compose("exec", "-T", service, "zcash-cli",
                     "-conf=/etc/zcash/shadecheck.conf", "-datadir=/data", method, *encoded)
    try:
        return json.loads(result, parse_float=Decimal)
    except json.JSONDecodeError:
        return result


def require_regtest(service="zcashd"):
    info = node("getblockchaininfo", service=service)
    if info.get("chain") != "regtest":
        raise RuntimeError("Refusing to operate: node is not regtest")
    return info


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def wait_node(service="zcashd"):
    deadline = time.monotonic() + 180
    last_error = ""
    while time.monotonic() < deadline:
        try:
            return require_regtest(service)
        except RuntimeError as error:
            last_error = str(error)
            exited = compose("ps", "--all", "--status", "exited", "--quiet", service)
            if exited:
                raise RuntimeError("Node exited during startup:\n" + compose("logs", "--tail", "60", service)) from error
            time.sleep(2)
    raise RuntimeError(f"Node did not become ready: {last_error}")


def lightd_info():
    with grpc.insecure_channel("127.0.0.1:9067") as channel:
        info = rpc.CompactTxStreamerStub(channel).GetLightdInfo(pb.Empty(), timeout=5)
    if info.chainName != "regtest":
        raise RuntimeError(f"Refusing unexpected lightwalletd chain: {info.chainName}")
    return info


def wait_lightd():
    deadline = time.monotonic() + 180
    last_error = ""
    while time.monotonic() < deadline:
        try:
            return lightd_info()
        except (RuntimeError, grpc.RpcError) as error:
            last_error = str(error)
            time.sleep(2)
    raise RuntimeError(f"lightwalletd did not become ready: {last_error}")


def up():
    command(["docker", "info"], timeout=15)
    compose("config", "--quiet")
    print("Starting the pinned local regtest node...", flush=True)
    compose("up", "-d", "zcashd", timeout=600)
    info = wait_node()
    if info["blocks"] < 110:
        print("Generating local blocks to activate Sapling and mature wallet coins...", flush=True)
        node("generate", 110 - info["blocks"])
    print("Building the pinned lightwalletd revision; the first build may take several minutes...", flush=True)
    # Inherit output so build progress is visible to the developer and CI.
    subprocess.run(COMPOSE + ["up", "-d", "--build", "lightwalletd"],
                   cwd=ROOT, check=True, timeout=1200)
    wait_lightd()
    check()


def check():
    chain = require_regtest()
    lightd = lightd_info()
    print(json.dumps({"node_chain": chain["chain"], "node_height": chain["blocks"],
                      "node_subversion": node("getnetworkinfo")["subversion"],
                      "lightwalletd_chain": lightd.chainName,
                      "lightwalletd_height": lightd.blockHeight,
                      "lightwalletd_revision": lightd.gitCommit}, indent=2))


def prepare():
    require_regtest()
    coins = [c for c in node("listunspent", 101) if c.get("spendable") and Decimal(c["amount"]) > Decimal("0.001")]
    if not coins:
        raise RuntimeError("No mature spendable local coins. Run the up command first.")
    coin = coins[0]
    recipient = node("getnewaddress")
    amount = Decimal(coin["amount"]) - Decimal("0.0001")
    inputs = [{"txid": coin["txid"], "vout": coin["vout"]}]
    raw = node("createrawtransaction", inputs, {recipient: float(amount)})
    signed = node("signrawtransaction", raw)
    if not signed.get("complete"):
        raise RuntimeError("The local wallet did not completely sign the transaction")
    decoded = node("decoderawtransaction", signed["hex"])
    txid = decoded["txid"]
    if txid in node("getrawmempool"):
        raise RuntimeError("Prepared transaction was already submitted")
    write_json(STATE, {"network": "regtest", "transaction_kind": "transparent",
                       "hex": signed["hex"], "txid": txid, "input": inputs[0],
                       "payload_sha256": hashlib.sha256(bytes.fromhex(signed["hex"])).hexdigest()})
    print(f"Signed local transparent transaction prepared, NOT broadcast: {txid}")
    print(f"State: {STATE}")


def shielded_structure(decoded):
    result = {
        "transparent_inputs": len(decoded.get("vin", [])),
        "transparent_outputs": len(decoded.get("vout", [])),
        "sapling_spends": len(decoded.get("vShieldedSpend", [])),
        "sapling_outputs": len(decoded.get("vShieldedOutput", [])),
        "sprout_joinsplits": len(decoded.get("vjoinsplit", [])),
    }
    if (result["transparent_inputs"] or result["transparent_outputs"]
            or result["sprout_joinsplits"] or not result["sapling_spends"]
            or not result["sapling_outputs"]):
        raise RuntimeError("Transaction does not satisfy the Sapling-to-Sapling structure requirement")
    return result


def sync_wallet_chain():
    target = require_regtest()
    source = require_regtest("wallet")
    if source["blocks"] > target["blocks"]:
        raise RuntimeError("Wallet node is ahead of verifier; refusing to replace or rewind its chain")
    wallet_tip = source["bestblockhash"]
    if node("getblockhash", source["blocks"]) != wallet_tip:
        raise RuntimeError("Wallet chain diverged from verifier; refusing a silent reset")
    for height in range(source["blocks"] + 1, target["blocks"] + 1):
        block_hash = node("getblockhash", height)
        block = node("getblock", block_hash, 0)
        status = node("submitblock", block, service="wallet")
        if status is not None:
            raise RuntimeError(f"Wallet rejected canonical block {height}: {status}")
        if height % 25 == 0:
            print(f"Wallet imported actual canonical block {height}", flush=True)
    if require_regtest("wallet")["bestblockhash"] != target["bestblockhash"]:
        raise RuntimeError("Wallet failed to synchronize to the verifier's exact chain tip")


def wallet_payment(sender, receiver, amount, privacy):
    operation = node("z_sendmany", sender, [{"address": receiver, "amount": amount}],
                     1, 0.0001, privacy, service="wallet")
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        statuses = node("z_getoperationstatus", [operation], service="wallet")
        if not statuses:
            raise RuntimeError("Wallet lost the asynchronous operation")
        status = statuses[0]
        if status["status"] == "success":
            return status["result"]["txid"]
        if status["status"] in {"failed", "cancelled"}:
            raise RuntimeError(f"Actual wallet operation failed: {status.get('error', status)}")
        time.sleep(1)
    raise RuntimeError(f"Wallet operation did not finish: {operation}")


def prepare_shielded():
    require_regtest()
    lightd_info()
    print("Starting isolated local wallet node...", flush=True)
    compose("up", "-d", "wallet", timeout=600)
    wait_node("wallet")
    if node("getconnectioncount", service="wallet") != 0:
        raise RuntimeError("Wallet node has peers; refusing an uncontrolled broadcast path")
    if node("getconnectioncount") != 0:
        raise RuntimeError("Verifier node has peers; refusing this isolated proof setup")
    # Setup payments and block imports are real, but are not the measured SC-002 transaction.
    funding_address = node("getnewaddress", service="wallet")
    print("Funding wallet with a real setup payment and importing canonical blocks...", flush=True)
    funding_txid = node("sendtoaddress", funding_address, 1)
    node("generate", 1)
    sync_wallet_chain()
    sender = node("z_getnewaddress", "sapling", service="wallet")
    receiver = node("z_getnewaddress", "sapling", service="wallet")
    print("Building real Sapling funding transaction on wallet node...", flush=True)
    shielding_txid = wallet_payment(funding_address, sender, 0.5, "AllowRevealedSenders")
    shielding_hex = node("getrawtransaction", shielding_txid, service="wallet")
    if not node("decoderawtransaction", shielding_hex).get("vShieldedOutput"):
        raise RuntimeError("Setup payment did not create an actual Sapling output")
    if node("sendrawtransaction", shielding_hex) != shielding_txid:
        raise RuntimeError("Verifier did not accept the exact Sapling funding transaction")
    node("generate", 1)
    sync_wallet_chain()
    print("Building fully shielded Sapling-to-Sapling transaction with real proofs...", flush=True)
    txid = wallet_payment(sender, receiver, 0.25, "FullPrivacy")
    raw = node("getrawtransaction", txid, service="wallet")
    decoded = node("decoderawtransaction", raw)
    structure = shielded_structure(decoded)
    if decoded["txid"] != txid:
        raise RuntimeError("Verifier's decoder disagrees with wallet txid")
    if txid in node("getrawmempool"):
        raise RuntimeError("Measured transaction is already in verifier mempool")
    if txid not in node("getrawmempool", service="wallet"):
        raise RuntimeError("Wallet node has not validated the constructed transaction")
    write_json(STATE, {
        "network": "regtest", "transaction_kind": "sapling-shielded",
        "hex": raw, "txid": txid, "structure": structure,
        "construction": "real isolated zcashd wallet; locally accepted in wallet mempool",
        "verifier_tip": require_regtest()["bestblockhash"],
        "setup_transactions": {"transparent_funding": funding_txid, "sapling_funding": shielding_txid},
        "payload_sha256": hashlib.sha256(bytes.fromhex(raw)).hexdigest(),
    })
    print(f"Real shielded transaction constructed and accepted on isolated wallet node: {txid}")
    print("NOT submitted to the verification backend. Next: prove")
    print(json.dumps(structure, indent=2))
    print(f"State: {STATE}")


def observe_matching_mempool(stub, data):
    # lightwalletd can close the first stream when initializing its cached tip.
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        stream = stub.GetMempoolStream(pb.Empty(), timeout=max(0.1, deadline - time.monotonic()))
        try:
            for tx in stream:
                if tx.data == data:
                    return tx.height
        finally:
            stream.cancel()
        time.sleep(0.1)
    raise RuntimeError("Matching transaction bytes were not observed before the deadline")


def prove():
    require_regtest()
    lightd_info()
    transaction = json.loads(STATE.read_text())
    if transaction["network"] != "regtest":
        raise RuntimeError("Prepared transaction is not labeled regtest")
    txid = transaction["txid"]
    if txid in node("getrawmempool"):
        raise RuntimeError("Transaction is already in the mempool. Prepare a fresh transaction.")
    decoded = node("decoderawtransaction", transaction["hex"])
    if decoded["txid"] != txid:
        raise RuntimeError("Prepared txid disagrees with actual node decoder")
    kind = transaction["transaction_kind"]
    if kind == "transparent":
        source = transaction["input"]
        if node("gettxout", source["txid"], source["vout"]) is None:
            raise RuntimeError("Prepared input was already spent. Prepare a fresh transaction.")
        structure = {"transparent_inputs": len(decoded["vin"]), "transparent_outputs": len(decoded["vout"])}
    elif kind == "sapling-shielded":
        structure = shielded_structure(decoded)
        if require_regtest()["bestblockhash"] != transaction["verifier_tip"]:
            raise RuntimeError("Verifier tip changed after shielded preparation; prepare again")
    else:
        raise RuntimeError("Unknown transaction kind; refusing unsupported proof")
    data = bytes.fromhex(transaction["hex"])
    directory = ROOT / "out/regtest" / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
    events = directory / "events.jsonl"
    recorder = Recorder(events, "upstream")
    server = None
    try:
        with grpc.insecure_channel("127.0.0.1:9067") as upstream:
            server, port = start_server(recorder, upstream=rpc.CompactTxStreamerStub(upstream))
            with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
                grpc.channel_ready_future(channel).result(timeout=5)
                stub = rpc.CompactTxStreamerStub(channel)
                response = stub.SendTransaction(pb.RawTransaction(data=data), timeout=15)
                if response.errorCode != 0:
                    raise RuntimeError(f"Backend rejected the real transaction: {response.errorCode} {response.errorMessage}")
                height = observe_matching_mempool(stub, data)
                if height != 0:
                    raise RuntimeError("Returned transaction is not reported as mempool data")
            # Independent node RPC confirmation, without broadcasting through RPC.
            pool = node("getrawmempool")
            actual_hex = node("getrawtransaction", txid)
            if txid not in pool or bytes.fromhex(actual_hex) != data:
                raise RuntimeError("Independent node confirmation does not match captured transaction")
            write_json(directory / "backend-proof.json", {
                "network": "regtest", "transaction_kind": kind, "decoded_structure": structure,
                "txid": txid, "node_mempool_contains_txid": txid in pool,
                "node_raw_transaction_matches": bytes.fromhex(actual_hex) == data,
                "payload_sha256": hashlib.sha256(data).hexdigest(),
                "send_response_code": response.errorCode,
                "send_response_message": response.errorMessage,
                "node_subversion": node("getnetworkinfo")["subversion"],
                "lightwalletd_revision": lightd_info().gitCommit,
            })
    finally:
        if server is not None:
            server.stop(0).wait()
        recorder.close()
        print(f"Captured evidence: {events}", flush=True)
    report = directory / "report.json"
    run = subprocess.run([sys.executable, "-m", "shadecheck.cli", "test",
                          "--events", str(events), "--policy", "strict",
                          "--output", str(report)], cwd=ROOT)
    result = json.loads(report.read_text())
    if run.returncode != 1 or not any(f["severity"] == "HIGH" for f in result["findings"]):
        raise RuntimeError("Real evidence did not satisfy HIGH plus strict exit 1")
    # Also validates recorder integrity before accepting this integration proof.
    load_events(events)
    command([sys.executable, "-m", "shadecheck.cli", "report", "--input", str(report),
             "--format", "html", "--output", str(directory / "report.html")])
    print(f"SC-002 REAL REGTEST PROOF VERIFIED: HIGH; strict CLI exit 1. Kind: {kind}. Reports: {directory}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "check", "prepare", "prepare-shielded", "prove", "stop"])
    args = parser.parse_args()
    try:
        if args.action == "stop":
            print(compose("stop"))
        elif args.action == "prepare-shielded":
            prepare_shielded()
        else:
            globals()[args.action]()
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, grpc.RpcError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"Regtest setup error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
