# ShadeCheck

**Privacy CI for Zcash applications.**

ShadeCheck evaluates defined observable Zcash application behaviors against documented privacy tests. Passing means no violation of the selected tests was observed with the required coverage. It does not establish anonymity.

A shielded transaction can still be associated with the connection broadcasting it. ShadeCheck records actual RPC behavior, evaluates deterministic rules, preserves inspectable evidence, compares baselines, and returns enforceable CI exit codes.

## Run the real system

Requirements: Git, Python 3.11+, and Docker Desktop with Linux containers (or Docker Engine/Compose on Linux). Start Docker and require both Client and Server in `docker version`.

From the cloned repository in Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe scripts/acceptance.py
```

Linux/macOS Python commands:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python scripts/acceptance.py
```

The command starts a dedicated regtest node and pinned lightwalletd source, constructs real signed transparent and Sapling transactions, captures actual events, runs all five rule families, and verifies expected policy outcomes. The first build/proof construction takes several minutes. Existing developer-owned local wallet/chain volumes are preserved; do not run two suites concurrently.

Acceptance PASS means the checks produced their required outcomes. Aggregate privacy remains FAIL because deliberately weak flows and broadcast linkage are exercised. No fabricated runtime events or backend acceptance are used.

[Setup and troubleshooting](docs/regtest-setup.md) · [Acceptance audit](docs/acceptance.md) · [Threat model](docs/threat-model.md)

## Inspect a recorded real run

```powershell
.\.venv\Scripts\shadecheck.exe demo
.\.venv\Scripts\shadecheck.exe dashboard
```

Open http://127.0.0.1:9070. Both commands validate the newest completed out/acceptance run. `demo --suite PATH` gives a **recorded evidence walkthrough**, not new network execution. With no saved evidence it fails clearly. It never invents a transaction or a PASS result.

The dashboard shows report filters, findings, source events, baseline changes, rule coverage/limits, and byte-exact downloads. Large integers are displayed as decimal strings to preserve nanosecond precision; original downloads retain their exact numeric types. No Node installation is needed for the CLI/dashboard. Optional `npm run dev`, `npm run demo`, and `npm test` launch the same Python commands on Windows and POSIX systems.

[Dashboard guide](docs/dashboard.md)

## Five initial rule families

| Rule | Implemented test | Boundary |
| --- | --- | --- |
| SC-001 | Block-range size/alignment against an explicit policy | Does not infer wallet birthday/history or cover timing fingerprints |
| SC-002 | Broadcast connection-to-payload association; HIGH adds accepted submission and exact mempool bytes | A connection is not a person; shielding does not remove broadcast linkage |
| SC-003 | Non-empty proper subset of IDs from a delivered multi-transaction compact block | Delivery/retrieval does not establish ownership or internal wallet processing |
| SC-004 | Explicit transparent recipient selection/execution under a shielded requirement | Trusted local adapter; automatic Unified Address fallback is not implemented |
| SC-005 | New failures, behavior categories, and severity increases against a compatible baseline | Stronger observation can increase severity without a code change |

[SC-001](docs/sc001.md) · [SC-002](docs/threat-model.md) · [SC-003](docs/sc003.md) · [SC-004](docs/sc004.md) · [SC-005](docs/sc005.md)

The proxy forwards GetLatestBlock, GetBlockRange, GetTransaction, SendTransaction, and GetMempoolStream. Other methods return UNIMPLEMENTED. This is a native local wallet/protocol-client integration, not universal wallet compatibility.

## Evaluate your captured evidence in CI

Your integration test must first exercise its client through the ShadeCheck observer and save actual events. The Action does not automatically inspect a wallet's source code or run an application merely because it is installed.

```yaml
- uses: actions/checkout@v4
# Run your integration test through the observer and capture events.jsonl first.
- name: Evaluate captured broadcast evidence
  uses: 0xaje/ShadeCheck-@main # Pin a reviewed release commit for reproducible use.
  with:
    events: out/client/events.jsonl
    rules: SC-002
    policy: strict
    output-dir: out/privacy-gate
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: privacy-evidence
    path: out/privacy-gate/
```

For SC-001/SC-004 supply `config`; for comparisons supply `baseline` with compatible rules/policies. The Action defaults to **no source** and exits 2 unless exactly one explicit source is supplied. A fixture is available only as explicitly selected protocol conformance input; it is not real-backend acceptance or application privacy evidence.

Strict findings return 1. Invalid execution or strict missing coverage returns 2. Configure the job as a required repository check to enforce merge restrictions. A PASS does not automatically approve or merge a pull request. The real acceptance workflow exercises the Action on actual aligned and narrow traces and requires exact success/failure outcomes. The separate fixture workflow asserts its expected rejection instead of ignoring errors.

## Baselines and reports

```sh
shadecheck test --events events.jsonl --rules SC-002 --output out/report.json
shadecheck report --format json
shadecheck report --format html --output out/report.html
shadecheck report --format markdown
shadecheck baseline save --events events.jsonl --input out/report.json --output baseline.json
shadecheck test --events new-events.jsonl --rules SC-002 --baseline baseline.json
shadecheck explain SC-003
```

Baselines include the full validated trace and recomputed result. Existing baselines are not silently overwritten; known strict failures remain failures. Evidence SHA-256 values are fingerprints, not Zcash transaction IDs. Hash chains detect inconsistent editing; they are not signatures and do not prevent a malicious author rewriting the whole trace.

## Public deployment and judging

The public site is a **recorded real-regtest evidence viewer**. It must be exported from a validated acceptance directory, with its source CI run and commit. It does not execute a scan when someone changes a tab.

```sh
python scripts/export_site.py --suite out/acceptance/RUN --output public --source-run-url https://github.com/0xaje/ShadeCheck-/actions/runs/RUN_ID --source-commit FULL_40_CHARACTER_SHA
```

Vercel serves the committed `public` directory using vercel.json; `/api/data` maps to generated data and `/download/ID` maps to original artifact bytes. Export refuses an existing output directory. The CI workflow exports `out/site` as a reproducible deployment artifact. Runtime keys/credentials are never required to view recorded evidence.

[Submission and two-minute video guide](docs/HACKATHON_PITCH.md) · [Deploy/reproduction guide](docs/submission.md)

## Verification and scope

```sh
python -m unittest discover -s tests -v
python scripts/acceptance.py --verify out/acceptance/RUN
```

Unit/conformance fixtures are explicitly separated from real runtime evidence. Node and wallet-adapter records depend on trusted local test components. Spending keys stay in developer-owned local wallet volumes. Only dedicated regtest services are used; no arbitrary network scanning or production privacy guarantee is offered.

Node release and lightwalletd source revision are pinned; upstream base-image tags/package repositories may change. Actual image identities are recorded; builds are not claimed byte-identical or fully hermetic.

[MIT project license](LICENSE). Upstream notices are preserved in [THIRD_PARTY_LICENSE](THIRD_PARTY_LICENSE) and [fixture provenance](fixtures/PROVENANCE.md).
