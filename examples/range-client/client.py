"""Small real gRPC consumer example; not a wallet or synthetic RPC server."""
import argparse
import json
import sys

import grpc
from shadecheck.generated import service_pb2 as pb, service_pb2_grpc as rpc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', required=True, help='Controlled ShadeCheck observer host:port')
    parser.add_argument('--start', required=True, type=int)
    parser.add_argument('--end', required=True, type=int)
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start or args.end - args.start >= 1000:
        parser.error('Choose an ascending non-genesis range of at most 1000 blocks')
    with grpc.insecure_channel(args.server) as channel:
        client = rpc.CompactTxStreamerStub(channel)
        blocks = list(client.GetBlockRange(pb.BlockRange(
            start=pb.BlockID(height=args.start), end=pb.BlockID(height=args.end)), timeout=30))
    if [b.height for b in blocks] != list(range(args.start, args.end + 1)):
        raise RuntimeError('Backend did not deliver the complete requested range')
    print(json.dumps({'requested_start': args.start, 'requested_end': args.end,
                      'blocks': [{'height': b.height, 'block_hash': b.hash[::-1].hex()} for b in blocks]},
                     sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, grpc.RpcError) as error:
        print(f'Range client error: {error}', file=sys.stderr)
        raise SystemExit(2)
