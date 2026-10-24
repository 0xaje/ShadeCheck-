# Recorded current-release funded wallet evidence

This archive is the original GitHub CI artifact from a real controlled regtest execution, not a fixture or a new run. No events were rewritten or relabelled. It contains evidence, parsed sync statuses, the recipient receipt, JSON/HTML reports and the integration manifest. No wallet files, seeds, spending/viewing keys or private client failure logs are included.

- [Source CI run 40099904709](https://github.com/0xaje/ShadeCheck-/actions/runs/40099904709), ShadeCheck revision `7ccf7c9e7270a9bde88c18ef8a4170acf80fa258`.
- Unmodified zingolib release `zingolib_v7.0.0`, commit `bfb0a2156819ea7f75a9b09b1724abfd06c8925e`; Zebra 7.0.0 and Zaino 0.10.1-no-tls with pinned image digests.
- Explicit upstream `nakednet-test-mode` build. This is local test transport, not validation of default production mixnet behavior. The source release tag is not a claimed CLI binary version; this upstream binary still reports `Zingo CLI 0.1.1`.
- Direct and observed initial scans both completed heights 1–210. A stale or incomplete scan fails the gate.
- 1,009 events; 213 distinct delivered compact block heights checked against the canonical node.
- Actual mined funds shielded by the wallet, then an actual shielded send. Both transmissions were accepted into Zebra's mempool, matched byte-for-byte through the observer and included in blocks.
- The payment has zero transparent inputs and outputs. Recipient scanned through height 216 and reported exactly 100,000 shielded zatoshis in the Ironwood pool, with zero transparent value.
- SC-002 produced two HIGH findings and actual strict CLI exit 1. Integration validation is VERIFIED; privacy remains FAIL for the observed direct broadcast behavior. A direct broadcaster's visibility is not itself a new wallet vulnerability.
- Only SC-002 is evaluated in this funded gate. Other families have separate scenarios; do not merge their coverage into this trace.

## Inspect without building Rust or starting Docker

Install ShadeCheck, then from the repository:

```bash
python -m zipfile -e examples/modern/recorded-regtest-20261024.zip out/modern-recorded
python scripts/modern_wallet.py --verify out/modern-recorded/20261024T135437-8bcfe43c
```

Open `out/modern-recorded/20261024T135437-8bcfe43c/report.html`, or inspect `report.json`, `events.jsonl`, `recipient-receipt.json` and `integration.json`.

Original archive: 128,851 bytes; SHA-256 `ed2f80fd89eb55fa975728e6e8740ffaf95173dab58f3a23236dd36a9f534f9f`.

Offline verification checks the inventory, scan targets, recipient amount and deterministic findings. It does not rerun a wallet, independently replay consensus, authenticate an author or prove anonymity. [Fresh execution and exact pins](../../docs/modern-wallet.md).
