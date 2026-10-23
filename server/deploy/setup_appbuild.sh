#!/usr/bin/env bash
# v0.132 Hoola App Builder: a SEPARATE build machine for native Android apps (NOT the Hoola VPS: a Gradle build needs ~3 GB
# RAM and a few minutes of CPU). Ubuntu 24.04, 4 GB RAM / 2 vCPU or more. Run as root on that machine:
#   HOOLA_BUILD_SECRET=<same as APP_BUILD_SECRET on the Hoola server> bash setup_appbuild.sh
# Then on the Hoola VPS .env:  APP_BUILD_MODE=worker  APP_BUILD_URL=https://<this machine's https name>  APP_BUILD_SECRET=<same>
set -euo pipefail
: "${HOOLA_BUILD_SECRET:?set HOOLA_BUILD_SECRET (24+ characters)}"
apt-get update -y
apt-get install -y openjdk-17-jdk-headless unzip curl python3 nginx
id hoolabuild >/dev/null 2>&1 || useradd -m -s /bin/bash hoolabuild
SDK=/opt/android-sdk
mkdir -p $SDK/cmdline-tools
if [ ! -x $SDK/cmdline-tools/latest/bin/sdkmanager ]; then
  # Google's command-line tools (official zip); check the current link on developer.android.com/studio#command-line-tools-only
  curl -fsSL -o /tmp/clt.zip "https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip"
  unzip -q /tmp/clt.zip -d $SDK/cmdline-tools && mv $SDK/cmdline-tools/cmdline-tools $SDK/cmdline-tools/latest
fi
yes | $SDK/cmdline-tools/latest/bin/sdkmanager --licenses >/dev/null || true
$SDK/cmdline-tools/latest/bin/sdkmanager --install "platform-tools" "build-tools;36.0.0" "platforms;android-37" >/dev/null
chown -R hoolabuild:hoolabuild $SDK
install -d -o hoolabuild -g hoolabuild /srv/hoola-build /opt/hoola-builder
install -o hoolabuild -g hoolabuild -m 0644 "$(dirname "$0")/../app_builder/worker.py" /opt/hoola-builder/worker.py
cat > /etc/systemd/system/hoola-builder.service <<UNIT
[Unit]
Description=Hoola App Builder (native Android builds)
After=network-online.target
[Service]
User=hoolabuild
Environment=HOOLA_BUILD_SECRET=${HOOLA_BUILD_SECRET}
Environment=HOOLA_BUILD_HOME=/srv/hoola-build
Environment=ANDROID_HOME=${SDK}
Environment=ANDROID_SDK_ROOT=${SDK}
Environment=JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ExecStart=/usr/bin/python3 /opt/hoola-builder/worker.py --host 127.0.0.1 --port 8090
Restart=always
MemoryMax=6G
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
[Install]
WantedBy=multi-user.target
UNIT
chmod 600 /etc/systemd/system/hoola-builder.service
systemctl daemon-reload && systemctl enable --now hoola-builder
cat > /etc/nginx/sites-available/hoola-builder <<'NGX'
server {
    listen 80;
    server_name _;
    client_max_body_size 80m;
    location / { proxy_pass http://127.0.0.1:8090; proxy_read_timeout 600s; }
}
NGX
ln -sf /etc/nginx/sites-available/hoola-builder /etc/nginx/sites-enabled/hoola-builder
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo "Builder running. Put TLS in front (e.g. certbot --nginx -d build.example.com), then set APP_BUILD_* on the Hoola server."
