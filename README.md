# SpoolTag Studio

SpoolTag Studio is an offline Linux and Windows desktop utility for reading and writing filament profile data on NFC tags used with Anycubic ACE-compatible workflows. It provides a native desktop window, a persistent light/dark theme, live PC/SC reader selection, filament presets, tag reading and writing, and raw dump export.

This is an unofficial community utility. Anycubic is a trademark of its respective owner and does not endorse this project.

## Download

- [Portable Linux x86-64 bundle](dist/SpoolTagStudio-0.3.1-linux-x86_64.tar.gz)
- [Installable Linux x86-64 package](dist/SpoolTagStudio-0.3.1-linux-amd64.deb)
- [Portable Windows application](dist/SpoolTagStudio.exe)
- [Windows installer](dist/installer/SpoolTagStudio-Setup-0.3.1.exe)
- [SHA-256 checksums](dist/SHA256SUMS.txt)

### Install on Linux

For Debian, Ubuntu, Linux Mint, Pop!_OS, and related x86-64 distributions:

```bash
sudo apt install ./dist/SpoolTagStudio-0.3.1-linux-amd64.deb
spooltag-studio
```

The package adds **SpoolTag Studio** to the desktop application menu. To remove it:

```bash
sudo apt remove spooltag-studio
```

For the portable version, extract and run it without installation:

```bash
tar -xzf dist/SpoolTagStudio-0.3.1-linux-x86_64.tar.gz
cd SpoolTagStudio-0.3.1-linux-x86_64
./SpoolTagStudio
```

The portable executable contains Python and all Python packages. On Linux it opens a native GTK/WebKit window when the required desktop libraries are installed, and falls back to the default browser if they are unavailable. No Internet connection is needed while using it.

## Hardware

- A PC/SC-compatible contactless reader
- NTAG213 tags (two tags are normally used per spool)

Tested reader profiles currently include:

- Chameleon Ultra over USB (firmware 2.0 or newer; current firmware recommended)
- ACR122U
- ACR1252U PICC interface
- ACR1552U PICC interface

Other PC/SC readers appear in the reader menu as untested devices and can be selected manually. On Windows, install the manufacturer's reader driver. On Linux, install and start `pcscd`; the `.deb` package declares it as a dependency. Chameleon Ultra devices are detected by USB VID/PID and communicate through their serial port; close ChameleonUltraGUI before selecting the device because only one application can own the port.

## Run From Source

Python 3.11 is recommended.

Linux:

```bash
sudo apt install python3-venv python3-dev python3-gi build-essential pkg-config libpcsclite-dev pcscd xdg-utils gir1.2-gtk-3.0 gir1.2-webkit2-4.1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m anycubic_nfc_app
```

Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m anycubic_nfc_app
```

The application opens in a native window. To force browser mode explicitly:

```bash
python -m anycubic_nfc_app --browser
```

Reader selection is saved in `%APPDATA%\SpoolTag Studio\settings.json` on Windows and `${XDG_CONFIG_HOME:-~/.config}/SpoolTag Studio/settings.json` on Linux. Automatic mode selects a tested reader and ignores untested interfaces such as a reader's SAM slot.

## Updates

Use the cloud-download button in the application header to check for releases manually. Automatic checks are optional and disabled by default. The app downloads the matching Windows `.exe` or Linux `.deb` only after the user selects **Download and install**, verifies it against the release SHA-256 checksum, and then opens the normal visible installer.

## Build

### Linux

Install the Linux system packages listed under **Run From Source**, install development dependencies, then create both Linux packages:

```bash
pip install -r requirements-dev.txt
./build-linux.sh
```

The build writes a portable `.tar.gz`, an installable `.deb`, and updated SHA-256 checksums to `dist/`. Packages are architecture-specific and must be built on the target architecture. Release packages use the Ubuntu 22.04 workflow as their compatibility baseline.

### Windows

Build the portable one-file executable with:

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

```bash
pytest
```

The automated tests do not require an NFC reader. Physical-device validation is still required before publishing a release.

## Attribution And Distribution

The NFC format research and initial implementation were based on [Molodos/anycubic-nfc-filament](https://github.com/Molodos/anycubic-nfc-filament). That upstream repository did not include a software license when this version was created. Public redistribution of derivative code requires permission from the upstream copyright holder or an independently implemented replacement for the format layer.
