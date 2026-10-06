# Fixture and protocol provenance

Upstream: https://github.com/zcash/lightwalletd

Pinned revision: d16d48124e9ad4157ebc2324b5090c6ba201470c

- proto/service.proto: upstream walletrpc/service.proto.
- proto/compact_formats.proto: upstream walletrpc/compact_formats.proto.
- transaction-v5.hex: first transaction row (row index 2, column 0) of upstream testdata/tx_v5.json. That file attributes its source to zcash-test-vectors transaction_v5.py.

This is a serialization test vector. It is not represented as a funded, signed, spendable, mined, or network-accepted transaction. The controlled replay endpoint deliberately rejects it.

Generated Python stubs were produced with grpcio-tools 1.84.0. Imports were changed to relative package imports. Upstream protocol source headers retain their MIT license notices; see THIRD_PARTY_LICENSE.
