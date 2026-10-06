import argparse
import html
import json
import sys
from pathlib import Path

import grpc
from .core import Recorder, canonical, evaluate, load_events
from .generated import service_pb2_grpc as rpc
from .harness import probe, start_server


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shadecheck")
    commands = parser.add_subparsers(dest="command", required=True)
    test = commands.add_parser("test", help="Evaluate captured evidence or execute a local protocol fixture probe")
    source = test.add_mutually_exclusive_group(required=True)
    source.add_argument("--events")
    source.add_argument("--fixture", help="Hex transaction file; replayed only against a rejecting local endpoint")
    test.add_argument("--policy", choices=["strict", "advisory"], default="strict")
    test.add_argument("--output", default="out/report.json")
    test.add_argument("--record", default="out/events.jsonl")
    observe = commands.add_parser("observe", help="Forward two supported RPCs to your controlled lightwalletd")
    observe.add_argument("--upstream", required=True)
    observe.add_argument("--plaintext-upstream", action="store_true")
    observe.add_argument("--output", default="out/events.jsonl")
    observe.add_argument("--port", type=int, default=9068)
    report = commands.add_parser("report")
    report.add_argument("--input", default="out/report.json")
    report.add_argument("--format", choices=["json", "html"], default="json")
    report.add_argument("--output")
    explain = commands.add_parser("explain")
    explain.add_argument("rule", choices=["SC-002"])
    args = parser.parse_args(argv)
    try:
        if args.command == "explain":
            print("SC-002: MEDIUM for non-empty submission on an observable connection. HIGH requires upstream errorCode=0 plus identical transaction bytes returned by GetMempoolStream within 30 seconds. Strict policy fails any finding. Fixture replay never earns HIGH. No txid is inferred.")
            return 0
        if args.command == "observe":
            if not 1 <= args.port <= 65535:
                raise ValueError("Port must be between 1 and 65535")
            channel = (grpc.insecure_channel(args.upstream) if args.plaintext_upstream
                       else grpc.secure_channel(args.upstream, grpc.ssl_channel_credentials()))
            recorder = Recorder(args.output, "upstream")
            server, _ = start_server(recorder, f"127.0.0.1:{args.port}", rpc.CompactTxStreamerStub(channel))
            print(f"Observer listening at 127.0.0.1:{args.port}; only SendTransaction and GetMempoolStream supported", flush=True)
            try:
                server.wait_for_termination()
            except KeyboardInterrupt:
                pass
            finally:
                server.stop(0).wait()
                channel.close()
                recorder.close()
            return 0
        if args.command == "test":
            if args.fixture:
                transaction = bytes.fromhex(Path(args.fixture).read_text())
                recorder = Recorder(args.record, "protocol-fixture")
                try:
                    probe(recorder, transaction)
                finally:
                    recorder.close()
                events = load_events(args.record)
            else:
                events = load_events(args.events)
            result = evaluate(events, args.policy)
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
