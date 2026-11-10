---
name: byox-bittorrent
description: Build a BitTorrent client: tracker, peers, pieces, verify
when_to_use: bittorrent client, torrent client, peer to peer download
---
GOAL: download a real .torrent file, verify every piece against SHA-1, write output.

PHASES
1. Bencode decoder: nested dicts, lists, ints, byte strings.
2. HTTP tracker announce: info_hash, peer_id, port; parse compact peer list.
3. TCP peer handshake (19 + "BitTorrent protocol" + info_hash + peer_id).
4. Bitfield, interested/unchoke, request piece (index, begin, length=16384).
5. SHA-1 verify each piece on receipt; write to file; seed back to peers.

CORE CONCEPTS
- info_hash = SHA-1 of bencoded info dict; 20 bytes sent as raw bytes not hex.
- Piece = many 16 KB blocks; request each block separately; assemble to verify.
- Choke/unchoke: upload to 4 fastest + 1 random unchoked peer every 10 s.

VERIFY: download ubuntu.torrent; file SHA-1 matches the torrent's piece hashes.
