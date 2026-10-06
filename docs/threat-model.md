# SC-002 threat model and milestone gate

Adversary: the service receiving a client's broadcast RPC, able to observe the transport connection and submitted transaction bytes. It may observe matching transaction bytes through its own mempool interface. No global passive adversary, account identity, IP-to-person attribution, Tor analysis, or chain deanonymization is modeled.

MEDIUM is justified by direct connection-to-payload association even when the broadcast is rejected. HIGH requires upstream-reported acceptance and exact byte correlation within the configured 30-second window. Fixture mode cannot generate HIGH. Matching is by submitted serialization, not a naive SHA-256 Zcash txid.

The observer captures the gRPC transport peer and hashes it. A connection is not a stable wallet identity. The observer itself changes routing and timings. A mitigated architecture must demonstrate a reduced link at the modeled observer; relabeling a session or choosing advisory policy is not mitigation.

The first transport milestone requires a controlled real backend to accept a valid transaction, GetMempoolStream to return matching bytes, the finding to embed those recorded events, and strict CLI execution to return 1. The real regtest CI run on October 6, 2026 satisfied these conditions with a genuinely signed transparent transaction and independent node confirmation. This is not yet a shielded-wallet integration or mitigation proof. Fixture replay remains only an internal protocol test.

The completed transport proof is evidence for the narrow SC-002 rule. Broader privacy claims require the remaining tests and wallet integrations.
