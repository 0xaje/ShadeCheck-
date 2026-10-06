import argparse
import html
import json
import sys
from pathlib import Path

import grpc
from .core import Recorder, canonical, evaluate, load_events
from .generated import service_pb2_grpc as rpc
from .harness import live_sc002_probe, probe, start_server


def _read_hex_transaction(path):
    text = Path(path).read_text().strip()
    if not text:
        raise ValueError("Transaction file is empty")
    try:
        return bytes.fromhex(text)
    except ValueError as error:
        raise ValueError("Transaction file must contain raw transaction bytes encoded as hex") from error


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shadecheck")
    commands = parser.add_subparsers(dest="command", required=True)
    test = commands.add_parser("test", help="Evaluate captured evidence or execute a local protocol fixture probe")
    source = test.add_mutually_exclusive_group(required=True)
    source.add_argument("--events")
    source.add_argument("--fixture", help="Hex transaction file; replayed only against a rejecting local endpoint")
    test.add_argument("--policy", choices=["strict", "advisory"], default="strict")
    test.add_argument("--rules", nargs="+", choices=["SC-001", "SC-002", "SC-003", "SC-004"], default=["SC-002"])
    test.add_argument("--config", help="JSON policy configuration; required when selecting SC-001 or SC-004")
    test.add_argument("--output", default="out/report.json")
    test.add_argument("--record", default="out/events.jsonl")

    observe = commands.add_parser("observe", help="Forward supported broadcast, mempool, and latest-block RPCs to your controlled lightwalletd")
    observe.add_argument("--upstream", required=True)
    observe.add_argument("--plaintext-upstream", action="store_true")
    observe.add_argument("--output", default="out/events.jsonl")
    observe.add_argument("--port", type=int, default=9068)

    live = commands.add_parser(
        "live-sc002",
        help="Send a real signed raw transaction through a running ShadeCheck observer and require exact mempool re-observation",
    )
    live.add_argument("--observer", default="127.0.0.1:9068")
    live.add_argument("--transaction", required=True, help="Hex file containing a genuinely signed raw Zcash transaction")
    live.add_argument("--timeout", type=int, default=30)

    report = commands.add_parser("report")
    report.add_argument("--input", default="out/report.json")
    report.add_argument("--format", choices=["json", "html"], default="json")
    report.add_argument("--output")
    explain = commands.add_parser("explain")
    explain.add_argument("rule", choices=["SC-001", "SC-002", "SC-003", "SC-004"])
    args = parser.parse_args(argv)
    try:
        if args.command == "explain":
            if args.rule == "SC-004":
                print("SC-004: explicit shielded-payment policy required. MEDIUM for instrumented permissive transparent selection; HIGH requires actual decoded transparent components linked by payload fingerprint to accepted upstream submission. Adapter records are not passive network observations. Specific FullPrivacy rejection or verified execution supplies outcome coverage.")
                return 0
            if args.rule == "SC-001":
                print("SC-001: MEDIUM for upstream block ranges that violate an explicit size/alignment policy. Complete actual range delivery is required for PASS coverage. No wallet history or identity is inferred.")
                return 0
            if args.rule == "SC-003":
                print("SC-003: MEDIUM when the same connection requests a non-empty proper subset of IDs from an upstream compact block containing at least two transactions within 30 seconds. Block delivery is observable; wallet processing or ownership is not. PASS is limited to this rule and recorded trace.")
                return 0
            print("SC-002: MEDIUM for non-empty submission on an observable connection. HIGH requires upstream errorCode=0 plus identical transaction bytes returned by GetMempoolStream within 30 seconds. Strict policy fails any finding. Fixture replay never earns HIGH. No txid is inferred.")
            return 0
        if args.command == "observe":
            if not 1 <= args.port <= 65535:
                raise ValueError("Port must be between 1 and 65535")
            channel = (grpc.insecure_channel(args.upstream) if args.plaintext_upstream
                       else grpc.secure_channel(args.upstream, grpc.ssl_channel_credentials()))
            recorder = Recorder(args.output, "upstream")
            server, _ = start_server(recorder, f"127.0.0.1:{args.port}", rpc.CompactTxStreamerStub(channel))
            print(f"Observer listening at 127.0.0.1:{args.port}; GetLatestBlock, GetBlockRange, GetTransaction, SendTransaction, and GetMempoolStream supported", flush=True)
            try:
                server.wait_for_termination()
            except KeyboardInterrupt:
                pass
            finally:
                server.stop(0).wait()
                channel.close()
                recorder.close()
            return 0
        if args.command == "live-sc002":
            transaction = _read_hex_transaction(args.transaction)
            result = live_sc002_probe(args.observer, transaction, args.timeout)
            print(canonical(result))
            if not result["accepted"]:
                print("ShadeCheck live milestone incomplete: backend rejected the transaction.", file=sys.stderr)
                return 1
            if not result["mempool_match"]:
                print("ShadeCheck live milestone incomplete: accepted transaction was not observed byte-for-byte in the mempool stream.", file=sys.stderr)
                return 1
            print("ShadeCheck live milestone evidence generated: backend accepted the transaction and exact bytes were observed in the mempool stream.", file=sys.stderr)
            return 0
        if args.command == "test":
            if args.fixture:
                transaction = _read_hex_transaction(args.fixture)
                recorder = Recorder(args.record, "protocol-fixture")
                try:
                    probe(recorder, transaction)
                finally:
                    recorder.close()
                events = load_events(args.record)
            else:
                events = load_events(args.events)
            sync_policy = None
            payment_policy = None
            if args.config:
                config = json.loads(Path(args.config).read_text())
                if not isinstance(config, dict) or config.get("schema_version") != 1:
                    raise ValueError("Policy configuration requires schema_version 1")
                sync_policy = config.get("sync")
                payment_policy = config.get("payment")
            result = evaluate(events, args.policy, rules=args.rules, sync_policy=sync_policy, payment_policy=payment_policy)
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(canonical(result) + "\n")
            print(f"{result['status']}: {len(result['findings'])} finding(s); report: {output}")
            return 1 if result["status"] == "FAIL" else (2 if result["status"] == "WARN" and args.policy == "strict" else 0)
        result = json.loads(Path(args.input).read_text())
        content = (json.dumps(result, indent=2, sort_keys=True) if args.format == "json" else
                   "<!doctype html><meta charset='utf-8'><title>ShadeCheck evidence report</title>"
                   "<h1>ShadeCheck: " + html.escape(result["status"]) + "</h1>"
                   "<p>Defined observable behavior tests; passing does not establish anonymity.</p>"
                   "<pre>" + html.escape(json.dumps(result, indent=2, sort_keys=True)) + "</pre>")
        if args.output:
            Path(args.output).write_text(content + "\n")
        else:
            print(content)
        return 0
    except (OSError, ValueError, KeyError, TypeError, grpc.RpcError) as error:
        print(f"ShadeCheck error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
