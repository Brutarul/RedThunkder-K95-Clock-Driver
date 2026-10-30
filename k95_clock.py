#!/usr/bin/python3
"""Synchronize a wired RedThunder K95 display with Linux local time."""

import argparse
import datetime as dt
import errno
import fcntl
import os
from pathlib import Path
import struct
import sys


REPORT_SIZE = 520
# Linux asm-generic ioctl: _IOWR('H', 0x06, 520), HIDIOCSFEATURE.
HIDIOCSFEATURE = (3 << 30) | (REPORT_SIZE << 16) | (ord('H') << 8) | 0x06
HIDIOCGRAWINFO = (2 << 30) | (8 << 16) | (ord('H') << 8) | 0x03
HID_ID = '0003:0000258A:0000019D'
# Exact descriptor of the K95 vendor interface examined on this machine.
# Matching it avoids sending commands to other keyboards sharing this USB ID.
REPORT_DESCRIPTOR = bytes.fromhex(
    '0601000980a10185011981298315002501950375018102950175058101c0'
    '050c0901a101850219002aff02150026ff7f950175108100c0'
    '0602ff0901a1018503150026ff00092f750895038102c0'
    '05010906a1018504050719e029e715002501750195088102050719002967'
    '150025017501956881020985098709880989098a098b09910992750195088102c0'
    '0600ff0901a1018505150026ff00190029ff75089505b102c0'
    '0600ff0901a1018506150026ff00190129027508960704b102c0'
    '0602ff0902a1018509150026ff007508950709028100150026ff0019012902'
    '7508960702b102c0'
    '05010902a10185070901a1000509150025011901290575019505810295038101'
    '050116008026ff7f093009317510950281061581257f0938750895018106'
    '050c0a380295018106c0c0'
)


def clock_report(now):
    """Vendor command 0x0b, 14-byte system-status payload; see PROTOCOL.md."""
    report = bytearray(REPORT_SIZE)
    report[:8] = bytes.fromhex('09 0b 00 00 01 00 0e 00')
    struct.pack_into(
        '<H6B', report, 11,
        now.year, now.month, now.day, now.hour, now.minute, now.second,
        (now.weekday() + 1) % 7,  # Windows SYSTEMTIME: Sunday=0
    )
    return report


def is_k95(device):
    try:
        info = dict(line.split('=', 1) for line in (device / 'uevent').read_text().splitlines())
        interface = device.resolve().parent
        return (
            info.get('HID_ID') == HID_ID
            and info.get('HID_NAME') == 'SINO WEALTH K95'
            and (interface / 'bInterfaceNumber').read_text().strip() == '01'
            and (device / 'report_descriptor').read_bytes() == REPORT_DESCRIPTOR
        )
    except FileNotFoundError:
        return False  # Device unplugged during enumeration.


def find_devices():
    return [Path('/dev') / p.name for p in sorted(Path('/sys/class/hidraw').glob('hidraw*'))
            if is_k95(p / 'device')]


def sync_device(path):
    fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Recheck after open in case a hidraw number was recycled during hotplug.
        info = bytearray(8)
        fcntl.ioctl(fd, HIDIOCGRAWINFO, info)
        if struct.unpack('=IHH', info) != (3, 0x258A, 0x019D):
            raise RuntimeError(f'{path}: device identity changed')
        if not is_k95(Path('/sys/class/hidraw') / path.name / 'device'):
            raise RuntimeError(f'{path}: unsupported device/interface')
        now = dt.datetime.now().astimezone()
        report = clock_report(now)
        sent = fcntl.ioctl(fd, HIDIOCSFEATURE, report)
        if sent != REPORT_SIZE:
            raise RuntimeError(f'{path}: short HID transfer ({sent}/{REPORT_SIZE})')
        print(f'{path}: clock report sent for {now.isoformat(timespec="seconds")}')
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='show device and packet without opening USB')
    parser.add_argument('--allow-missing', action='store_true', help='exit successfully when the keyboard is unplugged')
    args = parser.parse_args()
    try:
        devices = find_devices()
        if not devices:
            if not args.allow_missing:
                print('No supported wired K95 found. Connect its USB cable and select wired mode.', file=sys.stderr)
            return 0 if args.allow_missing else 1
        for path in devices:
            if args.dry_run:
                now = dt.datetime.now().astimezone()
                print(f'{path}: {now.isoformat(timespec="seconds")}; '
                      f'{REPORT_SIZE} bytes; prefix: {clock_report(now)[:22].hex(" ")}')
            else:
                try:
                    sync_device(path)
                except OSError as exc:
                    if args.allow_missing and exc.errno in (errno.ENOENT, errno.ENODEV):
                        continue
                    raise
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f'K95 clock sync failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
