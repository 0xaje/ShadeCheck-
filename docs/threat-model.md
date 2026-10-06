# SC-002 threat model and milestone gate

Adversary: the service receiving a client's broadcast RPC, able to observe the transport connection and submitted transaction bytes. It may observe matching transaction bytes through its own mempool interface. No global passive adversary, account identity, IP-to-person attribution, Tor analysis, or chain deanonymization is modeled.

MEDIUM is justified by direct connection-to-payload association even when the broadcast is rejected. HIGH requires upstream-reported acceptance and exact byte correlation within the configured 30-second window. Fixture mode cannot generate HIGH. Matching is by submitted serialization, not a naive SHA-256 Zcash txid.

The observer captures the gRPC transport peer and hashes it. A connection is not a stable wallet identity. The observer itself changes routing and timings. A mitigated architecture must demonstrate a reduced link at the modeled observer; relabeling a session or choosing advisory policy is not mitigation.

The first transport milestone requires a controlled real backend to accept a valid transaction, GetMempoolStream to return matching bytes, the finding to embed those recorded events, and strict CLI execution to return 1. The real regtest CI run on October 6, 2026 satisfied these conditions with a genuinely signed transparent transaction and independent node confirmation. The subsequent [real shielded integration run](https://github.com/0xaje/ShadeCheck-/actions/runs/37401106271) verified two successive Sapling-to-Sapling transactions, each with one Sapling spend, two Sapling outputs, and zero transparent inputs or outputs. The wallet constructs and accepts each transaction on an isolated local node; its first submission to the separate verifier passes through ShadeCheck. This is not a mitigation proof. Fixture replay remains only an internal protocol test.

The completed transport proof is evidence for the narrow SC-002 rule. Broader privacy claims require the remaining tests and wallet integrations.

## SC-003 observer boundary

SC-003 observes delivered compact blocks and subsequent ID-specific requests on a recorded connection. It cannot observe wallet processing or establish transaction ownership. Its deterministic subset condition, finite-trace limitations, explicit coverage requirements, and verified real backend comparison are documented in [SC-003](sc003.md). Broader fetching changed this tested result; this is not an anonymity or production mitigation claim.

## SC-001 declared-policy boundary

SC-001 compares observed block-range boundaries and request sizes with an explicit developer-selected alignment and chunk policy. It does not infer a wallet birthday, local balance, transaction history, or person. Complete upstream delivery is required for PASS coverage. Historical completed-chunk conformance is verified; chain-tip truncation, timing fingerprints, reorg policy, and repeated-history analysis are outside this implementation. See [SC-001](sc001.md).
