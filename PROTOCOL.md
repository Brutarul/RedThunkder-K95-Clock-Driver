# K95 clock protocol and evidence

## Source

The official downloads page <https://redthundergame.com/gsjj> lists
**RedThunder K95 US Setup.zip** (2025-08-07), download ID 165048.
The package examined here was retrieved from the public mirror linked at
<https://oemdrivers.com/keyboard-redthunder-k75> (despite that page's K75 title,
the archive contains the K95 installer and K95 configuration).

SHA-256 of the analyzed files:

```text
7f266b05ae3efb16ec1abc8942d788b2dd77d92d703505c42be9431cd9e86d1c  k95-us.zip
92283ec395787b3976d8947ff829cf07587e710aca92e96fb767e8cf69817e17  OemDrv.exe
```

`app/Dev/kb/K95/KB.ini` identifies `Fw=26`, wired VID/PID `258a:019d`, wireless
VID/PID `258a:0150`, and `SendSysParam=2000`.

The installer was extracted using innoextract. OemDrv.exe was statically
disassembled and its clock-packet routines emulated in Unicorn with a fake USB
handle; HidD_SetFeature was intercepted rather than executed. No Windows utility
or firmware updater was run on the keyboard.

## Reverse-engineering landmarks (OemDrv.exe image base 0x400000)

- `0x40b8e6` selects the G5 keyboard class for Fw 26.
- `0x468c30` builds system status from Windows SYSTEMTIME and three status values.
- Vtable `0x615014`, slot `0x54`, points to `0x490120`.
- `0x490120` sends command `0x0b`, 14 payload bytes, through `0x48f100`.
- `0x48f100` constructs a zero-padded 520-byte feature report and calls
  HidD_SetFeature via `0x5bd7cc`.
- Fw 26 uses report ID 9. The connected device descriptor specifies feature
  report 9 with 519 data bytes, matching 520 bytes including the report ID.

## Packet

All offsets include the report ID at byte 0. Numeric fields are binary, not BCD.

| Offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | `09` | HID feature report ID |
| 1 | `0b` | System status / clock command |
| 2–3 | `00 00` | Subcommand / reserved |
| 4 | `01` | Packet count |
| 5 | `00` | Packet index |
| 6–7 | `0e 00` | Payload length, little-endian (14) |
| 8–10 | `00 00 00` | Non-clock system-status fields, supplied as zero |
| 11–12 | e.g. `ea 07` | Full year, little-endian (2026) |
| 13 | 1–12 | Month |
| 14 | 1–31 | Day of month |
| 15 | 0–23 | Hour, local time |
| 16 | 0–59 | Minute |
| 17 | 0–59 | Second |
| 18 | 0–6 | Day of week, Sunday = 0 |
| 19–21 | zero | Unused trailing payload bytes |
| 22–519 | zero | Padding |

The vendor clock builder leaves the final three payload bytes uninitialized;
this implementation explicitly zeros them. The other three non-clock status
bytes are also zero: this helper does not supply PC utilization/status data.

Emulating the vendor code for Friday, 2026-10-30 14:37:52 produces:

```text
09 0b 00 00 01 00 0e 00 00 00 00 ea 07 0a 1e 0e 25 34 05 00 00 00
```

followed by zero padding to 520 bytes. This is the independent test oracle.
Linux uses `HIDIOCSFEATURE(520)` (`0xc2084806` on Fedora x86_64) to transmit
the report. No checksum or preceding configuration/firmware command is required
for the tested wired keyboard.

## Hardware validation

On 2026-10-30 at 23:30:14 CET, the 520-byte report was accepted through
`/dev/hidraw9`. The owner then confirmed that the keyboard displayed the matching
local date and time. Hidraw numbering is dynamic; production code discovers it
using sysfs on every run.

The installed systemd service also completed successfully at 23:32:00 CET.
The timer was verified enabled and active, with its next run scheduled for
23:33:00. All four protocol/error-handling tests, systemd unit validation, and
udev rule syntax validation passed. Physical replug, reboot, and suspend/resume
were not exercised during installation.
