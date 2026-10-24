# Current-release independent wallet on Zebra and Zaino

This is a separate real-execution gate for a funded independent Zingo wallet. Its status is determined by the workflow and artifact verifier, not by this document or a successful build. Do not describe the gate as verified unless its run completes and produces a validated `integration_status: VERIFIED` manifest.

## Pinned components

- Zebra 7.0.0, image digest `sha256:a70d2be8ffef3a4b6e37355724e36a0e6c1838e46baa28bfb216739f00cf2d34`.
- Zaino 0.10.1-no-tls, image digest `sha256:c8428a39d510fd59a9182a5e19cf473d6af6a4b6a672aff8b1a690e9c23c17b9`.
- Zingolib release `zingolib_v7.0.0`, source commit `bfb0a2156819ea7f75a9b09b1724abfd06c8925e`; Rust 1.99.0.
- Unmodified upstream source, built with `--no-default-features --features nakednet-test-mode`. This is upstream's explicit local transport testing feature. It bypasses default mixnet transport for a controlled experiment and is never a claim about production Zingo network behavior.

The activation schedule matches the client's regtest defaults through NU6.3 at height 1, with NU7 not activated. The fact Zebra supports NU7 does not mean this scenario exercises it.

## Required runtime evidence

1. Create throwaway sender/recipient wallets locally; never request or publish seeds/keys.
2. Mine actual local coinbase funds to the sender's transparent address and wait for indexer readiness.
3. Require complete, nonempty direct and observed client synchronization over the same initial block span.
4. Let the independent wallet shield the mature local funds and broadcast through ShadeCheck. Require actual Zebra mempool acceptance, identical mempool bytes observed through the proxy, and block inclusion.
5. Let the wallet send 100000 zatoshis to a shielded recipient through the observer. Require accepted node-decoded transaction structure with zero transparent inputs and outputs, matching mempool evidence, and block inclusion.
6. Require the recipient wallet to scan and report exactly 100000 shielded zatoshis, without transparent receipt.
7. Check every recorded compact-block hash against the canonical Zebra chain, recompute SC-002 findings, and require an actual strict CLI exit of 1 supported by HIGH evidence for each transmission.
8. Save an inventory and recompute the resulting bundle. Other families are not implicitly covered by this workflow.

## Reproduce

Requirements: Docker Linux engine with Compose v2, Python 3.11+, Rust 1.99.0, C/C++ build tools, OpenSSL development libraries, pkg-config and protobuf compiler. Use a trusted developer machine. Do not run two copies concurrently.

```bash
python -m shadecheck.cli doctor
# Clone once; do not reuse a modified client checkout.
git clone https://github.com/zingolabs/zingolib.git ../shadecheck-modern-zingo
git -C ../shadecheck-modern-zingo checkout --detach bfb0a2156819ea7f75a9b09b1724abfd06c8925e
cd ../shadecheck-modern-zingo
rustup toolchain install 1.99.0 --profile minimal
cargo +1.99.0 build --locked --release -p zingo-cli --no-default-features --features nakednet-test-mode
cd ../ShadeCheck-
python scripts/modern_wallet.py --source ../shadecheck-modern-zingo
```

The driver uses a distinct Compose project, `shadecheck-modern-regtest`, volumes and localhost ports 29032 (node RPC) and 29067 (indexer). It does not modify the existing regression backend. It may append blocks to its dedicated modern chain on repeat runs. Wallets and private client failure logs stay in `.shadecheck/modern-wallets`, outside `out/modern` artifacts. Local test node RPC is unencrypted and unauthenticated on loopback; this is not a production deployment configuration.

The driver sets the miner address only for the child Compose processes. To stop this stack while preserving its local volumes, a placeholder valid regtest address is sufficient for Compose substitution:

```bash
SHADECHECK_MODERN_MINER=tmSRd1r8gs77Ja67Fw1JcdoXytxsyrLTPJm docker compose -f integration/modern/compose.yml down
```

On Windows PowerShell set `$env:SHADECHECK_MODERN_MINER` before the Compose command. Never run `down -v` on a chain whose data you intend to retain.

Offline inspection uses `python scripts/modern_wallet.py --verify out/modern/RUN`. It validates the inventory and recomputes recorded evidence/results. It does not independently rerun the historical wallet process, revalidate consensus, or authenticate an author. Source CI and exact pins provide the execution context.

This current-client gate complements the five-family legacy regression suite and historical Zingo sync experiment. It does not turn their separate evidence into one client trace or claim every backend/wallet combination is supported.
