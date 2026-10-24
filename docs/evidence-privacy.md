# Evidence privacy and publication

ShadeCheck is a developer-controlled test observer. It intentionally records correlations that a developer wants to test. Those records are sensitive test data, not anonymous telemetry.

## Fresh recording defaults

- Transport peers are represented by HMAC-SHA-256 pseudonyms keyed with a random per-recorder key. The key is never saved. Equal peers within one recording can be joined; separate recordings do not share a predictable peer hash.
- Compatibility-only RPC messages retain their sizes and per-run keyed fingerprints, not raw addresses, tree messages, keys, or a reusable plain message hash.
- Transaction payloads retain byte lengths and SHA-256 fingerprints for exact matching against node evidence. These remain correlatable when the transaction bytes are known; they are not anonymous identifiers or transaction IDs.
- Rule-required heights, transaction IDs, ordering and timestamps are retained. Those can themselves reveal sensitive behavior.
- Broadcast responses retain the numeric error code and request association. Arbitrary upstream response text is forwarded to the client but omitted from the observer evidence.
- New local event, report, baseline and diagnostic files use mode 0600 on POSIX. Newly created containing directories use 0700. Existing parent directory permissions are not changed. Windows users must use account-restricted NTFS ACLs; POSIX modes do not implement Windows access control or disk encryption.
- Local wallet files and private client diagnostics remain outside public evidence bundles. Do not supply a real user's wallet, seed or viewing key to a demonstration.

These changes do not retroactively anonymize historical artifacts. Historical controlled regtest evidence remains unchanged so its original hashes and provenance can be checked.

## Collection, retention and sharing

Use throwaway regtest wallets under a trusted local account. Disable or restrict third-party CI log shipping. Treat traces, reports and baselines together: findings and baselines embed evidence, so protecting only events.jsonl is insufficient. The optional dashboard serves the selected evidence to processes that can access its loopback endpoint; loopback is not authentication against a malicious local user.

Retention is developer-controlled. ShadeCheck does not silently delete evidence or wallets. Keep private traces only as long as investigation needs them, use your CI provider's artifact-retention settings, and remove unneeded copies deliberately. Back up data needed for reproducibility before cleanup. Deleting a file is not guaranteed secure erasure.

Public export is a separate, explicit operation. It accepts a validated controlled regtest suite and requires `--acknowledge-public-evidence`. Review its inventory, logs and downloaded ZIP before publication. This acknowledgement is consent, not automatic proof that every file is secret-free. Do not export a production or public-testnet user trace. Raw artifact bytes are kept exact; silently redacting a signed/hash-linked report would invalidate its evidence. If publication is inappropriate, keep the whole bundle private.

## Threat boundary

The test driver, local OS, wallet/node and recorder process are trusted. A compromised recorder can forge an entire trace; hash chains detect inconsistent edits, not malicious authorship. A keyed pseudonym does not hide traffic from the observer that sees it live. Mitigation claims must specify the observer and trust boundary.
