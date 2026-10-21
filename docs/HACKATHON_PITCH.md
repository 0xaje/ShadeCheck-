# ShadeCheck: submission narrative and two-minute video

## Product

Privacy CI for Zcash applications. A correctly shielded transaction can still be linked to observable application behavior. ShadeCheck records defined RPC/native-adapter events, evaluates five documented rule families, stores inspectable evidence, compares baselines, and returns enforceable CI results.

Primary user: a wallet/SDK developer who needs evidence that a release did not introduce a tested privacy regression. Track choice: Core & Tooling, subject to the organizer's current form/rules.

The implementation uses a controlled regtest zcashd wallet, protocol-authentic lightwalletd clients, and a separately verified pinned independent Zingo CLI synchronization workflow. It does not claim support for every wallet or discovery of new protocol vulnerabilities.

## Demonstration

Use the [final step-by-step recording guide](VIDEO_RECORDING_GUIDE.md) as the primary script. It includes the deployed recorded-evidence viewer, exact filters, a fresh local sync comparison, saved baseline navigation, the verified independent Zingo sync experiment, narration, captions, and recording checks. Keep the opening brief and prioritize inspectable evidence.

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

## Narration and navigation

The authoritative narration and screen sequence are in the [recording guide](VIDEO_RECORDING_GUIDE.md). Do not combine multiple scripts into one short video.
