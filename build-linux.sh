#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

if [[ -z "${PYTHON:-}" ]]; then
    PYTHON="$PROJECT_ROOT/.venv-linux/bin/python"
    if [[ ! -x "$PYTHON" ]]; then
        PYTHON="$PROJECT_ROOT/.venv/bin/python"
    fi
    if [[ ! -x "$PYTHON" ]]; then
        PYTHON="$(command -v python3 || true)"
    fi
fi
if [[ -z "$PYTHON" ]]; then
    echo "Error: Python 3 is required." >&2
    exit 1
fi
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Error: Linux packages must be built on Linux." >&2
    exit 1
fi
if ! "$PYTHON" -m PyInstaller --version >/dev/null 2>&1; then
    echo "Error: PyInstaller is not installed. Run: $PYTHON -m pip install -r requirements-dev.txt" >&2
    exit 1
fi
if ! "$PYTHON" - <<'PY'
import gi
import webview

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("WebKit2", "4.1")
except ValueError:
    gi.require_version("WebKit2", "4.0")
PY
then
    echo "Error: GTK 3, PyGObject, and WebKitGTK development bindings are required." >&2
    exit 1
fi

VERSION="$("$PYTHON" -c 'from anycubic_nfc_app.version import APP_VERSION; print(APP_VERSION)')"
MACHINE="$(uname -m)"
case "$MACHINE" in
    x86_64)
        PORTABLE_ARCH="x86_64"
        DEB_ARCH="amd64"
        ;;
    aarch64|arm64)
        PORTABLE_ARCH="aarch64"
        DEB_ARCH="arm64"
        ;;
    *)
        echo "Error: Unsupported Linux architecture: $MACHINE" >&2
        exit 1
        ;;
esac

APP_NAME="SpoolTagStudio"
PACKAGE_NAME="spooltag-studio"
PORTABLE_BASENAME="${APP_NAME}-${VERSION}-linux-${PORTABLE_ARCH}"
DEB_BASENAME="${APP_NAME}-${VERSION}-linux-${DEB_ARCH}"
STAGING_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/spooltag-studio-build.XXXXXX")"
trap 'rm -rf "$STAGING_ROOT"' EXIT
PORTABLE_ROOT="$STAGING_ROOT/$PORTABLE_BASENAME"
DEB_ROOT="$STAGING_ROOT/${PACKAGE_NAME}_${VERSION}_${DEB_ARCH}"

printf 'Building SpoolTag Studio %s for Linux %s...\n' "$VERSION" "$MACHINE"
"$PYTHON" -m PyInstaller --clean --noconfirm SpoolTagStudio.spec

mkdir -p "$PORTABLE_ROOT" "$PROJECT_ROOT/dist"
install -m 0755 "$PROJECT_ROOT/dist/$APP_NAME" "$PORTABLE_ROOT/$APP_NAME"
install -m 0644 "$PROJECT_ROOT/README.md" "$PORTABLE_ROOT/README.md"
cat > "$PORTABLE_ROOT/README-LINUX.txt" <<'EOF'
SpoolTag Studio portable Linux bundle

Run ./SpoolTagStudio from this directory. No Python installation is required.
The application runs a private local server and opens in your default web
browser. No Internet connection is needed while using it.

NFC readers require the PC/SC service (pcscd) and access to the reader device.
For Chameleon Ultra serial access, your user may need membership in the
dialout group. Log out and back in after adding group membership.
EOF

tar -C "$STAGING_ROOT" -czf "$PROJECT_ROOT/dist/${PORTABLE_BASENAME}.tar.gz" "$PORTABLE_BASENAME"

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "Error: dpkg-deb is required to create the installable .deb package." >&2
    exit 1
fi

mkdir -p \
    "$DEB_ROOT/DEBIAN" \
    "$DEB_ROOT/usr/bin" \
    "$DEB_ROOT/usr/share/applications" \
    "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps" \
    "$DEB_ROOT/usr/share/doc/$PACKAGE_NAME"

install -m 0755 "$PROJECT_ROOT/dist/$APP_NAME" "$DEB_ROOT/usr/bin/$PACKAGE_NAME"
install -m 0644 "$PROJECT_ROOT/installer/linux/spooltag-studio.desktop" \
    "$DEB_ROOT/usr/share/applications/spooltag-studio.desktop"
install -m 0644 "$PROJECT_ROOT/anycubic_nfc_app/static/images/spooltag-icon.svg" \
    "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps/spooltag-studio.svg"
install -m 0644 "$PROJECT_ROOT/installer/linux/copyright" \
    "$DEB_ROOT/usr/share/doc/$PACKAGE_NAME/copyright"
gzip -9cn "$PROJECT_ROOT/README.md" > "$DEB_ROOT/usr/share/doc/$PACKAGE_NAME/README.md.gz"
chmod 0644 "$DEB_ROOT/usr/share/doc/$PACKAGE_NAME/README.md.gz"

INSTALLED_SIZE="$(du -sk "$DEB_ROOT/usr" | cut -f1)"
cat > "$DEB_ROOT/DEBIAN/control" <<EOF
Package: $PACKAGE_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $DEB_ARCH
Installed-Size: $INSTALLED_SIZE
Maintainer: SpoolTag Studio Contributors
Depends: libpcsclite1, pcscd, python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1 | gir1.2-webkit2-4.0, xdg-utils
Homepage: https://github.com/tomtomdk/anycubic-nfc-filament
Description: NFC filament tag utility for Anycubic-compatible workflows
 SpoolTag Studio reads and writes filament profile data on NFC tags used with
 Anycubic ACE-compatible workflows. It supports PC/SC readers and Chameleon
 Ultra devices.
EOF

dpkg-deb --root-owner-group --build "$DEB_ROOT" "$PROJECT_ROOT/dist/${DEB_BASENAME}.deb"

CHECKSUM_TMP="$STAGING_ROOT/SHA256SUMS.txt"
: > "$CHECKSUM_TMP"
for artifact in \
    "SpoolTagStudio.exe" \
    "installer/SpoolTagStudio-Setup-${VERSION}.exe" \
    "${PORTABLE_BASENAME}.tar.gz" \
    "${DEB_BASENAME}.deb"; do
    if [[ -f "$PROJECT_ROOT/dist/$artifact" ]]; then
        (cd "$PROJECT_ROOT/dist" && sha256sum "$artifact") >> "$CHECKSUM_TMP"
    fi
done
mv "$CHECKSUM_TMP" "$PROJECT_ROOT/dist/SHA256SUMS.txt"

printf '\nCreated:\n  %s\n  %s\n  %s\n' \
    "$PROJECT_ROOT/dist/${PORTABLE_BASENAME}.tar.gz" \
    "$PROJECT_ROOT/dist/${DEB_BASENAME}.deb" \
    "$PROJECT_ROOT/dist/SHA256SUMS.txt"
