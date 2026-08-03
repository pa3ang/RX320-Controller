# Ten-Tec RX320 Control Program
## Version 1.0 (July 2026)

---

## 1. Introduction

The **RX320 Control Program** is a Python/Tkinter desktop application for controlling the **Ten-Tec RX320** receiver.

The RX320 is controlled via an RS-232 serial port. It supports only a limited command set, and the desired receive frequency must be converted into the appropriate tuning factors (see the separate document in the `doc` folder of this repository).

The program performs all required calculations to determine the correct tuning values and also applies a user-defined `freq_offset`, allowing accurate frequency calibration after the receiver has been calibrated with an external source.

> **Note:** Due to component aging, the RX320's frequency may drift over time. The `freq_offset` setting can be used to compensate for this drift after calibration.

### Main Features

- **Frequency, Mode, Filter, and AGC** control
- **Direct Frequency** entry with tuning buttons for **±1 kHz** and **±100 Hz** 
- **Band** selection with predefined Amateur Radio band frequencies
- **2 Quick Memory** buttons, functioning as temporary memory locations
- **4 Fixed Memory** buttons
- **2 Drop-down** menus with additional frequency/mode presets
- **S-Meter**
- **DX Cluster** window with click-to-tune functionality

> **Note:** The RX320 only supports reading the **signal strength** from the receiver. Frequency, Mode, Filter, and AGC settings cannot be read back, so the application keeps track of their current values internally.
---

## 2. Requirements

- Python 3 with Tkinter (already included in most Python installations)
- A serial connection to the transceiver (USB /RS232 cable)
- Internet access for the DX Cluster feature

> **Note:** the Tkinter geometrics is tailored for a 7"TFT screen.

### Required files

| File | Purpose |
|---|---|
| `rx320.ini` | All user-specific settings |
| `rx320.py` | RX320 communication class |
| `dxcluster.py` | DX Cluster network class |
| `rx320.png` | Ten-Tec logo |
---

## 3. Configuration file: `rx320.ini`

The `.ini` file is divided into sections. All of them are required.

### `[Radio]`

```ini
port = /dev/ttyUSB0
freq_offset_low = -50
freq_offset_high = -300
cw_pitch = 700
volume = 30
start_frequency = 7073000
```

| Parameter | Description |
|-----------|-------------|
| `port` | Serial port to which the RX320 is connected. Under Linux this is typically `/dev/ttyUSB0`. |
| `freq_offset_low` | Frequency calibration offset (Hz) measured at 100 kHz. |
| `freq_offset_high` | Frequency calibration offset (Hz) measured at 30 MHz. |
| `cw_pitch` | CW audio pitch in Hz. This value is used when tuning to CW signals. |
| `volume` | Initial receiver volume (0–63). |
| `start_frequency` | Frequency in Hz that is set when the program starts. |
---

### `[Messages]`
```
callsign  = PA3ANG
message_1 = R UR 55N 55N OP JOHAN 73
literal_1 = REPORT
message_2 = TU
literal_2 = TU
cq        = CQ CQ DE PA3ANG PA3ANG K
```
- `callsign` — used on the first CW button, and also for RBN searches and DX Cluster login.
- `message_1` / `message_2` — the actual CW text sent by buttons 2 and 3.
- `literal_1` / `literal_2` — the short text shown **on** those buttons (the full message shows as a tooltip on hover).
- `cq` — text sent by the CQ button.

### `[Memories]`
```
fixed = 3630,LSB;7073,LSB;14060,CW;14292,USB
extra_1 = 3573,CW;10136,DIGI;
extra_2 = ...
```
Each entry is `frequency(kHz),mode`, separated by semicolons.
- `fixed` — fills the 4 fixed memory buttons (in order).
- `extra` — fills the **Extra Memories** drop-down menu, useful for additional frequencies that don't need a dedicated button.

### `[Bandplan]`
```
80m = 3500,3600,CW;3600,3800,LSB
40m = 7000,7040,CW;7040,7200,LSB
...
```
Defines band edges and the default mode to use in each frequency sub-range. This is used to:
- Populate the **Band** drop-down (only bands within your model's range are listed)
- Automatically determine the mode when tuning to a DX Cluster spot
- Look up the band name when logging a QSO to Cloudlog

### `[DXCluster]`
```
host = 	dxcluster.iu1bow.it
port = 7300
call = NOCALL
```
Your preferred DX Cluster server and alternatives, plus the callsign used to log in.

### `[Filters]`
```
commands =
    clear/spots all
    accept/spots on hf and by_zone 14,15,16
```
A list of cluster filter/setup commands (one per line) sent automatically after login.

---

## 4. The Main Window

The window title bar shows the program version and your configured QMX model.

### Top row
| Control | Function |
|---|---|
| **Frequency field** | Shows/sets the current VFO frequency in kHz. Type a value and press **Enter** to tune. |
| **Mode drop-down** | Select LSB, USB, CW, AM, or DIGI. |
| **Band drop-down** | Select a band; automatically tunes to that band using its default sub-range. |
| **S/Power Meter** | Shows receive signal in S points or RF power in Watt |

### Center row


### Memory row
| **Four buttons** | One button per entry in `[Memories] fixed`. Each button is color-coded by mode (see `[ModeColors]`) and, when clicked, instantly sets the transceiver to that frequency and mode. |
| **Extra memories** | In a drop-down menu, configured under `[Memories] extra` and colored by mode as well. |


### DX Cluster Window
| **Double-click (left)** a spot | Tunes the receiver to that spot's frequency and sets the correct mode from the bandplan. |

---


## 5. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Program won't start / crashes immediately | `rx320.ini` missing, malformed, or missing a required section |
| No frequency/mode updates from the radio | Wrong serial port in `[Serial]`, or cable/driver issue |
| No DX spots appear | Check `[DXCluster]` host, port, callsign and your internet connection |
| Band drop-down is empty or missing bands | Check that `[Bandplan]` entries fall within your configured QMX model's frequency range |

---

## 6. File Summary (Linux/macOS)

```
project-folder/
├── rx320.ini         (your settings — edit this)
├── main.py           (this program)
├── rx320.py            (QMX CAT communication)
├── dxcluster.py      (DX Cluster network client)

```
