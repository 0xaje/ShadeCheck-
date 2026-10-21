# Independent Zingo CLI integration

This integration runs an unmodified, independently developed Zcash wallet client
against a real local node and lightwalletd, first directly and then through
ShadeCheck. It is a compatibility and evidence experiment, not Zingo endorsement,
third-party adoption, a production audit, or a claim about the latest release.

## Exact target and current gate

- Upstream: https://github.com/zingolabs/zingolib
- Release: `zingolib_v3.0.1` (historical compatibility target).
- Commit: `31da83657d88fbb3b57bf45996023850e8aaf9da`.
- Build: Rust 1.90.0, `cargo build --locked --release -p zingo-cli --features regtest`.
- Source is not patched to make the test pass. The runner refuses a different HEAD
  or tracked source modifications. The report records the executable SHA-256.
- The release has a direct local regtest mode. This does not test the latest
  release's mixnet transport or production defaults.

The integration is verified only when the dedicated workflow completes the real
wallet synchronization step and emits `integration_status: VERIFIED`. A compiled
binary or passing synthetic unit tests alone do not satisfy that gate.

## Why a separate backend

The CLI's regtest configuration activates network upgrades through NU6.1 at
height 1. The existing MVP backend activates Sapling for its frozen scenarios.
Changing that chain in place would invalidate existing data. The integration
therefore uses `integration/zingo/compose.yml`, Docker project
`shadecheck-zingo-regtest`, separate volumes, and loopback port 19067. It never
alters the original MVP volumes or publishes node RPC/P2P ports.

## Reproduce on Linux / WSL

Requirements: Docker with Linux containers; Python 3.11+ with ShadeCheck installed;
Rust 1.90.0; the upstream prerequisites (build-essential, protobuf-compiler,
libssl-dev and pkg-config); network access for upstream source, Cargo dependencies,
proving-parameter downloads, and Docker build inputs.

```bash
git clone https://github.com/zingolabs/zingolib.git ../shadecheck-zingo-client
git -C ../shadecheck-zingo-client checkout --detach 31da83657d88fbb3b57bf45996023850e8aaf9da
cd ../shadecheck-zingo-client
cargo +1.90.0 build --locked --release -p zingo-cli --features regtest
cd ../ShadeCheck-
./.venv/bin/python scripts/zingo_integration.py --source ../shadecheck-zingo-client
```

Use the actual ShadeCheck checkout directory if its name differs. The script
starts the separate backend, mines actual regtest blocks, and creates two fresh
wallets. It requires nonzero block scanning and 100% block scan completion in
both runs. On the observed run it also requires actual compact block delivery
and checks every distinct delivered block hash against the canonical node.

To stop only this integration's services (preserving data):

```bash
docker compose -f integration/zingo/compose.yml down
```

## Evidence and interpretation

Each attempt has a new `out/zingo/TIMESTAMP-ID` directory. A successful run saves:

- `direct/client-sync.json`: parsed upstream sync status and actual process exit.
- `observed/client-sync.json`: parsed upstream sync status through the observer.
- `observed/events.jsonl`: hash-chained actual RPC evidence.
- `observed/report.json` and `observed/report.html`: deterministic rule results.
- `policy.json`: explicit policy used for evaluation.
- `integration.json`: source/binary provenance, backend revision, canonical block
  checks, method counts, missing coverage, and limitations.

Wallets, spending keys and private failure diagnostics remain under
`.shadecheck/zingo-wallets`, outside the downloadable evidence directory and CI
artifact upload. Do not upload that private wallet directory. This first test
uses unfunded wallets; no user funds or user wallet is required.

The integration exits zero when the compatibility/evidence checks succeeded,
independently of the report's privacy status. Its manifest separately records the
actual strict policy exit. An integration failure exits 2 and writes
`integration-error.json`; it cannot create a VERIFIED manifest.

SC-001 checks an explicitly selected 20-block aligned range requirement. That is
an experiment policy, not a universal wallet privacy standard. A chain-tip range
can violate it for legitimate reasons; a finding is not by itself a security
vulnerability. SC-002/SC-003/SC-004 remain uncovered unless their required
behaviors were actually observed. SC-005 is not evaluated here. No missing
coverage is converted into PASS.

Additional schema-defined RPCs are forwarded to preserve wallet operation.
Their recorded fingerprints/sizes are marked `compatibility-only`; forwarding
server info, tree state, subtree roots, transparent lookups, or other RPCs does
not mean ShadeCheck has privacy rules for them. Raw compatibility messages and
transparent addresses are not copied into these event records. Hashes can still
be sensitive/correlatable metadata, so treat evidence as developer test data.

Saved artifacts can also be checked without Docker or the wallet binary:

```bash
./.venv/bin/python scripts/zingo_integration.py --verify out/zingo/TIMESTAMP-ID
```

This recomputes event integrity and rule results and checks recorded file hashes.
It does not rerun consensus checks, authenticate the author, or independently
prove that the historical client process ran; source CI provenance supplies the
execution context.

## Remaining work after this gate

A funded receive/send workflow, independent-client broadcast evidence, repeat
sync/reorg scenarios, newer upstream versions, transport modes, and external
maintainer validation require additional tests. This experiment does not replace
the already verified MVP acceptance suite or prove anonymity.
