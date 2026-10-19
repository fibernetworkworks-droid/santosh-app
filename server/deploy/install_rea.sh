#!/usr/bin/env bash
# App Jaanch: installs REA (github.com/morluto/rea, MIT) pinned to rea-agents 6.7.0, plus the JADX engine it uses for
# APKs (SHA-256 checked). Static analysis only: Santosh blocks REA's runtime / debugger / Frida / adb / browser tools.
# Needs node + npm and a JDK 17+ (sudo apt install -y openjdk-21-jdk-headless).
set -euo pipefail
DIR="${REA_DIR:-$HOME/apps/rea}"
JAR_URL="https://github.com/1013503897/jadx-headless-mcp/releases/download/v0.7.1/jadx-headless-mcp-0.7.1-all.jar"
JAR_SHA="6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75"
mkdir -p "$DIR" && cd "$DIR"
[ -f package.json ] || npm init -y >/dev/null
npm install --ignore-scripts --save-exact rea-agents@6.7.0
curl -fL -o jadx-headless-mcp-0.7.1-all.jar "$JAR_URL"
echo "$JAR_SHA  jadx-headless-mcp-0.7.1-all.jar" | sha256sum -c -
command -v java >/dev/null || { echo "Install a JDK 17+: sudo apt install -y openjdk-21-jdk-headless"; exit 1; }
"$DIR/node_modules/.bin/rea" --version
echo
echo "Add to ~/apps/santosh-core/.env:"
echo "REA_BIN=$DIR/node_modules/.bin/rea"
echo "REA_JADX_JAR=$DIR/jadx-headless-mcp-0.7.1-all.jar"
