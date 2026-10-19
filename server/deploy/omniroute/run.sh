#!/usr/bin/env bash
# OmniRoute (open-source LLM gateway) next to Santosh. Loopback only: nothing is reachable from the internet.
set -euo pipefail
VERSION="${OMNIROUTE_VERSION:-3.8.51}"
docker rm -f omniroute >/dev/null 2>&1 || true
docker run -d --name omniroute --restart unless-stopped --stop-timeout 40 \
  -e REQUIRE_API_KEY=true \
  -e OMNIROUTE_MEMORY_MB=1024 --memory=2g \
  -p 127.0.0.1:20128:20128 \
  -v omniroute-data:/app/data \
  "diegosouzapw/omniroute:${VERSION}"
echo "OmniRoute ${VERSION} starting on 127.0.0.1:20128 (dashboard via SSH tunnel)."
