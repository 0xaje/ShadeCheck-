# Real local backend: Windows PowerShell

This setup creates an actual isolated Zcash regtest node and lightwalletd. The wallet generates local coins and signs a transparent transaction; the client broadcasts it through ShadeCheck. No fixture or mock replaces acceptance. The observer then captures the identical bytes from lightwalletd's actual mempool stream, and the script independently confirms the transaction in the node's mempool.

This proves SC-002 transport linkability using a transparent transaction. This transparent proof alone does not demonstrate a shielded wallet flow, anonymity, or mitigation. The [shielded guide](shielded-regtest.md) and [consolidated acceptance workflow](acceptance.md) add the verified shielded and rule-comparison paths. All test keys remain inside the developer's local node wallet.

Validated with an actual node and lightwalletd in [GitHub Actions](https://github.com/0xaje/ShadeCheck-/actions/runs/37396184795) on October 6, 2026. The downloaded evidence contained six captured events with a valid hash chain, one HIGH finding supported by three events, backend response code 0, and independently matching node mempool data. These commands were also verified on the developer's Windows machine.

## Prerequisites

Install Docker Desktop for Windows with Linux containers and the WSL 2 backend, Git, and Python 3.11+. Start Docker Desktop and wait until its engine is running.

In PowerShell:

```powershell
docker version
docker compose version
git --version
py --version
```

`docker version` must show both Client and Server. If Server is missing, start/fix Docker Desktop before proceeding.

## Update and install

From your existing ShadeCheck repository:

```powershell
git pull --ff-only
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
```

You do not need to activate PowerShell scripts.

## Start and check the backend

```powershell
.\.venv\Scripts\python.exe scripts/regtest.py up
.\.venv\Scripts\python.exe scripts/regtest.py check
```

The first run downloads the node image and builds lightwalletd from the pinned source revision. It then verifies the actual node chain is regtest, generates 110 local blocks when necessary, and verifies lightwalletd's reported chain. Each failure exits non-zero rather than inventing readiness.

Node: `electriccoinco/zcashd:v6.12.2`, solely as a frozen local regression backend. This is deprecated software and is not the production-node recommendation. lightwalletd: source revision `d16d48124e9ad4157ebc2324b5090c6ba201470c`. The node image tag and build base images are version tags, not immutable image digests; the application source revision is pinned. No node RPC or P2P port is published. lightwalletd is exposed only on localhost:9067.

Expected check output includes:

- node_chain: regtest
- node_height: at least 110
- lightwalletd_chain: regtest
- actual node version and lightwalletd source revision

## Prepare a real signed transaction

```powershell
.\.venv\Scripts\python.exe scripts/regtest.py prepare
```

The local wallet selects a mature output, creates a fresh receiver, builds a transaction with a fee, signs it, and obtains its actual txid from the node's decoder. It does not broadcast. The transaction file is saved under the ignored .shadecheck directory; no spending keys are exported.

## Execute the full proof

```powershell
.\.venv\Scripts\python.exe scripts/regtest.py prove
```

This starts and stops the ShadeCheck observer automatically; no second terminal is needed. It fails if the transaction is rejected, no matching mempool bytes arrive, the node confirmation disagrees, HIGH is not justified, or the strict CLI exit is not 1.

Successful output is `SC-002 REAL REGTEST PROOF VERIFIED`. The orchestration script exits 0 because it verified the expected strict CLI exit 1. Evidence, backend confirmation, JSON report, and HTML report are saved in a unique out/regtest subdirectory.

To open the latest report:

```powershell
$latest = Get-ChildItem .\out\regtest -Directory | Sort-Object Name -Descending | Select-Object -First 1
Start-Process (Join-Path $latest.FullName "report.html")
```

Do not mine another block during the proof. For another run, use prepare then prove again.

## Troubleshooting and stopping

```powershell
docker compose -f integration/compose.yml ps
docker compose -f integration/compose.yml logs --tail 80 zcashd lightwalletd
.\.venv\Scripts\python.exe scripts/regtest.py stop
```

Stop preserves local wallet and chain volumes. Do not delete volumes unless you intend to discard this local test wallet and chain.

## Source references

- Node regtest coinbase behavior: https://github.com/zcash/zcash/blob/v6.12.2/src/chainparams.cpp
- Raw transaction creation/signing tests: https://github.com/zcash/zcash/blob/v6.12.2/qa/rpc-tests/rawtransactions.py
- Bundled Sapling and lazy Sprout parameters: https://github.com/zcash/zcash/blob/v6.12.2/src/init.cpp
- Node deprecation is not enforced on regtest: https://github.com/zcash/zcash/blob/v6.12.2/src/deprecation.cpp
- lightwalletd actual broadcast: https://github.com/zcash/lightwalletd/blob/d16d48124e9ad4157ebc2324b5090c6ba201470c/frontend/service.go
- Actual mempool stream: https://github.com/zcash/lightwalletd/blob/d16d48124e9ad4157ebc2324b5090c6ba201470c/common/mempool.go
