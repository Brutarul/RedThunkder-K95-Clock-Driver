#!/usr/bin/bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
    echo 'Run: sudo bash uninstall.sh' >&2
    exit 1
fi
systemctl disable --now redthunder-k95-clock.timer
systemctl stop redthunder-k95-clock.service
rm -f /etc/udev/rules.d/90-redthunder-k95-clock.rules
rm -f /etc/systemd/system/redthunder-k95-clock.service /etc/systemd/system/redthunder-k95-clock.timer
rm -f /usr/local/libexec/redthunder-k95-clock.py
systemctl daemon-reload
udevadm control --reload-rules
echo 'Removed RedThunder K95 clock synchronization.'
