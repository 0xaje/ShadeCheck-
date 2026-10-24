# ShadeCheck: final two-minute demo

This is the current master recording plan. It replaces the earlier sync-only presentation. Use the [Antigravity editing prompt](VIDEO_UPDATE_PROMPT.md) for the same sequence and narration; do not combine it with an older script.

Target: 118 seconds of content plus a two-second end hold, landscape 1080p. Measure the generated narration and the final export; the submission form requests a two-minute video. No finished video is claimed by this document.

## The story

A developer declares a requirement, captures a real application request, checks a compatible baseline, and gets an enforceable CI decision. An independent funded-wallet workflow provides separate integration evidence. The public viewer makes the original five-family evidence inspectable.

These are separate real records, with their own source revisions:

| Scene | Source | Verified scope |
| --- | --- | --- |
| Developer workflow | [Original onboarding CI](https://github.com/0xaje/ShadeCheck-/actions/runs/40103273814), [original archive](../examples/range-client/README.md#original-recorded-onboarding-proof) | Separate protocol client; SC-001 requirement and SC-005 baseline comparison |
| Consumer gates on merged code | [Merged onboarding CI](https://github.com/0xaje/ShadeCheck-/actions/runs/40103918913) | Clean installed environment, real captures, exact positive/negative Action outcomes |
| Current funded wallet | [Funded CI](https://github.com/0xaje/ShadeCheck-/actions/runs/40099904709), [original archive](../examples/modern/README.md) | Unmodified Zingolib 7.0.0 on Zebra 7 / Zaino 0.10.1; explicit local test transport; SC-002 |
| Public viewer | https://shade-check-nu.vercel.app/ | Separate recorded five-family acceptance run, source linked inside the viewer |

Do not present the range-client configuration change as a modification to Zingo, or claim the funded Zingo trace covers every rule. The source release tag is Zingolib 7.0.0; its upstream CLI binary still prints 0.1.1.

## Prepare the screens

Pull the repository and install it using [getting started](GETTING_STARTED.md). Existing reviewed footage can be reused if it shows these actual records and scope. The following commands extract saved evidence; they do not run a new wallet or network test.

PowerShell:

```powershell
.\.venv\Scripts\python.exe -m zipfile -e examples/range-client/recorded-walkthrough-20261024.zip out/onboarding-recorded
.\.venv\Scripts\python.exe scripts/developer_walkthrough.py --verify out/onboarding-recorded/onboarding-ci
.\.venv\Scripts\python.exe -m zipfile -e examples/modern/recorded-regtest-20261024.zip out/modern-recorded
.\.venv\Scripts\python.exe scripts/modern_wallet.py --verify out/modern-recorded/20261024T135437-8bcfe43c
```

Bash/WSL:

```bash
./.venv/bin/python -m zipfile -e examples/range-client/recorded-walkthrough-20261024.zip out/onboarding-recorded
./.venv/bin/python scripts/developer_walkthrough.py --verify out/onboarding-recorded/onboarding-ci
./.venv/bin/python -m zipfile -e examples/modern/recorded-regtest-20261024.zip out/modern-recorded
./.venv/bin/python scripts/modern_wallet.py --verify out/modern-recorded/20261024T135437-8bcfe43c
```

Prepare these tabs/files before recording:

1. `out/onboarding-recorded/onboarding-ci/policy.json`.
2. `baseline-run/report.html` and `unchanged-run-comparison.html` inside that same folder.
3. `changed-run/report.html` and `changed-run-comparison.html` inside that folder. The comparison includes the underlying SC-001 finding and one SC-005 regression; do not call them two independent leaks.
4. Merged onboarding CI: open job `onboarding`. Show the compliant and changed consumer gates and the subsequent exact negative-outcome assertion. The deliberately failing step is expected; the overall job must be successful.
5. Funded wallet CI: open job `modern`, step `Real funded wallet receive and send through observer`. Locate the shielding/sending lines and final `CURRENT INDEPENDENT WALLET RECEIVE/SEND VERIFIED` line.
6. `out/modern-recorded/20261024T135437-8bcfe43c/recipient-receipt.json`: show `total_ironwood_balance: 100000` and `total_transparent_balance: 0`. Open that folder's `report.html` showing two HIGH SC-002 findings.
7. Public viewer: show the acceptance/privacy distinction, the source link, report evidence, and Download run.

Use a readable zoom and Do Not Disturb. Hide unrelated accounts, wallet files, keys and notifications. Do not zoom so far out that report text becomes illegible.

If you instead record a fresh local walkthrough, run the documented command and keep its actual outputs together. Label a removed wait “Wait shortened”. Label saved artifact/CI scenes “Recorded real execution”; never describe them as a test running live during the video.

## Exact sequence and narration

The timings are editing targets. The narration is approximately 203 words; actual voice duration must be checked. Keep natural speech and trim navigation pauses rather than speeding through evidence.

| Time | Show | Exact narration |
| --- | --- | --- |
| 0:00–0:12 | ShadeCheck title over real application footage; short problem caption | Zcash can shield a transaction while application requests still reveal clues. ShadeCheck helps wallet and SDK developers test defined privacy behaviors before release. |
| 0:12–0:26 | Actual policy JSON; point to chunk_size 20 and alignment_height 0 | Here is a concrete requirement: our example client must request completed historical blocks in aligned batches of twenty. We capture its actual requests through a local observer. |
| 0:26–0:46 | Baseline PASS, unchanged comparison with zero regressions, then changed request and its regression | The baseline passes. A fresh unchanged run also passes, with zero regressions. A changed seven-block request violates the requirement. ShadeCheck records the evidence and reports one new regression. This is a controlled protocol client. |
| 0:46–1:00 | Actual passing/failing consumer gates, then successful exact-outcome assertion | The consumer CI check requires the correct outcomes: unchanged passes, while the violating request returns exit one. A process error cannot substitute for that policy failure. |
| 1:00–1:25 | Actual funded-wallet CI, recipient receipt, then two HIGH SC-002 findings | We also verified an unmodified current Zingo release on Zebra and Zaino. It shielded mined regtest funds, sent a shielded payment, and the recipient verified receipt. ShadeCheck observed both broadcasts. This uses upstream’s explicit local test transport. |
| 1:25–1:44 | Public viewer: source, evidence and original download | This public viewer contains a separate recorded five-rule acceptance suite. Developers can inspect events, reports and compatible baseline comparisons, then download the original evidence. Green acceptance means expected outcomes were verified, including privacy failures. |
| 1:44–1:58 | Repository getting-started guide and product title | ShadeCheck turns declared requirements into reproducible CI checks. It does not establish anonymity. The repository includes setup instructions, integrations and recomputable evidence. |
| 1:58–2:00 | Hold title, repository and demo URL | No additional narration. |

Use these short captions where relevant:

- Protocol-client scenes: “Declared completed-range policy · controlled protocol client”.
- Saved records: “Recorded real execution”.
- Wallet scene throughout: “Explicit upstream local test transport · SC-002”.
- Public viewer: “Separate recorded suite · five rule families”.
- Closing: “Passing tested requirements does not establish anonymity”.

The batching requirement needs architecture-specific exceptions for live tips, reorgs and resume behavior. Returning more blocks has a cost. The short video need not explain every exception, but the policy caption and linked guide must remain clear. Direct broadcast visibility is not automatically a new production wallet vulnerability.

## Final check before upload

- Total duration is at most 120 seconds, including end cards and transitions.
- Each result is readable and belongs to the source shown.
- No animation invents RPCs, statuses, receipts, transaction IDs or a live scan.
- Acceptance success is distinguished from intentionally failing privacy requirements.
- Saved versus fresh execution is labelled accurately.
- The default production mixnet is not claimed as tested.
- No broad adoption, independent unfamiliar-user success, privacy score or prize guarantee is claimed.
- The actual final MP4 has been watched end to end with audio.

The unfamiliar-reader exercise remains a separate pending task in [ONBOARDING_REVIEW.md](ONBOARDING_REVIEW.md). It must not be marked complete from this recording or an assistant review.

Use the actual ShadeCheck video URL after upload. If changing the hackathon video URL or description, press SUBMIT again; the supplied form says saving a draft alone removes submitted status. Repository updates alone do not change that form.
