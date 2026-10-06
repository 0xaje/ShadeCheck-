# ShadeCheck

Privacy CI for Zcash applications.

ShadeCheck evaluates defined observable Zcash application behaviors against documented privacy tests. Passing does not establish anonymity.

## Current implementation

This implements **all five initial rule families** within the documented observable-behavior boundaries. It captures actual gRPC requests using the official lightwalletd protobuf schema, writes inspectable JSONL evidence, evaluates sync-range policy, broadcast connection linkability, selective retrieval, and instrumented wallet payment privacy, and baseline regressions, and generates JSON/HTML reports with policy exit codes.

The local protocol client replays an upstream transaction test vector to a controlled endpoint that explicitly rejects it. It never claims a fixture was network accepted, mined, or consensus valid. No spending keys are requested or stored.

**SC-002 transport milestone verified:** the real regtest integration run accepted a genuinely signed transparent transaction, captured its exact bytes through lightwalletd's mempool stream, independently confirmed those bytes at the node, and verified HIGH plus strict CLI exit 1. Real Sapling-to-Sapling integration is also verified: two successive shielded transactions passed backend validation with zero transparent inputs or outputs and produced the same evidence-backed HIGH finding. The [real observer-role comparison](docs/broadcast-comparison.md) is verified: separated routing removes submission visibility from the read observer while the broadcast observer still reports HIGH. This is not a production mitigation or anonymity proof.

## Run the consolidated acceptance suite

See the [definition-of-done audit and fresh-machine guide](docs/acceptance.md). With Docker Desktop running:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe scripts/acceptance.py
```

This single command starts the real backend, runs transparent/shielded proofs and all five rule families, checks strict exit codes, and independently audits the saved evidence, baselines, and JSON/HTML results. [Fresh CI run 37409730042](https://github.com/0xaje/ShadeCheck-/actions/runs/37409730042) passed the consolidated workflow: 18 steps, 24 recomputed reports, and 112 hashed artifacts. The downloaded artifact passed independent offline revalidation, and changed evidence was rejected. It saves one isolated out/acceptance run with suite.json, suite.html, individual reports, logs, artifact hashes, and actual image identities. Acceptance PASS means the test checks behaved as required; expected privacy failures remain FAIL. Offline revalidation: `python scripts/acceptance.py --verify <suite-directory>`.

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

## Real SC-001 sync-range comparison

See the [SC-001 rule and Windows guide](docs/sc001.md). Run `python scripts/sync_pattern.py` with the backend running. The script evaluates actual block-range requests against an explicit 20-block aligned policy and independently checks each compact block against the canonical node. [Real CI run 37406302451](https://github.com/0xaje/ShadeCheck-/actions/runs/37406302451) verified narrow MEDIUM/FAIL with strict exit 1 and aligned PASS for the declared SC-001 policy with exit 0. Select SC-001 with `--rules SC-001 --config <policy.json>`; the comparison saves its exact policy beside the evidence. This policy does not establish anonymity or infer wallet history.

## Real SC-003 retrieval comparison

See the [SC-003 rule and Windows guide](docs/sc003.md). Run `python scripts/selective_fetch.py` with the backend running. It records actual compact-block delivery and transaction retrieval, independently checks returned bytes and inclusion against the node, and compares fetching one compact transaction with fetching every compact transaction in the same confirmed block.

[Real CI run 37403356091](https://github.com/0xaje/ShadeCheck-/actions/runs/37403356091) verified subset MEDIUM/FAIL with strict exit 1 and complete fetch PASS for SC-003 with exit 0. Full events, JSON/HTML reports, and node confirmation are inspectable in the uploaded artifact. Select SC-003 explicitly using `shadecheck test --events <path> --rules SC-003`; the existing default remains SC-002. Passing this narrow executed rule does not establish anonymity.

## Real SC-004 payment-policy comparison

See the [SC-004 rule and Windows guide](docs/sc004.md). Run `python scripts/transparent_fallback.py` with the backend running. It compares an actual Sapling-to-transparent payment permitted by AllowRevealedRecipients with FullPrivacy rejecting that recipient and then accepting a shielded payment. The tested flow explicitly requires shielding.

[Real CI run 37407689623](https://github.com/0xaje/ShadeCheck-/actions/runs/37407689623) verified permissive HIGH/FAIL with strict exit 1 and FullPrivacy PASS for SC-004 with exit 0. Saved event hash chains and recomputed reports were checked, including native privacy error -8, actual decoded transaction components, exact mempool bytes, and independent node acceptance. Select `--rules SC-004 --config <policy.json>`. Native-wallet adapter evidence is explicitly distinguished from observed RPC evidence. Automatic Unified Address fallback is not implemented; this tests the explicit transparent recipient path.

## SC-005 baselines and regression checks

See the [SC-005 rule, baseline format, and Windows guide](docs/sc005.md). `shadecheck baseline save` stores the full validated trace and recomputed result; `shadecheck test --baseline` and `shadecheck compare` evaluate new failures, higher severity, and newly observed behavior categories. Named evidence/report paths can be supplied explicitly. Comparisons require compatible rule selection, policy, and evidence modes. A saved known failure remains a strict failure.

Run `python scripts/privacy_regression.py` with the real backend running and a prior actual `regtest.py prove` trace available. It checks fresh aligned versus unaligned requests, a newly observed sync violation category, and MEDIUM-to-HIGH escalation using an explicitly labeled prefix and the complete actual broadcast trace. [Real CI run 37408670341](https://github.com/0xaje/ShadeCheck-/actions/runs/37408670341) passed all five comparison cases; the saved reports were reproduced exactly from the artifact. JSON/HTML comparisons include inspectable evidence and portable baselines. The prefix does not assert rejection or acceptance before those outcomes were observed.

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

`GetLatestBlock`, `GetBlockRange`, `GetTransaction`, `SendTransaction`, and `GetMempoolStream` are forwarded in the current observer. Other RPCs return UNIMPLEMENTED. This is not yet a full wallet sync proxy.

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

Each event includes sequence, wall clock and monotonic elapsed time, hashed transport peer, RPC/phase, payload size/fingerprint, mode, and hash chain. A SHA-256 payload fingerprint is **not** a Zcash transaction ID. Full raw transaction bytes are forwarded without being stored in proxy events. The SC-004 backend proof additionally saves the actual decoded local test transaction; native adapter events include test receiver addresses and wallet operation results. Hash chaining detects accidental editing; it is not a signature or protection against an author rewriting the complete chain.

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

## Acceptance status

The core CLI MVP passed its defined acceptance suite on a fresh Linux CI runner. All individual real milestones, including SC-005, are also verified on the developer's Windows machine. The consolidated Windows command awaits execution. No dashboard has been built. Passing this acceptance suite means the expected checks and exit codes were verified; it does not mean the tested architecture passed every privacy requirement or establish production readiness or anonymity. Broader rule-family behaviors and wallet support remain outside the documented coverage.

See [threat model](docs/threat-model.md) and [fixture provenance](fixtures/PROVENANCE.md).
