#!/usr/bin/env bash
# v0.49 Live off-VPS backup of Hoola's SQLite database with Litestream (Apache-2.0, github.com/benbjohnson/litestream).
# Every change is streamed to S3-compatible storage (AWS S3, Cloudflare R2, Backblaze B2, DigitalOcean Spaces, MinIO...).
#
#   export LITESTREAM_BUCKET=hoola-backup LITESTREAM_ENDPOINT=https://<account>.r2.cloudflarestorage.com \
#          LITESTREAM_ACCESS_KEY_ID=... LITESTREAM_SECRET_ACCESS_KEY=...
#   bash ~/santosh_app/server/deploy/setup_backup.sh
#
# Keys go only into ~/apps/santosh-core/.litestream.env (chmod 600), never into the repo or chat.
set -euo pipefail
CORE=${CORE:-$HOME/apps/santosh-core}
DB=${DB:-$CORE/santosh.db}
VER=${LITESTREAM_VERSION:-0.3.13}
: "${LITESTREAM_BUCKET:?set LITESTREAM_BUCKET}"; : "${LITESTREAM_ACCESS_KEY_ID:?}"; : "${LITESTREAM_SECRET_ACCESS_KEY:?}"
if ! command -v litestream >/dev/null; then
  arch=$(dpkg --print-architecture)
  curl -fsSL -o /tmp/litestream.deb "https://github.com/benbjohnson/litestream/releases/download/v${VER}/litestream-v${VER}-linux-${arch}.deb"
  sudo dpkg -i /tmp/litestream.deb
fi
umask 077
cat > "$CORE/.litestream.env" <<ENV
LITESTREAM_ACCESS_KEY_ID=${LITESTREAM_ACCESS_KEY_ID}
LITESTREAM_SECRET_ACCESS_KEY=${LITESTREAM_SECRET_ACCESS_KEY}
ENV
cat > "$CORE/litestream.yml" <<YML
dbs:
  - path: ${DB}
    replicas:
      - type: s3
        bucket: ${LITESTREAM_BUCKET}
        path: hoola/santosh.db
        ${LITESTREAM_ENDPOINT:+endpoint: ${LITESTREAM_ENDPOINT}}
        retention: 168h
        sync-interval: 10s
YML
set -a; . "$CORE/.litestream.env"; set +a
pm2 delete hoola-backup >/dev/null 2>&1 || true
pm2 start "$(command -v litestream)" --name hoola-backup -- replicate -config "$CORE/litestream.yml"
pm2 save
echo "Backup running. Check:   litestream snapshots -config $CORE/litestream.yml $DB"
echo "Restore drill (to a copy): litestream restore -config $CORE/litestream.yml -o /tmp/restore-test.db $DB"
