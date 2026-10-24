# A real client integration example

This separate Python process makes an actual GetBlockRange call to your controlled observer and requires delivery of every requested height. It uses ShadeCheck's installed protocol bindings and gRPC dependency. It is not a wallet, synthetic server, transaction generator or consensus verifier.

Start with the [fresh developer walkthrough](../../docs/GETTING_STARTED.md), which installs/runs the package, captures three real traces, independently checks block hashes, saves a baseline and enforces the expected outcomes. The [client integration guide](../../docs/CLIENT_INTEGRATION.md) explains manual observer wiring and the consumer Action.

`policy.json` is an example requirement for completed historical 20-block aligned ranges, not a universal wallet requirement or proof of anonymity. The [CI workflow](../../.github/workflows/developer-onboarding.yml) tests this example from a clean installed wheel; that is automated execution evidence, not independent user adoption.
