"""Synthetic unit boundaries, never exported as real wallet-run evidence."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

import grpc

from shadecheck.core import Recorder, evaluate, load_events
from shadecheck.generated import service_pb2 as pb
from shadecheck.generated import service_pb2_grpc as rpc
from shadecheck.harness import start_server


class SyntheticBackend(rpc.CompactTxStreamerServicer):
    def GetLightdInfo(self, request, context):
        return pb.LightdInfo(chainName="regtest", blockHeight=123)

    def GetTreeState(self, request, context):
        context.abort(grpc.StatusCode.NOT_FOUND, "synthetic missing tree")

    def GetSubtreeRoots(self, request, context):
        yield pb.SubtreeRoot(rootHash=b"synthetic-root")

    def GetTaddressBalanceStream(self, request_iterator, context):
        return pb.Balance(valueZat=sum(len(x.address) for x in request_iterator))


class CompatibilityBoundaries(unittest.TestCase):
    def test_wire_preservation_errors_streams_and_no_invented_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            backend = grpc.server(ThreadPoolExecutor(max_workers=2))
            rpc.add_CompactTxStreamerServicer_to_server(SyntheticBackend(), backend)
            port = backend.add_insecure_port("127.0.0.1:0")
            backend.start()
            self.addCleanup(lambda: backend.stop(0).wait())
            upstream = grpc.insecure_channel(f"127.0.0.1:{port}")
            self.addCleanup(upstream.close)
            recorder = Recorder(Path(temp) / "events.jsonl", "protocol-fixture")
            observer, observed_port = start_server(recorder, upstream=rpc.CompactTxStreamerStub(upstream))
            try:
                with grpc.insecure_channel(f"127.0.0.1:{observed_port}") as channel:
                    client = rpc.CompactTxStreamerStub(channel)
                    info = client.GetLightdInfo(pb.Empty(), timeout=5)
                    self.assertEqual(info, pb.LightdInfo(chainName="regtest", blockHeight=123))
                    roots = list(client.GetSubtreeRoots(pb.GetSubtreeRootsArg(), timeout=5))
                    self.assertEqual(roots, [pb.SubtreeRoot(rootHash=b"synthetic-root")])
                    balance = client.GetTaddressBalanceStream(iter([pb.Address(address="private-address")]), timeout=5)
                    self.assertEqual(balance.valueZat, 15)
                    with self.assertRaises(grpc.RpcError) as failure:
                        client.GetTreeState(pb.BlockID(height=999), timeout=5)
                    self.assertEqual(failure.exception.code(), grpc.StatusCode.NOT_FOUND)
                    self.assertEqual(failure.exception.details(), "synthetic missing tree")
            finally:
                observer.stop(0).wait()
                recorder.close()
            events = load_events(recorder.path)
            text = recorder.path.read_text()
            self.assertNotIn("private-address", text)
            self.assertNotIn("synthetic-root", text)
            self.assertTrue(all(e["metadata"].get("coverage_role") == "compatibility-only"
                                for e in events if e["phase"] != "error"))
            self.assertEqual(evaluate(events)["status"], "WARN")
            self.assertEqual(evaluate(events)["findings"], [])
            self.assertTrue(any(e["metadata"].get("grpc_code") == "NOT_FOUND" for e in events))

    def test_no_backend_stays_unimplemented(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder = Recorder(Path(temp) / "events.jsonl", "protocol-fixture")
            server, port = start_server(recorder)
            try:
                with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
                    with self.assertRaises(grpc.RpcError) as failure:
                        rpc.CompactTxStreamerStub(channel).GetLightdInfo(pb.Empty(), timeout=5)
                    self.assertEqual(failure.exception.code(), grpc.StatusCode.UNIMPLEMENTED)
            finally:
                server.stop(0).wait()
                recorder.close()


if __name__ == "__main__":
    unittest.main()
