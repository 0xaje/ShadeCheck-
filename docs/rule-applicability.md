# Choosing useful privacy requirements

A finding is an observed condition under a declared test, not automatically a newly discovered vulnerability. ShadeCheck does not assign a universal anonymity score. Severity describes the implemented observation strength and potential disclosure, not an independently calibrated probability of harm.

Before enabling a strict gate, name the observer, the behavior your architecture promises to prevent, the workflow that exercises it, the required coverage, and a developer action if it fails. A fail should represent a requirement the team actually intends to enforce.

| Family | Appropriate requirement / observer | Legitimate exceptions and limits | Investigation or change |
| --- | --- | --- | --- |
| SC-001 | A visible sync observer must see a declared fixed-size/aligned request policy for the selected historical range | Tip truncation, resuming and reorg handling can violate a simplistic policy legitimately. This is not inferred wallet history or a default claim that every narrow request is a vulnerability. | Test comparable completed ranges; choose an explicit policy consistent with the client; assess padding cost and remaining metadata. |
| SC-002 | The observer in this role must not see both a client-associated submission and its transaction payload | A direct broadcast server inherently sees submitted bytes. That can be acceptable in a declared trust model. HIGH adds accepted submission and exact mempool re-observation; it does not identify a person. | Inspect server trust and role separation. Merely hiding a label, hashing an ID, changing severity or selecting advisory policy is not a privacy mitigation. A separated read observer lacking broadcast coverage must not be called a privacy PASS. |
| SC-003 | A block-serving observer must not see selective ID retrieval within the tested window | Maintenance or other legitimate retrieval can meet the subset condition. The recorded window cannot prove internal wallet relevance. | Reproduce in a real relevant workflow; evaluate broader retrieval/batching and bandwidth cost. |
| SC-004 | A specifically shielded payment flow must not select or execute a transparent path | Transparent payments are valid when explicitly intended. The current rule uses trusted adapter receipts, not automatic inference of Unified Address fallback. | Enforce wallet privacy requirements and inspect accepted transaction structure. |
| SC-005 | Comparable current behavior must not introduce new failures, categories or severity above the recorded baseline | A different scenario, stronger observation or changed backend may alter results without a code regression. | Preserve compatible context and investigate the evidence; a baseline cannot exempt an existing strict failure. |

## Minimal developer workflow

1. Start with one actual integration workflow and one relevant rule. Run the existing controlled acceptance suite first to verify the installation.
2. Capture fresh events through the observer. Keep the same backend, driver configuration and rule policy when comparing changes.
3. Inspect JSON/HTML evidence and confirm the finding describes the intended observer. Do not publish private traces by default.
4. Save a complete-coverage baseline; run the changed workflow; evaluate the actual current trace and baseline in CI.
5. Fail the required CI check for the requirements the team has explicitly selected. Diagnose missing coverage separately from successful covered tests.

The native-wallet acceptance cases, historical Zingo sync integration and current-release funded integration are separate execution gates. Their coverage must not be merged into a fictional single wallet trace. See the independent integration documents for their verified status and exact source versions.
