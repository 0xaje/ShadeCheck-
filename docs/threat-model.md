# SC-002 threat model and milestone gate

Adversary: the service receiving a client's broadcast RPC, able to observe the transport connection and submitted transaction bytes. It may observe matching transaction bytes through its own mempool interface. No global passive adversary, account identity, IP-to-person attribution, Tor analysis, or chain deanonymization is modeled.

MEDIUM is justified by direct connection-to-payload association even when the broadcast is rejected. HIGH requires upstream-reported acceptance and exact byte correlation within the configured 30-second window. Fixture mode cannot generate HIGH. Matching is by submitted serialization, not a naive SHA-256 Zcash txid.

The observer captures the gRPC transport peer and hashes it. A connection is not a stable wallet identity. The observer itself changes routing and timings. A mitigated architecture must demonstrate a reduced link at the modeled observer; relabeling a session or choosing advisory policy is not mitigation.

The first milestone is complete only after a controlled real backend accepts a valid transaction, GetMempoolStream returns matching bytes, the finding embeds those recorded events, and strict CLI execution returns 1. Current local replay establishes protocol transport, recording, evaluation, reporting, and exit behavior only.

No broader implementation should begin before this gate is resolved.
