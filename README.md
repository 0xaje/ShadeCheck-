# ShadeCheck

Privacy CI for Zcash applications.

ShadeCheck evaluates defined observable Zcash application behaviors against documented privacy tests. Passing does not establish anonymity.

## Current implementation

This is the **SC-002 foundation**, not the completed MVP. It captures actual gRPC requests using the official lightwalletd protobuf schema, writes inspectable JSONL evidence, evaluates broadcast connection linkability, and generates JSON/HTML reports with policy exit codes.

The local protocol client replays an upstream transaction test vector to a controlled endpoint that explicitly rejects it. It never claims a fixture was network accepted, mined, or consensus valid. No spending keys are requested or stored.

**SC-002 transport milestone verified:** the real regtest integration run accepted a genuinely signed transparent transaction, captured its exact bytes through lightwalletd's mempool stream, independently confirmed those bytes at the node, and verified HIGH plus strict CLI exit 1. Real Sapling-to-Sapling integration is also verified: two successive shielded transactions passed backend validation with zero transparent inputs or outputs and produced the same evidence-backed HIGH finding. Mitigation comparison remains.

## Run the real local backend

See the [Windows PowerShell setup guide](docs/regtest-setup.md). After installing Docker Desktop and ShadeCheck:

```sh
python scripts/regtest.py up
python scripts/regtest.py prepare
python scripts/regtest.py prove
```

The prove command starts the observer automatically and saves evidence and JSON/HTML reports in a unique out/regtest directory. The [real-backend CI run](https://github.com/0xaje/ShadeCheck-/actions/runs/37396184795) passed on October 6, 2026. Its artifacts contain the actual evidence. The [shielded setup guide](docs/shielded-regtest.md) adds a real local wallet and repeatable Sapling-to-Sapling proof. The [shielded and repeat-run CI proof](https://github.com/0xaje/ShadeCheck-/actions/runs/37401106271) passed, including inspectable JSON/HTML reports. The protocol fixture workflow remains a separate internal conformance test.

## Setup

Python 3.11 or newer:

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install .
python -m unittest discover -s tests -v
```

## Local protocol slice — internal test only

```sh
shadecheck test --fixture fixtures/transaction-v5.hex --policy strict
shadecheck report --format json
shadecheck report --format html --output out/report.html
shadecheck explain SC-002
```

Expected: **MEDIUM SC-002**, **FAIL**, exit **1**. Submission bytes were observed on an identifiable connection; the endpoint explicitly rejects the submission. Each finding embeds the actual recorded request and response.

This path is an internal protocol/conformance test. It is not the judge-visible proof of ShadeCheck's real-world capability.

Evidence creation is exclusive. Use a fresh `--record` path for each run; existing evidence is never silently overwritten.

## Real SC-002 milestone

The live path must use a real controlled backend. Zebra regtest or a controlled Zcash Testnet node backed by official `zcash/lightwalletd` is appropriate. The raw transaction must be genuinely signed by a wallet/client for that environment; ShadeCheck does not generate fake transaction bytes.

Terminal 1 — run the observer in front of the controlled lightwalletd instance:

```sh
shadecheck observe \
  --upstream 127.0.0.1:9067 \
  --plaintext-upstream \
  --output out/live-events.jsonl
```

The observer listens on `127.0.0.1:9068`.

Terminal 2 — send a genuinely signed raw transaction through the observer and require exact mempool re-observation:

```sh
shadecheck live-sc002 \
  --observer 127.0.0.1:9068 \
  --transaction /path/to/real-signed-transaction.hex \
  --timeout 30
```

A successful live milestone requires **both**:

1. the real backend returns `errorCode=0` for `SendTransaction`; and
2. `GetMempoolStream` returns the exact same raw transaction bytes within the timeout.

Stop the observer with Ctrl-C after the live probe, then evaluate the evidence:

```sh
shadecheck test \
  --events out/live-events.jsonl \
  --policy strict \
  --output out/live-report.json
```

Only this upstream-backed evidence can produce **HIGH**. A fixture can never produce HIGH.

## Controlled lightwalletd integration

Only `SendTransaction` and `GetMempoolStream` are forwarded in the current observer. Other RPCs return UNIMPLEMENTED. This is not yet a full wallet sync proxy.

The observer itself changes routing and timing. SC-002 therefore makes a narrow claim: the service receiving the broadcast can associate submitted raw transaction bytes with the transport connection it observed. A connection is not a person or stable wallet identity.

## SC-002 deterministic severity

| Observation | Result |
| --- | --- |
| Non-empty SendTransaction payload associated with transport peer | MEDIUM |
| Above plus real upstream `errorCode=0` and identical bytes returned by `GetMempoolStream` within 30 seconds | HIGH |
| No non-empty broadcast request captured | WARN: missing coverage |
| Invalid/empty evidence or execution error | Exit 2 |

Strict policy rejects any SC-002 finding (exit 1); missing coverage also returns non-zero (exit 2). Advisory policy returns WARN with exit 0. A HIGH finding is a statement about this RPC observer's capability, not proof of user deanonymization. Server-reported acceptance plus byte-for-byte mempool observation is evidence of backend acceptance/propagation in the controlled environment; it is not proof of mining or finality.

## Evidence

Each event includes sequence, wall clock and monotonic elapsed time, hashed transport peer, RPC/phase, payload size/fingerprint, mode, and hash chain. A SHA-256 payload fingerprint is **not** a Zcash transaction ID. Full raw transaction bytes are forwarded without being stored in evidence. Hash chaining detects accidental editing; it is not a signature or protection against an author rewriting the complete chain.

Reports may contain privacy-sensitive connection and transaction fingerprints. Treat them as controlled test artifacts.

## No-fake implementation rule

ShadeCheck's product claims must come from real protocol behavior:

- no fabricated transactions;
- no dummy backend success;
- no mocked privacy findings in the judge-visible workflow;
- no hard-coded HIGH severity;
- no claim of network acceptance unless the backend actually accepted the transaction;
- no claim of mempool propagation unless identical raw bytes were actually observed.

Fixtures remain only for deterministic unit/protocol tests and are labeled as such.

## Remaining MVP

SC-001, SC-003, SC-004, SC-005, baselines, mitigation comparison, and Windows verification of the shielded path remain. The developer has verified the transparent regtest path on Windows. The separate regtest workflow now validates a real node/lightwalletd broadcast; it does not establish production readiness or anonymity.

See [threat model](docs/threat-model.md) and [fixture provenance](fixtures/PROVENANCE.md).
