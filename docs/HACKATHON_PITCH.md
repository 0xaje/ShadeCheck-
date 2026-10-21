# ShadeCheck: submission narrative and two-minute video

## Product

Privacy CI for Zcash applications. A correctly shielded transaction can still be linked to observable application behavior. ShadeCheck records defined RPC/native-adapter events, evaluates five documented rule families, stores inspectable evidence, compares baselines, and returns enforceable CI results.

Primary user: a wallet/SDK developer who needs evidence that a release did not introduce a tested privacy regression. Track choice: Core & Tooling, subject to the organizer's current form/rules.

The implemented integration uses a controlled regtest zcashd wallet and protocol-authentic lightwalletd clients. It does not claim support for every wallet or discovery of new protocol vulnerabilities.

## Demonstration

Prepare the real backend before recording and disclose that preparation. Do not pretend the initial Docker build and shielded proof construction took sixty seconds. A recorded walkthrough must be labeled recorded; it must reference actual saved traces.

| Time | Picture / explanation |
| --- | --- |
| 0–15s | A shielded transaction can still expose broadcast linkage. Developers need reproducible behavior checks, not an anonymity score. |
| 15–40s | Actual signed shielded transaction submitted through observer; matching mempool bytes and independent node confirmation; SC-002 HIGH and strict exit 1. This links a connection to bytes, not a person. |
| 40–70s | SC-004 actual permissive payment has a transparent output; FullPrivacy rejects that recipient, then a shielded payment passes SC-004. SC-002 linkage is not claimed fixed. |
| 70–95s | Saved compatible baseline compared with a real narrower sync request; SC-005 regression and exact failing CI exit. Keep the same rule selection/policy. |
| 95–115s | Public recorded-run viewer: source CI link, evidence root, event inspection and an actual download. |
| 115–120s | Passing means no tested violation was observed in this environment. Repository contains the reproduction command and limitations. |

## Claims that are supported

- Actual upstream/native-wallet behavior in a controlled environment.
- Deterministic documented rules and inspectable findings.
- Recomputed portable baselines and evidence integrity checks.
- An explicit consumer Action that evaluates supplied captured events.
- Expected negative cases enforced with exact exit checks.

## Claims not to make

- First/only framework without a supporting landscape study.
- Complete anonymity, zero leaks, or proof of wallet ownership from a selected fetch.
- Exact wallet birthday inferred from an unaligned request.
- Unforgeable/immutable evidence: an author can rewrite a whole chain and recompute hashes.
- Five-minute support for arbitrary wallets, automatic Unified Address fallback, or a Zebra integration that has not been executed.
- PR approved/merged merely because a CLI printed PASS.

## Judge reproduction paths

1. Inspect the public recorded run, its source CI job, report/event downloads, and scope.
2. Clone/install and run `python scripts/acceptance.py` with Docker running.
3. Revalidate the saved output offline with `python scripts/acceptance.py --verify PATH`.
4. Run the documented consumer Action against captured real evidence; positive and negative tests must preserve exit codes.

Video, screenshots, and website must all refer to the same reviewed release commit/evidence run. Keep test keys local. Do not use real users' metadata as demo content.

## Suggested narration (record footage from the actual run)

“Zcash can shield a transaction while the application around it still exposes privacy-sensitive behavior. ShadeCheck gives developers a reproducible way to test defined behaviors before release.

Here is a real Sapling transaction from our controlled Zcash environment. The observer captures its submission, the backend accepts it, and identical bytes appear in the mempool. ShadeCheck reports a link between those bytes and the broadcasting connection. This identifies a connection, not a person.

Now look at payment policy. The permissive flow produces a transparent output under a requirement to remain shielded. FullPrivacy rejects that recipient, and a genuinely shielded payment changes the SC-004 result. That does not remove broadcast linkage.

Next, we compare a saved baseline with an actual narrower sync request. The regression produces a finding and a strict failing exit. The consumer Action preserves that result and renders an inspectable summary.

The dashboard can launch controlled local tests and show actual execution logs. The public viewer shows a labelled recorded run, its source CI commit, supporting events, and exact downloads. Judges can reproduce the full suite with one command.

Passing ShadeCheck does not establish anonymity. It means no violation of the selected documented tests was observed with the required coverage in this environment.”
