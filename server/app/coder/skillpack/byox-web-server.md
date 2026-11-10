---
name: byox-web-server
description: Build an HTTP/1.1 server: sockets, routing, keep-alive, TLS
when_to_use: web server from scratch, http server, own nginx
---
GOAL: a server that passes an HTTP conformance test and handles 10k concurrent connections.

PHASES
1. TCP echo server: bind, listen, accept, read line, write back, close.
2. HTTP parser: method (GET/POST), path, headers, body by Content-Length.
3. Static file server: serve files from a directory; correct Content-Type.
4. Router: match routes by method + path; return JSON; 404 for unknowns.
5. Event loop (epoll on Linux): 10k concurrent connections; keep-alive support.

CORE CONCEPTS
- HTTP/1.1: `\r\n` line endings; header ends at blank line; persistent by default.
- epoll: edge-triggered (EPOLLET) + non-blocking fds for the highest throughput.
- TLS: use OpenSSL SSL_CTX; wrap the accepted fd with SSL_new + SSL_set_fd.

LANGUAGE: C (sockets), Go (net/http internals), Rust (tokio mio), Node.js (net).

VERIFY: `curl -v http://localhost:8080/` returns 200; wrk -c 10000 shows zero errors.
