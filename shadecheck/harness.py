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

    def GetLatestBlock(self, request, context):
        seq = self.recorder.record("GetLatestBlock", "request", context.peer())
        if self.upstream is None:
            context.abort(grpc.StatusCode.UNIMPLEMENTED, "Latest block requires an actual backend")
        try:
            response = self.upstream.GetLatestBlock(request, timeout=15)
        except grpc.RpcError as error:
            self.recorder.record("GetLatestBlock", "error", context.peer(),
                                 request_sequence=seq, grpc_code=error.code().name)
            context.abort(error.code(), error.details())
        self.recorder.record("GetLatestBlock", "response", context.peer(),
                             request_sequence=seq, height=response.height,
                             block_hash=response.hash.hex())
        return response

    def GetBlockRange(self, request, context):
        seq = self.recorder.record("GetBlockRange", "request", context.peer(),
                                   start_height=request.start.height, end_height=request.end.height)
        if self.upstream is None:
            context.abort(grpc.StatusCode.UNIMPLEMENTED, "Block ranges require an actual backend")
        call = self.upstream.GetBlockRange(request, timeout=30)
        context.add_callback(call.cancel)
        try:
            for block in call:
                self.recorder.record("GetBlockRange", "response", context.peer(),
                                     request_sequence=seq, height=block.height,
                                     block_hash=block.hash.hex(),
                                     transaction_ids=[tx.txid.hex() for tx in block.vtx],
                                     serialized_sha256=hashlib.sha256(block.SerializeToString()).hexdigest())
                yield block
        except grpc.RpcError as error:
            self.recorder.record("GetBlockRange", "error", context.peer(),
                                 request_sequence=seq, grpc_code=error.code().name)
            context.abort(error.code(), error.details())

    def GetTransaction(self, request, context):
        seq = self.recorder.record("GetTransaction", "request", context.peer(),
                                   transaction_id=request.hash.hex())
        if self.upstream is None:
            context.abort(grpc.StatusCode.UNIMPLEMENTED, "Transaction retrieval requires an actual backend")
        try:
            response = self.upstream.GetTransaction(request, timeout=15)
        except grpc.RpcError as error:
            self.recorder.record("GetTransaction", "error", context.peer(),
                                 request_sequence=seq, grpc_code=error.code().name)
            context.abort(error.code(), error.details())
        self.recorder.record("GetTransaction", "response", context.peer(),
                             request_sequence=seq, height=response.height,
                             **payload_metadata(response.data))
        return response

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


def _compatibility_method(method):
    """Forward additional schema-defined RPCs without pretending rules cover them.

    Only message fingerprints/sizes are retained: tree material, addresses, and
    wallet keys are not copied into the compatibility event metadata.
    """
    def fingerprint(message):
        data = message.SerializeToString(deterministic=True)
        return {"message_sha256": hashlib.sha256(data).hexdigest(),
                "message_size": len(data), "coverage_role": "compatibility-only"}

    def invoke(self, request, context):
        if self.upstream is None:
            context.abort(grpc.StatusCode.UNIMPLEMENTED, "Compatibility RPC requires an actual backend")
        seq = self.recorder.record(method.name, "request", context.peer(),
                                   **({"coverage_role": "compatibility-only"} if method.client_streaming
                                      else fingerprint(request)))
        if method.client_streaming:
            def requests():
                for item in request:
                    self.recorder.record(method.name, "request-item", context.peer(),
                                         request_sequence=seq, **fingerprint(item))
                    yield item
            outgoing = requests()
        else:
            outgoing = request
        remaining = context.time_remaining()
        timeout = min(120, remaining) if remaining is not None else 120
        call = getattr(self.upstream, method.name)
        try:
            if method.server_streaming:
                response = call(outgoing, timeout=timeout)
                context.add_callback(response.cancel)
                for item in response:
                    self.recorder.record(method.name, "response", context.peer(),
                                         request_sequence=seq, **fingerprint(item))
                    yield item
            else:
                response = call.future(outgoing, timeout=timeout)
                context.add_callback(response.cancel)
                item = response.result()
                self.recorder.record(method.name, "response", context.peer(),
                                     request_sequence=seq, **fingerprint(item))
                yield item
        except grpc.RpcError as error:
            self.recorder.record(method.name, "error", context.peer(),
                                 request_sequence=seq, grpc_code=error.code().name)
            context.abort(error.code(), error.details())
        except grpc.FutureCancelledError:
            context.abort(grpc.StatusCode.CANCELLED, "Downstream call cancelled")

    if method.server_streaming:
        return invoke

    def unary(self, request, context):
        return next(invoke(self, request, context))
    return unary


# Keep the five evidence-rich rule RPCs above; forward the remaining methods in
# the vendored protocol schema. Unknown methods stay UNIMPLEMENTED in gRPC.
for _method in pb.DESCRIPTOR.services_by_name["CompactTxStreamer"].methods:
    if _method.name not in Observer.__dict__:
        setattr(Observer, _method.name, _compatibility_method(_method))


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
