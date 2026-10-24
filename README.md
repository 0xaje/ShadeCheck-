<p align="center">
  <img src="docs/assets/shadecheck-banner.svg" alt="ShadeCheck — Privacy CI for Zcash applications. Observe. Inspect. Verify." width="100%" />
</p>

<p align="center">
  <a href="https://shade-check-nu.vercel.app/"><img alt="Open evidence demo" src="https://img.shields.io/badge/Demo-Explore%20real%20evidence-dcff9f?style=for-the-badge&amp;labelColor=142019" /></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-dcff9f?style=for-the-badge&amp;labelColor=142019" /></a>
  <a href="docs/acceptance.md"><img alt="Five documented rule families" src="https://img.shields.io/badge/Rules-5%20families-dcff9f?style=for-the-badge&amp;labelColor=142019" /></a>
</p>

<p align="center">
  <a href="https://shade-check-nu.vercel.app/"><strong>Open demo</strong></a> ·
  <a href="#run-the-real-system">Run locally</a> ·
  <a href="docs/threat-model.md">Threat model</a> ·
  <a href="docs/modern-wallet.md">Current wallet integration</a> ·
  <a href="https://github.com/0xaje/ShadeCheck-/actions">CI evidence</a>
</p>

# ShadeCheck

**Privacy CI for Zcash applications. Built for ZECATHON · Core &amp; Tooling.**

A transaction can be correctly shielded while application requests still expose clues. ShadeCheck helps Zcash wallet and SDK developers catch defined privacy-sensitive behaviors before release: capture real protocol events, evaluate deterministic rules, inspect the evidence, and compare against a baseline.

> Passing ShadeCheck means no violation of the tested rule was observed in the executed environment with the required coverage. **It does not establish anonymity.**

## Start here

| What you want to do | Where to go |
| --- | --- |
| Explore findings immediately | [Open the public evidence viewer](https://shade-check-nu.vercel.app/) — saved real regtest reports; no setup required |
| Try the first developer workflow | [Getting started](docs/GETTING_STARTED.md): saved proof or fresh baseline → unchanged → changed-request test |
| Connect your client and enforce CI | [Observer, requirement and consumer integration](docs/CLIENT_INTEGRATION.md) |
| Execute the full five-family suite | [Run locally](#run-the-real-system) with Python and Docker |
| Check what was actually verified | [Acceptance audit](docs/acceptance.md) and [validation record](docs/RELEASE_VALIDATION.md) |
| Inspect an independent client integration | [Current funded Zingo / Zebra / Zaino test](docs/modern-wallet.md) and [original evidence](examples/modern/README.md) |
| Understand the limits | [Threat model](docs/threat-model.md), [rule applicability](docs/rule-applicability.md), and [submission review](docs/JUDGE_REVIEW.md) |

<!-- Add the ShadeCheck-specific YouTube thumbnail/link here once its URL is supplied. Do not reuse another project's video. -->

## What the demo proves

- **Real controlled backend:** a local Zcash regtest node and lightwalletd, with actual signed transparent and Sapling transactions in the native-wallet scenarios.
- **Evidence-backed findings:** recorded RPC events support each finding; JSON and HTML reports are available for inspection.
- **Behavior comparisons:** deliberately weak flows fail the declared policy; controlled alternatives change selected results.
- **Regression gates:** saved baselines identify new failures, behavior categories, and increased severity; strict policy failures return nonzero exit codes.
- **Independent funded wallet:** unmodified Zingolib 7.0.0 on Zebra 7.0.0 / Zaino 0.10.1 synchronized, shielded real mined funds, sent a shielded payment and verified recipient receipt. The separate test recorded 1,009 events and two HIGH SC-002 findings, with strict exit 1. It uses explicit upstream local test transport; it does not audit production mixnet behavior.

The public website displays recorded evidence. Fresh execution runs on the developer's computer through the CLI or optional local dashboard runner.

```mermaid
flowchart TD
    Client["Client under test"] --> Observer["ShadeCheck observer"]
    Observer --> Backend["Controlled lightwalletd + Zcash regtest"]
    Observer --> Events["Normalized protocol evidence"]
    Events --> Rules["Deterministic privacy rules"]
    Baseline["Saved baseline"] --> Rules
    Rules --> Reports["Findings + JSON / HTML reports"]
    Rules --> Policy["PASS / WARN / FAIL + CI exit code"]
```

## Evidence privacy and useful policies

Fresh recordings use per-run keyed session identifiers and omit arbitrary broadcast response text. Local evidence files are private by default on POSIX; metadata remains sensitive and public export requires explicit acknowledgement. See [evidence handling](docs/evidence-privacy.md).

Select requirements that match your actual observer and workflow. A finding is not automatically a newly discovered vulnerability. See [rule applicability and developer actions](docs/rule-applicability.md).

## First developer workflow

Follow [getting started](docs/GETTING_STARTED.md) for Windows and Bash commands, expected outputs and troubleshooting. A separate example client retrieves real completed block ranges through the observer. The walkthrough validates a compliant baseline, a fresh unchanged run and an actual changed request, then asserts the resulting policy and regression exits. The [real onboarding CI](.github/workflows/developer-onboarding.yml) installs a wheel into a clean environment and tests the consumer Action against those traces. Its run and artifact verifier determine completion; this is not a claim of independent user adoption.

## Run the real system

The five-family acceptance suite uses a frozen zcashd/lightwalletd regression backend. It is a controlled test target, not a recommendation for a new production wallet backend. The separate [current Zebra/Zaino wallet integration](docs/modern-wallet.md) validates its own documented coverage.

Requirements: Git, Python 3.11+, and Docker Desktop with Linux containers (or Docker Engine/Compose on Linux). Start Docker and require both Client and Server in `docker version`.

From the cloned repository in Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m shadecheck.cli doctor
.\.venv\Scripts\python.exe scripts/acceptance.py
```

Linux/macOS Python commands:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python -m shadecheck.cli doctor
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

To run actual controlled tests from the local dashboard, use `shadecheck dashboard --enable-runner --project .` with Docker running. It launches fixed sync/acceptance drivers, shows actual logs/status, validates the new reports, and exposes their downloads. No arbitrary scan targets or shell commands are accepted. Default and public static views remain recorded-evidence viewers.

[Dashboard guide](docs/dashboard.md)

## Current-release wallet integration

The [funded-wallet gate](docs/modern-wallet.md) passed on the pinned current release: [real CI](https://github.com/0xaje/ShadeCheck-/actions/runs/40099904709), [original downloadable evidence](examples/modern/README.md). Funding, complete scans, shielding, shielded sending, node acceptance, exact mempool bytes, recipient receipt and strict SC-002 failure were verified. No source patches or public funds were used.

| Execution target | Verified scope | Boundary |
| --- | --- | --- |
| Zingolib 7.0.0 + Zebra 7.0.0 + Zaino 0.10.1 | Funded independent wallet; SC-002, two HIGH findings | Explicit upstream local test transport; not default mixnet behavior |
| Frozen zcashd 6.12.2 + pinned lightwalletd | All five rule families, weak/controlled alternatives, baselines, CLI and browser | Separate native-adapter and protocol-client scenarios; not one independent wallet audit |
| Historical Zingolib 3.0.1 sync | 101 blocks, 124 events; explicit SC-001 policy | Preserved historical evidence; no payment coverage or production vulnerability claim |

## Five initial rule families

| Rule | Implemented test | Boundary |
| --- | --- | --- |
| SC-001 | Block-range size/alignment against an explicit policy | Does not infer wallet birthday/history or cover timing fingerprints |
| SC-002 | Broadcast connection-to-payload association; HIGH adds accepted submission and exact mempool bytes | A connection is not a person; shielding does not remove broadcast linkage |
| SC-003 | Non-empty proper subset of IDs from a delivered multi-transaction compact block | Delivery/retrieval does not establish ownership or internal wallet processing |
| SC-004 | Explicit transparent recipient selection/execution under a shielded requirement | Trusted local adapter; automatic Unified Address fallback is not implemented |
| SC-005 | New failures, behavior categories, and severity increases against a compatible baseline | Stronger observation can increase severity without a code change |

[SC-001](docs/sc001.md) · [SC-002](docs/threat-model.md) · [SC-003](docs/sc003.md) · [SC-004](docs/sc004.md) · [SC-005](docs/sc005.md)

The proxy records rule-specific evidence for GetLatestBlock, GetBlockRange, GetTransaction, SendTransaction, and GetMempoolStream. Additional RPCs in the vendored protocol schema are forwarded with compatibility-only fingerprints and sizes; unknown methods remain UNIMPLEMENTED. Forwarding does not imply privacy rule coverage or universal wallet compatibility. See the [pinned independent Zingo CLI integration](docs/zingo-integration.md) for its real-execution gate and limitations.

The [historical independent synchronization record](docs/zingo-integration.md) remains available for audit alongside the current funded integration. Its older source version and narrower coverage are preserved explicitly.


## Evaluate your captured evidence in CI

Your integration test must first exercise its client through the ShadeCheck observer and save actual events. The Action does not automatically inspect a wallet's source code or run an application merely because it is installed.

```yaml
- uses: actions/checkout@v4
# Run your integration test through the observer and capture events.jsonl first.
- name: Evaluate captured broadcast evidence
  uses: 0xaje/ShadeCheck-@bbbbd166279edcbb92819dddaac6dc2443d6432e # Reviewed integration revision.
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
python scripts/export_site.py --acknowledge-public-evidence --suite out/acceptance/RUN --output public --source-run-url https://github.com/0xaje/ShadeCheck-/actions/runs/RUN_ID --source-commit FULL_40_CHARACTER_SHA
```

Vercel serves the committed `public` directory using vercel.json; `/api/data` maps to generated data and `/download/ID` maps to original artifact bytes. Export refuses an existing output directory. The CI workflow exports `out/site` as a reproducible deployment artifact. Runtime keys/credentials are never required to view recorded evidence.

[Submission and two-minute video guide](docs/HACKATHON_PITCH.md) · [Deploy/reproduction guide](docs/submission.md)

## Verified execution records

[Run 40081554868](https://github.com/0xaje/ShadeCheck-/actions/runs/40081554868) is green at source commit `74d2f8f199ed2b631c899aef8a25c722f4deeee4`: 53 unit checks, actual five-family Zcash acceptance, real positive/negative consumer Action gates, installed-wheel verification, local and static Chrome/mobile checks, and an actual dashboard-triggered sync job. Its 24 reports and 112 hashed acceptance artifacts were downloaded and independently revalidated. The committed public snapshot contains those exact reports, downloadable artifacts, and source provenance; it is recorded evidence, not a live scan. The newer funded-wallet gate has separate evidence and coverage.

[Validation record](docs/RELEASE_VALIDATION.md)

## Verification and scope

```sh
python -m unittest discover -s tests -v
python scripts/acceptance.py --verify out/acceptance/RUN
```

Unit/conformance fixtures are explicitly separated from real runtime evidence. Node and wallet-adapter records depend on trusted local test components. Spending keys stay in developer-owned local wallet volumes. Only dedicated regtest services are used; no arbitrary network scanning or production privacy guarantee is offered.

Node release and lightwalletd source revision are pinned; upstream base-image tags/package repositories may change. Actual image identities are recorded; builds are not claimed byte-identical or fully hermetic.

## License and attribution

ShadeCheck's original code is released under the [MIT License](LICENSE), copyright © 2026 Aje Oluwaseun Isaac ([@0xaje](https://github.com/0xaje)).

[THIRD_PARTY_LICENSE](THIRD_PARTY_LICENSE) contains Electric Coin Company's MIT notice for vendored lightwalletd protocol material. It is an upstream attribution notice, not a second project license or a duplicate to delete. See [third-party attribution](docs/third-party-attribution.md) and [fixture provenance](fixtures/PROVENANCE.md).

Built for [ZECATHON](https://thezecathon.com/), **Core & Tooling**. Zcash and Zingo names identify the ecosystem and tested upstream software; no endorsement is implied.
