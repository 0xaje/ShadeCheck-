# Consolidated MVP acceptance

Run the defined local integration from one entry point:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe scripts/acceptance.py
```

Docker Desktop must be running with Linux containers. No manual prepare/prove commands are needed: acceptance starts/checks the backend, creates real transactions, executes every comparison, and audits the resulting evidence. Do not run a second suite or mine blocks concurrently against the shared local wallet/chain volumes.

## What the result means

`SHADECHECK MVP ACCEPTANCE VERIFIED` means the acceptance checks behaved as required, including expected privacy failures. It does not mean the tested architecture passed every privacy requirement. `suite.json` and `suite.html` keep acceptance status separate from aggregate privacy status. The latter remains FAIL because genuine leak behaviors are deliberately exercised and SC-002 linkability remains visible at the broadcaster.

Each run saves its outputs in one unique out/acceptance directory. The subprocesses use SHADECHECK_OUTPUT_ROOT to keep their traces in that directory; historical outputs cannot satisfy this acceptance run. Existing local chain/wallet volumes are preserved. The workflow operates only against the dedicated regtest compose services.

## Definition of done audit

| Requirement | Executable check / evidence | Scope |
| --- | --- | --- |
| Real or protocol-authentic client | Native zcashd wallet constructs signed transparent/Sapling transactions; clients use official lightwalletd protobuf RPCs | Native local wallet plus protocol-authentic test clients, not every wallet |
| Actual events captured | Fresh upstream requests/responses; wallet-adapter records explicitly labeled | Observer and trusted native adapter boundaries documented |
| At least three behaviors | Broadcast linkability, narrow sync requests, selective retrieval, transparent recipient disclosure | Four defined behavior families |
| All five rules execute | Acceptance audits rule IDs from recomputed reports | Five families across a suite of traces; no invented single session |
| Evidence-backed failures | Required finding fields and exact embedded source-event equality | Hash-chain validation and re-evaluation, not author authentication |
| Weak configuration fails | SC-001 narrow, SC-003 subset, SC-004 permissive each require strict exit 1 | Defined local policies |
| Mitigation changes a result | Aligned sync, complete fetch, FullPrivacy each require scoped PASS/exit 0 | No production or anonymity claim |
| JSON output | CLI JSON command must round-trip to the saved result | Deterministic evaluation output |
| HTML output | Every base/comparison report has HTML, except one intentional duplicate CLI-equivalence result | Summary, coverage, findings, expandable evidence, comparison, limits |
| Baselines | Portable hashes/events/results validated; every comparison recomputed | Compatible test policies and evidence modes required |
| Strict non-zero failure | Drivers require exact exit codes; known failures remain FAIL | Missing coverage also remains non-zero |
| CI example | Regtest workflow invokes the same acceptance command and uploads its artifacts | Fresh Linux GitHub Actions runner |
| Clean-machine setup | Checkout, package installation, image build, empty-volume setup, actual acceptance | Fresh Linux CI; individual Windows milestones verified; consolidated Windows run separately verified when executed |
| Threat model and limitations | Rule documents and suite limitations | Explicit incomplete coverage listed below |
| No fake runtime data | Only real upstream/native evidence permitted in the acceptance artifact audit | Synthetic unit tests run separately and cannot supply runtime acceptance traces |

## Inspect and revalidate

```powershell
$latest = Get-ChildItem .\out\acceptance -Directory | Sort-Object Name -Descending | Select-Object -First 1
Start-Process (Join-Path $latest.FullName "suite.html")
.\.venv\Scripts\python.exe scripts/acceptance.py --verify $latest.FullName
```

Offline verification needs the installed Python package but performs no Docker operation. It checks every recorded artifact hash, revalidates event chains and portable baselines, recomputes each report, checks evidence equality, and repeats the cross-case acceptance assertions. Generated reports remain in their individual trace directories; suite.json indexes relative paths, evidence roots, rule selections, findings, and statuses. Logs record each executed step and its exit. The manifest excludes its own summary files; it is not signed.

The suite records actual Docker image identities in environment.json. The node release and lightwalletd source revision are pinned, while upstream base-image tags and package repositories may change. This setup is repeatable at the test-behavior level and is not claimed to be a fully hermetic byte-identical build.

## Fresh-machine setup

Install Git, Python 3.11+, and Docker Desktop with Linux containers/WSL 2. Run `docker version` and require both Client and Server. From a writable folder in PowerShell:

```powershell
git clone https://github.com/0xaje/ShadeCheck-.git ShadeCheck
cd ShadeCheck
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe scripts/acceptance.py
```

The first lightwalletd build and shielded proof construction may take several minutes. Linux:

```sh
git clone https://github.com/0xaje/ShadeCheck-.git ShadeCheck
cd ShadeCheck
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python scripts/acceptance.py
```

CI supplies Python and Docker on a fresh runner and executes the same command. On a workstation, stop with `python scripts/regtest.py stop`; volumes are preserved. Acceptance leaves the local backend running to permit inspection. Do not delete volumes unless you intend to discard the developer-owned test wallet and chain.

## Boundaries that remain

- SC-001 covers request size/alignment, not timing fingerprinting, repeated history, tip truncation, or reorg policies.
- SC-002 establishes observable connection-to-payload association, not identity or deanonymization; separate routing leaves the broadcaster's link intact.
- SC-003 observes delivery and ID-specific retrieval, not internal wallet processing or ownership.
- SC-004 covers the tested explicit transparent recipient path, not automatic Unified Address fallback or arbitrary wallet adapters.
- SC-005 compares documented behavior groups and severity, not leak frequency or all possible metadata changes. Increased severity may reflect stronger observation rather than a code change.
- The native adapter and node are trusted test components. Spending keys remain in developer-owned local wallet volumes; ShadeCheck does not receive or store them.
- Passing a defined rule means no violation was observed with the required coverage in the executed environment. It does not establish anonymity or production security.

## Verified fresh CI

[Run 37409730042](https://github.com/0xaje/ShadeCheck-/actions/runs/37409730042) passed on October 6, 2026 from a fresh GitHub Actions runner. It executed 18 steps, including 29 unit boundary tests, the actual node/lightwalletd setup, transparent and two shielded broadcast proofs, all rule comparisons, and all five explain commands. The final audit recomputed 24 reports and validated 112 hashed artifacts. Acceptance status was PASS; aggregate privacy status remained FAIL as required for the deliberately exposed behaviors.

The downloaded artifact was independently revalidated using the offline command. A temporary copy with a changed evidence file was rejected with exit 2. Consolidated Windows execution awaits verification; each individual real milestone has already been verified on Windows.
