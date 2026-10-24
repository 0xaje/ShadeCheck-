# A real client integration example

This separate Python process makes an actual GetBlockRange call to your controlled observer and requires delivery of every requested height. It uses ShadeCheck's installed protocol bindings and gRPC dependency. It is not a wallet, synthetic server, transaction generator or consensus verifier.

Start with the [fresh developer walkthrough](../../docs/GETTING_STARTED.md), which installs/runs the package, captures three real traces, independently checks block hashes, saves a baseline and enforces the expected outcomes. The [client integration guide](../../docs/CLIENT_INTEGRATION.md) explains manual observer wiring and the consumer Action.

`policy.json` is an example requirement for completed historical 20-block aligned ranges, not a universal wallet requirement or proof of anonymity. The [CI workflow](../../.github/workflows/developer-onboarding.yml) tests this example from a clean installed wheel; that is automated execution evidence, not independent user adoption.

## Original recorded onboarding proof

[Real CI run 40103273814](https://github.com/0xaje/ShadeCheck-/actions/runs/40103273814) passed at source `a21f4ed8f46e70d704477e9e90467b11fcbcc0b1`. It built a wheel, installed it into a fresh consumer environment, executed the external client outside the checkout, verified returned block hashes against the real node, and asserted both consumer Action outcomes. This is automated setup validation, not an independent person completing onboarding.

The original `recorded-walkthrough-20261024.zip` is 56,714 bytes, SHA-256 `312991d6c82108a37af4135ea14439c253b111c8a14f521d641bd51fb5bfe4cf`. It was downloaded, hash checked and revalidated locally. It includes the walkthrough plus passing/failing consumer Action outputs, with no wallet files or keys.

- Baseline and fresh unchanged requests: heights 80–99, PASS and strict exit 0.
- Changed request: heights 83–89, SC-001 FAIL and strict exit 1.
- Compatible baseline comparison: unchanged PASS with zero regressions; changed FAIL with one SC-005 regression.
- 50 actual observer events across three traces; 47 delivered block responses were checked against the canonical node.

Inspect this saved workflow without Docker:

```bash
python -m zipfile -e examples/range-client/recorded-walkthrough-20261024.zip out/onboarding-recorded
python scripts/developer_walkthrough.py --verify out/onboarding-recorded/onboarding-ci
```

Open `out/onboarding-recorded/onboarding-ci/changed-run-comparison.html` to see the developer decision. The verifier recomputes the walkthrough under `onboarding-ci`; the accompanying consumer Action files are separate CI outputs. Offline replay is not a fresh client execution or authenticated authorship. [Original provenance](provenance.json).
