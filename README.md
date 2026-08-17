# SpoolTag Studio

SpoolTag Studio is an offline Windows desktop utility for reading and writing filament profile data on NFC tags used with Anycubic ACE-compatible workflows. It provides an embedded desktop window, a persistent light/dark theme, live PC/SC reader selection, filament presets, tag reading and writing, and raw dump export.

This is an unofficial community utility. Anycubic is a trademark of its respective owner and does not endorse this project.

## Download

- [Portable Windows application](dist/SpoolTagStudio.exe)
- [Windows installer](dist/installer/SpoolTagStudio-Setup-0.2.0.exe)
- [SHA-256 checksums](dist/SHA256SUMS.txt)

## Hardware

- A Windows-compatible PC/SC contactless reader
- NTAG213 tags (two tags are normally used per spool)

Tested reader profiles currently include:

- Chameleon Ultra over USB (firmware 2.0 or newer; current firmware recommended)
- ACR122U
- ACR1252U PICC interface
- ACR1552U PICC interface

Other PC/SC readers appear in the reader menu as untested devices and can be selected manually. Install the manufacturer's Windows driver before starting the app. Chameleon Ultra devices are detected by USB VID/PID and communicate through their serial port; close ChameleonUltraGUI before selecting the device because only one application can own the port.

## Run From Source

Python 3.11 is recommended.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m anycubic_nfc_app
```

The application opens in a native window. To use a regular browser for troubleshooting:

```powershell
python -m anycubic_nfc_app --browser
```

Reader selection is saved in `%APPDATA%\SpoolTag Studio\settings.json`. Automatic mode selects a tested reader and ignores untested interfaces such as a reader's SAM slot.

## Build

Install development dependencies, then build the portable one-file executable:

```powershell
pip install -r requirements-dev.txt
.\build.ps1
```

The portable application is written to `dist\SpoolTagStudio.exe`.

To also create a per-user Windows installer, install Inno Setup 6 and run:

```powershell
.\build.ps1 -Installer
```

The installer is written to `dist\installer`.

## Test

```powershell
pytest
```

The automated tests do not require an NFC reader. Physical-device validation is still required before publishing a release.

## Attribution And Distribution

The NFC format research and initial implementation were based on [Molodos/anycubic-nfc-filament](https://github.com/Molodos/anycubic-nfc-filament). That upstream repository did not include a software license when this version was created. Public redistribution of derivative code requires permission from the upstream copyright holder or an independently implemented replacement for the format layer.
