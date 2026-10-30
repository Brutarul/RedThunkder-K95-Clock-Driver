# RedThunder K95 clock synchronization for Fedora

A native Python 3 helper sends Fedora's **local time and date** to the K95 over
Linux hidraw. A systemd timer runs at boot and every minute; a udev rule also
requests synchronization on USB connection. After suspend, a missed calendar
timer runs on resume. An unplugged keyboard is a normal, quiet no-op.

Verified on Fedora 44 with the wired **SINO WEALTH K95, USB 258a:019d** on
2026-10-30. I confirmed the displayed clock updated correctly. The
helper matches its exact vendor-interface descriptor, not a fixed hidraw number.

## Connection

Connect the keyboard's USB cable and select **wired mode** for synchronization.
This implementation supports that tested connection. Bluetooth and the
258a:0150 wireless receiver are not implemented. A cable used only for charging
while the keyboard remains in wireless mode may not expose the required interface.

The helper uses the system timezone (`/etc/localtime`), including DST. It copies
the computer's time; Fedora's normal time synchronization keeps that time accurate.

## Install / reinstall

```sh
cd ~/Workspace/redthunder-k95-clock
python3 -m unittest -v
sudo bash install.sh
```

Runtime dependency: Fedora's Python 3 standard library, systemd and udev.
No Windows software runs as part of synchronization.

## Status and manual synchronization

```sh
systemctl list-timers redthunder-k95-clock.timer
journalctl -u redthunder-k95-clock.service -n 20 --no-pager
sudo systemctl start redthunder-k95-clock.service
python3 k95_clock.py --dry-run
```

The oneshot service normally shows **inactive (dead)** between runs; the timer
should show **active (waiting)**. A successful USB transfer is logged as
`clock report sent`. There is no implemented clock readback; this log confirms
transfer, while the display provides end-to-end confirmation.

If the clock stops updating, check wired mode and run `--dry-run`. If no device
matches, a firmware revision may expose a different descriptor; examine it before
extending the match. Permission/USB errors are recorded in the journal and retried
at the next minute. No broad device permissions or custom kernel module are needed.

## Remove

```sh
cd ~/Workspace/redthunder-k95-clock
sudo bash uninstall.sh
```

Source and protocol notes remain in this directory. During development,
`innoextract` was installed to examine the vendor installer; it is not a runtime
dependency. Temporary research files are in `/tmp/opencode/k95-research`.
