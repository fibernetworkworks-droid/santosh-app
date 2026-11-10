---
name: byox-network-stack
description: Build a TCP/IP stack: Ethernet, ARP, IP, ICMP, TCP
when_to_use: tcp/ip stack, network stack, tcp from scratch, packets
---
GOAL: a userspace TCP stack that can serve an HTTP response to curl.

PHASES
1. Open TUN/TAP device; parse Ethernet II frame (dst/src MAC + ethertype).
2. ARP: respond to who-has requests for a virtual IP (e.g. 10.0.0.2).
3. IPv4: parse header + checksum; forward ICMP echo → ping replies work.
4. TCP state machine: SYN, SYN-ACK, ACK (3-way); data transfer; FIN.
5. HTTP: accept a curl request; send 200 OK with a body; teardown cleanly.

CORE CONCEPTS
- TUN device: kernel delivers raw IP packets; TAP delivers raw Ethernet frames.
- TCP sliding window: SND.UNA + SND.WND; retransmit on timeout; fast retransmit.
- IP checksum: one's complement sum of 16-bit words, then one's complement of result.

LANGUAGE: C or Rust; Linux only for TUN/TAP.

VERIFY: `curl http://10.0.0.2/` via TUN receives a valid HTTP 200 response.
