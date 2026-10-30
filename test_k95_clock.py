import datetime as dt
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import k95_clock as clock


class ClockTests(unittest.TestCase):
    def test_matches_emulated_vendor_report(self):
        # Independent oracle: OemDrv.exe's actual x86 packet-builder output.
        prefix = bytes.fromhex('09 0b 00 00 01 00 0e 00 00 00 00 ea 07 0a 1e 0e 25 34 05')
        expected = prefix + bytes(520 - len(prefix))
        self.assertEqual(clock.clock_report(dt.datetime(2026, 10, 30, 14, 37, 52)), expected)

    def test_sunday_and_leap_day(self):
        sunday = clock.clock_report(dt.datetime(2026, 11, 1, 0, 0, 0))
        self.assertEqual(sunday[13:19], bytes([11, 1, 0, 0, 0, 0]))
        leap = clock.clock_report(dt.datetime(2028, 2, 29, 23, 59, 59))
        self.assertEqual(leap[11:19], bytes.fromhex('ec 07 02 1d 17 3b 3b 02'))

    @patch.object(clock.os, 'close')
    @patch.object(clock.os, 'open', return_value=42)
    @patch.object(clock.fcntl, 'flock')
    def test_recycled_device_is_never_written(self, flock, open_fd, close_fd):
        def ioctl(fd, command, buffer):
            self.assertEqual(command, clock.HIDIOCGRAWINFO)
            buffer[:] = struct.pack('=IHH', 3, 0x258A, 0x0150)
        with patch.object(clock.fcntl, 'ioctl', side_effect=ioctl) as call:
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                clock.sync_device(Path('/dev/hidraw9'))
            self.assertEqual(call.call_count, 1)
        close_fd.assert_called_once_with(42)

    @patch.object(clock.os, 'close')
    @patch.object(clock.os, 'open', return_value=42)
    @patch.object(clock.fcntl, 'flock')
    @patch.object(clock, 'is_k95', return_value=True)
    def test_short_write_is_failure(self, is_k95, flock, open_fd, close_fd):
        def ioctl(fd, command, buffer):
            if command == clock.HIDIOCGRAWINFO:
                buffer[:] = struct.pack('=IHH', 3, 0x258A, 0x019D)
                return 0
            return 20
        with patch.object(clock.fcntl, 'ioctl', side_effect=ioctl):
            with self.assertRaisesRegex(RuntimeError, 'short HID transfer'):
                clock.sync_device(Path('/dev/hidraw9'))
        close_fd.assert_called_once_with(42)


if __name__ == '__main__':
    unittest.main()
