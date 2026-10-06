# Real comparison of RPC observer roles

This experiment changes which RPC observer sees a submission. It does not eliminate broadcast linkability: the broadcast service still sees the transaction bytes and submitting connection.

## What runs

The command constructs two fresh, genuinely proved Sapling-to-Sapling transactions on the dedicated local wallet node. Every transaction must have actual Sapling spends and outputs and zero transparent inputs or outputs. Each first submission to the verification backend goes through a real ShadeCheck observer and real lightwalletd.

1. Unified: the client requests the actual latest block, submits the transaction, and observes matching mempool bytes through the same endpoint and connection.
2. Separated: the client requests the latest block and observes mempool bytes through a read observer. It submits through a separate broadcast observer, which also records acceptance and matching mempool bytes.

Both configurations require independent node RPC confirmation of the exact accepted bytes. All observer evidence is retained and hash-chain validated. Each observer receives its own JSON and HTML report; comparison.json contains counts, statuses, and evidence roots derived from these reports.

## Interpret the result

| Observer | Unified | Separated |
| --- | --- | --- |
| Read observer | Submission and matching observation: SC-002 HIGH / FAIL | Matching observation without submission: WARN, no broadcast coverage |
| Broadcast observer | Same endpoint as read observer: HIGH / FAIL | Separate endpoint: HIGH / FAIL |

WARN has strict CLI exit 2, not exit 0. The experiment driver exits 0 only when it verifies the expected routing and real acceptance in both runs. No missing coverage is labeled PASS.

This is an observer-scoped routing change. Both local observer endpoints share one lightwalletd/verifier backend. It demonstrates role separation, not independent operators or an anonymity network. The shared backend, colluding observers, or an adversary with both records can correlate exact transaction fingerprints and timing. Other client metadata can also allow correlation. A production privacy claim requires an appropriate separate trust boundary and further tests.

## Windows PowerShell

From your repository, with Docker Desktop running:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe scripts/regtest.py up
.\.venv\Scripts\python.exe scripts/broadcast_comparison.py
```

The command creates fresh transactions itself. It mines actual setup blocks and may confirm earlier local mempool transactions. Allow it to finish without manually mining blocks. Output is saved beneath out/comparison in a unique run directory.

The wallet node first accepts the measured transactions locally for construction; that acceptance is disclosed in each backend-proof.json. Their first submission to the separate verification backend is the measured action. Spending keys remain in the developer-owned local wallet volume.

## Verified evidence

[Real CI run 37402373442](https://github.com/0xaje/ShadeCheck-/actions/runs/37402373442) passed on October 6, 2026. Both measured transactions had one Sapling spend, two Sapling outputs, zero transparent inputs/outputs, actual verifier acceptance, and independent exact-byte confirmation. Artifact inspection validated all three observer hash chains and recomputed their reports: unified HIGH/FAIL; separated read observer WARN with zero submissions; separated broadcast observer HIGH/FAIL.
