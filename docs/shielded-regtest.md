# Actual Sapling-to-Sapling SC-002 integration

The shielded path uses genuine Sapling proofs and signatures produced by the pinned zcashd wallet. It requires actual Sapling spends and outputs, zero transparent inputs, zero transparent outputs, and no Sprout JoinSplits, as decoded by the verification node itself.

## Why two local nodes?

The pinned zcashd z_sendmany RPC creates a signed/proved transaction and accepts it into the wallet node's local mempool. It does not expose an ordinary sign-only parameter. ShadeCheck therefore uses:

- zcashd: canonical chain and lightwalletd verification backend.
- wallet: separate developer-owned local wallet node, no P2P peers or published ports.

Actual canonical blocks are copied via getblock and submitblock so both nodes have the exact same chain and note anchors. The wallet node constructs the final shielded transaction and accepts it locally. That fact is disclosed; it is not described as globally unbroadcast.

The final transaction must be absent from the verification node's mempool before the observer submits it. The measured first submission to that verification backend goes through ShadeCheck and real lightwalletd. No testmode, generated stand-in proofs, or fake acceptance is used.

Funding payments are setup-only and are distinguished from the measured shielded transaction. Setup mines two new canonical blocks, possibly confirming earlier local mempool transactions. All activity remains on your dedicated regtest chain.

## Windows commands

With Docker Desktop running, from the existing repository:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe scripts/regtest.py up
.\.venv\Scripts\python.exe scripts/regtest.py prepare-shielded
.\.venv\Scripts\python.exe scripts/regtest.py prove
```

The first shielded preparation starts the second node, funds its wallet, imports blocks, generates actual Sapling notes, confirms funding, and constructs a Sapling-to-Sapling transaction under the FullPrivacy wallet policy. Allow it to finish. Do not mine blocks between prepare-shielded and prove.

Preparation prints the actual decoded structure and transaction ID. Successful proof prints HIGH, strict CLI exit 1, and Kind: sapling-shielded. The orchestration exits 0 because it verified that expected privacy-policy failure.

The backend-proof.json includes decoded_structure derived from the actual transaction, actual node mempool confirmation, matching serialization, node version, and lightwalletd revision.

For another shielded run, repeat prepare-shielded and prove. Stop all three services with:

```powershell
.\.venv\Scripts\python.exe scripts/regtest.py stop
```

All test spending keys stay in local node wallet volumes; ShadeCheck does not export or hold them. This validates a narrow broadcast-observer relationship even when the transaction itself is shielded; it does not establish anonymity or mitigation.

## Primary source

https://github.com/zcash/zcash/blob/v6.12.2/src/wallet/rpcwallet.cpp documents FullPrivacy and the asynchronous z_sendmany result. The actual signing/proving path is in https://github.com/zcash/zcash/blob/v6.12.2/src/wallet/asyncrpcoperation_sendmany.cpp.
