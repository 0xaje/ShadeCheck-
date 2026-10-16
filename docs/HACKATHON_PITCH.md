# ShadeCheck — ZK / Zcash Hackathon Submission & Pitch Guide

## 1. The Executive Pitch (30-Second Elevator Pitch)

> **"Zcash shields transactions with zero-knowledge proofs on-chain. But when mobile light wallets connect to lightwalletd servers over the network, what metadata are they leaking over the wire?**
>
> Today, the answer is: *nobody knows until someone sniffs the traffic.*
>
> **ShadeCheck is the first automated Privacy CI/CD framework for Zcash.** It intercepts gRPC client interactions, generates tamper-evident cryptographic hash chains of observable RPC behavior, evaluates traffic against 5 defined privacy rule families, and blocks vulnerable code in GitHub Actions before it ever hits production."

---

## 2. The Core Problem We Solve

In Zcash, cryptographic anonymity at the consensus layer (Sapling/Orchard ZK-SNARKs) is state-of-the-art. However, **network-layer and RPC side-channels completely deanonymize light-client users**:

1. **Unaligned Sync Queries (SC-001):** When a wallet asks lightwalletd for narrow block ranges (e.g. 5 blocks), an ISP or node operator immediately deduces the wallet's birthday and active transaction windows.
2. **Broadcast Connection Linkability (SC-002):** A wallet broadcasting a shielded transaction over an identifiable TCP/TLS connection allows the server to correlate the submitter's IP/session to the transaction bytes appearing in the mempool stream within seconds.
3. **Selective Transaction Fetching (SC-003):** If a wallet downloads a compact block and then fetches only *one* transaction ID instead of all transactions in the block, it explicitly signals: *"This transaction belongs to me."*
4. **Silent Transparent Fallbacks (SC-004):** When wallets lack strict enforcement, a user thinking they sent a private payment may inadvertently broadcast transparent inputs/outputs.
5. **Silent Privacy Regressions (SC-005):** A routine SDK refactor or mobile update can accidentally re-introduce a privacy leak without triggering any functional unit test failures.

**Before ShadeCheck:** Testing for these leaks required manual Wireshark packet captures, custom scripts, and subjective guesswork.
**With ShadeCheck:** A single GitHub Action blocks PRs that leak metadata.

---

## 3. The 4 Hackathon Winning Pillars

### Pillar 1: Reusable GitHub Action (`action.yml`)
Any Zcash wallet repo (Zashi, Ywallet, Zingo, Nighthawk) can add ShadeCheck in 5 lines:
```yaml
- name: Run ShadeCheck Privacy CI
  uses: 0xaje/ShadeCheck-@main
  with:
    rules: 'SC-001 SC-002 SC-003 SC-004'
    policy: 'strict'
```
When a PR is opened, ShadeCheck renders a rich **GitHub Step Summary** and blocks merges (`exit 1`) if privacy regressions are detected.

### Pillar 2: Cryptographic Tamper-Evident Evidence Chains
- Every observed gRPC event (methods, phases, timestamps, peer sessions) is recorded in an immutable, canonical JSONL hash chain (`previous_hash` -> `event_hash`).
- Tampered evidence is rejected automatically by the validator.
- Fixtures and synthetic traces cannot fabricate a fake "PASS".

### Pillar 3: Interactive "Leak vs. Shielded" Demo (`shadecheck demo`)
Judges can verify the entire pipeline in 60 seconds with one command:
```bash
shadecheck demo
```
- **Scenario A (Vulnerable):** Demonstrates unaligned block scans and broadcast linkability -> Fails strict policy -> `Exit 1: PR Blocked`.
- **Scenario B (Mitigated):** Demonstrates 20-block uniform chunk scans and FullPrivacy Sapling-to-Sapling execution -> `Exit 0: PR Approved`.

### Pillar 4: Zero-Dependency Local Evidence Dashboard
```bash
shadecheck dashboard
```
- Serves an immutable, audited snapshot on `http://127.0.0.1:9070`.
- Includes an interactive **Wire Leak Inspector** comparing adversary observations against ShadeCheck enforcement.
- Built strictly with standard Python libraries and lightweight HTML/CSS/JS (no Node runtime or CDN dependencies).

---

## 4. Competitive Landscape & Edge

| Dimension | Standard Zcash Lightwalletd Tests | Traditional Linters / SAST | ShadeCheck Privacy CI |
| :--- | :--- | :--- | :--- |
| **Focus** | Functional correctness (does it crash?) | Code syntax & static code patterns | **Observable behavioral privacy & side-channels** |
| **Verification** | Mocked responses or raw RPC calls | AST pattern matching | **Real gRPC wire proxy + Docker Zebra/zcashd regtest** |
| **Evidence** | Transient console output | Lint error lists | **Tamper-evident SHA-256 cryptographic hash chains** |
| **CI Integration**| Bespoke unit tests | GitHub Action | **Turnkey Composite GitHub Action with Step Summary** |
| **Honesty** | Assumes privacy from protocol | N/A | **Explicit threat boundary ("PASS != Anonymity")** |

---

## 5. 2-Minute Live Pitch / Demo Script (For Video or Panel)

1. **[0:00 - 0:30] Hook & Problem:**
   *"Judges, imagine downloading a Zcash shielded wallet. You trust zero-knowledge proofs to keep your balances secret. But the moment your wallet connects to a lightwalletd node, your IP address is logged, your sync range reveals when you opened the app, and your transaction broadcast is linked directly to your connection. ZK protects the chain, but your network metadata is exposed."*

2. **[0:30 - 1:00] Solution & Architecture:**
   *"We built ShadeCheck: the first automated Privacy CI framework for Zcash. ShadeCheck acts as an active gRPC observer in front of lightwalletd. It records every wire interaction into a tamper-evident cryptographic hash chain, evaluates 5 distinct privacy rule families, and integrates directly into GitHub Actions."*

3. **[1:00 - 1:35] Live Demonstration (`shadecheck demo`):**
   *(Run `shadecheck demo` on screen)*
   *"Notice what just happened: Scenario 1 simulated an unaligned block fetch and broadcast linkability. ShadeCheck immediately flagged the violation under strict policy and exited with code 1, blocking the PR. Then, Scenario 2 applied uniform 20-block chunking and FullPrivacy enforcement: ShadeCheck verified zero leaks and returned exit 0, approving the merge."*

4. **[1:35 - 2:00] Real Backend & Call to Action:**
   *"This isn't a mock: ShadeCheck includes real regtest integration with Zebra and zcashd, proving actual Sapling-to-Sapling transactions. With our ready-to-use GitHub Action, any Zcash wallet developer can protect their users' privacy in CI with just 5 lines of code. Thank you."*

---

## 6. Anticipated Judge Questions & Bulletproof Answers

- **Q: Does passing ShadeCheck prove that an app is completely anonymous?**
  *A:* "Absolutely not, and our documentation explicitly emphasizes this: *'Passing a defined test does not establish anonymity.'* ShadeCheck verifies defined observable behaviors against documented test policies. We avoid snake-oil claims and focus on provable, evidence-backed regression prevention."

- **Q: How hard is it for an existing Zcash mobile wallet to adopt ShadeCheck?**
  *A:* "It takes 5 minutes. They can drop our pre-built `action.yml` into `.github/workflows/`, point their integration test runner to the ShadeCheck observer port, and CI will automatically audit their gRPC traffic and render Step Summaries."

- **Q: Can a developer forge evidence to pass CI?**
  *A:* "No. Every event is linked via a SHA-256 hash chain with strict monotonic timestamps and canonical JSON serialization. Modifying a single byte invalidates the chain root, which our validator rejects before any report is accepted."
