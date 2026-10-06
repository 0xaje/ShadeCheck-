import hashlib
import time
from concurrent.futures import ThreadPoolExecutor

import grpc
from .generated import service_pb2 as pb
from .generated import service_pb2_grpc as rpc


def payload_metadata(data):
    return {"payload_size": len(data), "payload_sha256": hashlib.sha256(data).hexdigest()}


class Observer(rpc.CompactTxStreamerServicer):
    def __init__(self, recorder, upstream=None):
        self.recorder = recorder
        self.upstream = upstream

    def SendTransaction(self, request, context):
        seq = self.recorder.record("SendTransaction", "request", context.peer(),
                                   **payload_metadata(request.data))
        if self.upstream is None:
            # Controlled protocol endpoint does not pretend to accept a transaction.
            response = pb.SendResponse(errorCode=1, errorMessage="ShadeCheck fixture endpoint: no consensus backend; not broadcast")
        else:
            try:
                response = self.upstream.SendTransaction(request, timeout=15)
            except grpc.RpcError as error:
                self.recorder.record("SendTransaction", "error", context.peer(),
                                     request_sequence=seq, grpc_code=error.code().name)
                context.abort(error.code(), error.details())
        self.recorder.record("SendTransaction", "response", context.peer(),
                             request_sequence=seq, error_code=response.errorCode,
                             response_message=response.errorMessage)
        return response

    def GetMempoolStream(self, request, context):
        self.recorder.record("GetMempoolStream", "request", context.peer())
        if self.upstream is None:
            return
        call = self.upstream.GetMempoolStream(request, timeout=30)
        context.add_callback(call.cancel)
        try:
            for response in call:
                self.recorder.record("GetMempoolStream", "response", context.peer(),
                                     height=response.height, **payload_metadata(response.data))
                yield response
        except grpc.RpcError as error:
            self.recorder.record("GetMempoolStream", "error", context.peer(),
                                 grpc_code=error.code().name)
            context.abort(error.code(), error.details())


def start_server(recorder, bind="127.0.0.1:0", upstream=None):
    server = grpc.server(ThreadPoolExecutor(max_workers=4))
    rpc.add_CompactTxStreamerServicer_to_server(Observer(recorder, upstream), server)
    port = server.add_insecure_port(bind)
    if not port:
        raise ValueError("Could not bind observer")
    server.start()
    return server, port


def probe(recorder, transaction):
    if not transaction:
        raise ValueError("Transaction fixture cannot be empty")
    server, port = start_server(recorder)
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            grpc.channel_ready_future(channel).result(timeout=5)
            return rpc.CompactTxStreamerStub(channel).SendTransaction(
                pb.RawTransaction(data=transaction), timeout=5)
    finally:
        server.stop(0).wait()


def live_sc002_probe(endpoint, transaction, timeout_seconds=30):
    """Exercise SC-002 against a running ShadeCheck observer backed by real lightwalletd.

    The caller must provide a genuinely signed raw transaction appropriate for the
    controlled backend. This helper never manufactures transaction bytes and never
    upgrades a rejected transaction into a successful result.
    """
    if not transaction:
        raise ValueError("Live transaction cannot be empty")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    fingerprint = hashlib.sha256(transaction).hexdigest()
    with grpc.insecure_channel(endpoint) as channel:
        grpc.channel_ready_future(channel).result(timeout=5)
        stub = rpc.CompactTxStreamerStub(channel)
        response = stub.SendTransaction(pb.RawTransaction(data=transaction), timeout=15)
        accepted = response.errorCode == 0
        if not accepted:
            return {
                "accepted": False,
                "mempool_match": False,
                "payload_sha256": fingerprint,
                "backend_error_code": response.errorCode,
                "backend_error_message": response.errorMessage,
            }

        matched = False
        try:
            stream = stub.GetMempoolStream(pb.Empty(), timeout=timeout_seconds)
            for item in stream:
                if item.data == transaction:
                    matched = True
                    break
        except grpc.RpcError as error:
            if error.code() != grpc.StatusCode.DEADLINE_EXCEEDED:
                raise

        return {
            "accepted": True,
            "mempool_match": matched,
            "payload_sha256": fingerprint,
            "backend_error_code": response.errorCode,
            "backend_error_message": response.errorMessage,
            "timeout_seconds": timeout_seconds,
        }
