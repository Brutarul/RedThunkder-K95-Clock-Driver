#!/usr/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ $EUID -ne 0 ]]; then
    echo 'Run: sudo bash install.sh' >&2
    exit 1
fi
install -D -o root -g root -m 0644 k95_clock.py /usr/local/libexec/redthunder-k95-clock.py
install -o root -g root -m 0644 redthunder-k95-clock.service redthunder-k95-clock.timer /etc/systemd/system/
install -o root -g root -m 0644 90-redthunder-k95-clock.rules /etc/udev/rules.d/
restorecon /usr/local/libexec/redthunder-k95-clock.py /etc/systemd/system/redthunder-k95-clock.{service,timer} /etc/udev/rules.d/90-redthunder-k95-clock.rules
systemd-analyze verify /etc/systemd/system/redthunder-k95-clock.service /etc/systemd/system/redthunder-k95-clock.timer
udevadm verify /etc/udev/rules.d/90-redthunder-k95-clock.rules
systemctl daemon-reload
udevadm control --reload-rules
systemctl enable --now redthunder-k95-clock.timer
systemctl start redthunder-k95-clock.service
echo 'Installed. Clock synchronization is enabled at boot, on USB connection, and every minute.'
