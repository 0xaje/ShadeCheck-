# Recorded independent Zingo CLI evidence

This is a **recorded real regtest run**, not a new test execution or fixture.
The archive is the original GitHub CI artifact, including the original events,
JSON/HTML report, integration manifest, parsed client statuses, policy and backend
logs. No event has been rewritten or relabelled.

- Source run: https://github.com/0xaje/ShadeCheck-/actions/runs/39599061669
- ShadeCheck revision: `48e11f0b006fa2ad4fe4cefba027e6ea8a235196`.
- Independent client: Zingo CLI from zingolib release `zingolib_v3.0.1`, upstream
  commit `31da83657d88fbb3b57bf45996023850e8aaf9da` (unmodified).
- Both direct and observed clients scanned 101 blocks (heights 10–110).
- 124 captured events; 101 delivered block hashes checked against the node.
- Integration checks: VERIFIED. Privacy: FAIL, strict exit 1, two SC-001 MEDIUM
  findings under the explicitly chosen 20-block aligned policy.
- SC-002, SC-003 and SC-004: uncovered in this unfunded synchronization flow.
  SC-005: not selected. This is not an audit of current Zingo production behavior.
- The upstream binary prints `Zingo CLI 0.1.1`; the release tag above names the
  zingolib source release. The manifest records both without substituting a version.
- One mempool stream cancellation was observed when the client ended its sync;
  the two clients both reported completed block scanning.

The policy mismatch is **not proof of a Zingo security vulnerability**. It does
not establish transaction ownership, wallet identity, anonymity, adoption or
endorsement. The remaining workflow limits are in the [integration guide](../../docs/zingo-integration.md).

## Inspect without building a wallet or starting Docker

From the ShadeCheck repository, with ShadeCheck installed:

```bash
./.venv/bin/python -m zipfile -e examples/zingo/recorded-regtest-20261021.zip out/zingo-recorded
./.venv/bin/python scripts/zingo_integration.py --verify out/zingo-recorded/zingo/20261021T122804-10559827
```

Open `out/zingo-recorded/zingo/20261021T122804-10559827/observed/report.html` in a
browser, or inspect its `report.json`, `events.jsonl`, and `integration.json`.
Offline verification recomputes recorded integrity/results; it does not execute
a new wallet/network test or authenticate the author. See CI provenance above.

To run a **new** test, follow the [source-build instructions](../../docs/zingo-integration.md).

Original archive SHA-256:
`df27331727aebb1230daa8eb198fed565f6ce0c3db81bf58f944c126451ef4f9`.
