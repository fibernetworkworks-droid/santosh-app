---
name: byox-blockchain
description: Build a blockchain with PoW, ECDSA wallets and P2P sync
---
GOAL: a local chain where multiple nodes stay in sync and transactions are signed.

PHASES
1. Block struct: index, timestamp, data, previous_hash, hash; genesis block.
2. PoW: mine until SHA-256(block) starts with N zeros; adjustable difficulty.
3. UTXO transaction pool; Merkle root; coinbase reward for the miner.
4. ECDSA wallets: generate secp256k1 key pair; sign + verify transactions.
5. P2P networking (WebSockets / TCP): broadcast new blocks; resolve forks (longest chain).

CORE CONCEPTS
- Merkle root: hash pairs up the tree; a single changed tx changes the root.
- UTXO: each coin is an unspent output; double-spend = same UTXO in two txns.

VERIFY: two nodes accept a mined block; a tampered block is rejected by the peer.
