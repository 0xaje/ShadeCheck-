# Start using ShadeCheck

ShadeCheck checks declared, observable Zcash application behavior and produces evidence-backed CI results. The public website displays recorded evidence. Fresh execution happens in your local checkout or GitHub Actions.

Choose a path:

| Goal | Requirements | What you get |
| --- | --- | --- |
| Inspect the current funded-wallet proof | Git, Python 3.11+; package dependencies | Recomputed saved evidence; no Docker, Rust, funds or wallet required |
| Run a small fresh developer workflow | Above plus Docker Linux engine and Compose v2 | Three real client traces, a baseline, HTML/JSON reports and tested CI decisions |
| Test the current independent wallet yourself | Docker, Rust and native build tools | A fresh funded Zingo / Zebra / Zaino test; [separate instructions](modern-wallet.md) |

## 1. Install in a fresh user-owned directory

Use your home directory, not Windows System32. Keep separate virtual environments for Windows and WSL/Linux. These commands clone a new checkout; they do not delete existing evidence or wallet data.

Windows PowerShell:

```powershell
cd $HOME
git clone https://github.com/0xaje/ShadeCheck- ShadeCheck
cd ShadeCheck
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
```

Bash/WSL/Linux:

```bash
cd ~
git clone https://github.com/0xaje/ShadeCheck- ShadeCheck
cd ShadeCheck
python3 -m venv .venv
./.venv/bin/python -m pip install .
```

The commands below use `python` as shorthand for your new environment's Python. On PowerShell substitute `.\.venv\Scripts\python.exe`; on Bash substitute `./.venv/bin/python`. Activation is optional.

## 2. Inspect real recorded wallet evidence first

```bash
python -m zipfile -e examples/modern/recorded-regtest-20261024.zip out/modern-recorded
python scripts/modern_wallet.py --verify out/modern-recorded/20261024T135437-8bcfe43c
```

Expect `MODERN WALLET ARTIFACTS VERIFIED`. Open that directory's `report.html`. The two HIGH SC-002 findings describe observable broadcasts in explicit upstream local test transport. Verification success means saved evidence recomputed correctly; it does not mean the privacy report passed or that a fresh wallet ran on your computer. [Exact source CI and limits](../examples/modern/README.md).

## 3. Run the fresh developer walkthrough

Start Docker Desktop with Linux containers, or Docker Engine with Compose v2. Then:

```bash
python -m shadecheck.cli doctor
python scripts/developer_walkthrough.py
```

`doctor` must report READY. This checks prerequisites only. The walkthrough starts the dedicated frozen regression backend, checks its regtest network, then runs a separate client process outside the checkout. The initial image build can take several minutes; keep the terminal open. It uses actual locally generated blocks and no public funds. No new transaction or wallet integration is claimed by this range-client example.

The declared requirement is: **for this completed historical range, the block-serving observer must see a 20-block request beginning at a multiple of 20**.

| Actual behavior | Privacy result | Strict CLI exit | Baseline comparison |
| --- | --- | --- | --- |
| Compliant request: 20 aligned blocks | PASS | 0 | Saved as baseline |
| Fresh unchanged request: same 20 blocks | PASS | 0 | PASS, zero regressions |
| Changed request: seven blocks starting three blocks later | FAIL, SC-001 | 1 | FAIL, one SC-005 regression |

Every response is checked against the canonical node. The script exits 0 only after all expected outcomes have been verified, including the deliberately failing request. An execution error returns 2; it is never accepted as the expected policy failure.

At completion, the terminal prints `REAL DEVELOPER WALKTHROUGH VERIFIED` and the exact output directory. Inspect:

- `policy.json`: the requirement selected before the requests.
- `baseline-run/`, `unchanged-run/`, `changed-run/`: actual events, external-client receipts, node proofs and JSON/HTML reports.
- `baseline.json`: portable evidence-backed baseline.
- `changed-run-comparison.html`: the new regression and its current evidence.
- `walkthrough.json`: original artifact inventory and asserted exit codes.

The program chooses a unique output directory by default. `--output PATH` requires a new directory and preserves existing files. It does not stop Docker after a local run; the backend remains available for integration work. Do not run overlapping suites against the same dedicated stack.

To inspect a saved walkthrough later without starting Docker:

```bash
python scripts/developer_walkthrough.py --verify out/developer-walkthrough/YOUR-RUN
```

This checks recorded consistency, not historical authorship or a new consensus execution. Replacing `YOUR-RUN` with the printed directory is required.

## 4. Decide whether this policy belongs in your application

This test is useful when your client deliberately promises fixed historical range batching to this observer. It does not prove wallet history, ownership or anonymity. Fetching 20 blocks rather than seven returns 13 additional blocks in this example; actual bandwidth and timing costs depend on their contents and transport.

Live tip truncation, reorgs and resuming may legitimately require other patterns. Do not copy this strict policy onto every wallet. [Rule applicability](rule-applicability.md) explains exceptions. [Integrate a client](CLIENT_INTEGRATION.md) shows the observer and CI wiring.

For your own implementation, fix the request scheduling that violates the intended requirement, then capture a fresh run. Do not repair evidence, loosen a requirement merely for a green badge, or replace a failing baseline without investigation.

## If setup stops

| Symptom | Next action |
| --- | --- |
| `doctor` is BLOCKED / Docker pipe missing | Start Docker Desktop, select Linux containers, and check `docker version` shows a Server. Rerun doctor. |
| Python virtual environment reports permission denied | Use a fresh checkout under your own home directory and a new user-owned environment. Do not install the project with sudo to bypass ownership. |
| Python cannot import grpc or shadecheck | Run pip install with the same environment's Python used to launch the script. |
| No completed range / backend is not ready | Wait for the initial backend startup to finish; inspect `python scripts/regtest.py check`. Do not substitute saved data for fresh execution. |
| Existing output directory | Use the default unique directory or choose a different `--output` path. |
| WARN or exit 2 | Inspect required coverage and the error. Missing evidence or execution failure is not a passing privacy test. |

On Bash: `docker compose -f integration/compose.yml down` stops this dedicated backend while retaining its volumes. Do not add `-v` to routine shutdown. Windows users can run the same Docker command in PowerShell.

## What this onboarding check establishes

The automated workflow builds an actual wheel, installs it into a fresh virtual environment, runs the example client outside the checkout, validates real node-backed results, then exercises passing and failing consumer Actions. Its completion status comes from CI and the artifact verifier. It does not establish that an unfamiliar person can follow the instructions unaided. Use the [independent reader exercise](ONBOARDING_REVIEW.md) to test that separately.
