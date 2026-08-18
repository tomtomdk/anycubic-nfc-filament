import hashlib
import io
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from anycubic_nfc_app.updater import (
    RELEASE_DOWNLOAD_PREFIX,
    UpdateError,
    download_update,
    evaluate_release,
    parse_checksum_file,
    parse_version,
)
from anycubic_nfc_app.version import APP_VERSION


def release_payload(version="0.4.0"):
    installer_name = f"SpoolTagStudio-Setup-{version}.exe"
    base = f"{RELEASE_DOWNLOAD_PREFIX}v{version}/"
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/tomtomdk/anycubic-nfc-filament/releases/tag/v{version}",
        "assets": [
            {"name": installer_name, "browser_download_url": base + installer_name},
            {"name": "SHA256SUMS.txt", "browser_download_url": base + "SHA256SUMS.txt"},
        ],
    }


def test_semantic_versions_are_compared_numerically():
    assert parse_version("v1.10.0") > parse_version("1.9.9")
    with pytest.raises(UpdateError):
        parse_version("latest")


def test_release_selects_fixed_repository_assets():
    update = evaluate_release(release_payload(), current_version=APP_VERSION)

    assert update["available"] is True
    assert update["latest_version"] == "0.4.0"
    assert update["installer_name"] == "SpoolTagStudio-Setup-0.4.0.exe"


def test_release_rejects_untrusted_download_location():
    release = release_payload()
    release["assets"][0]["browser_download_url"] = "https://example.com/update.exe"

    with pytest.raises(UpdateError, match="unexpected download"):
        evaluate_release(release, current_version=APP_VERSION)


def test_checksum_parser_matches_only_requested_asset():
    checksum = "a" * 64
    contents = f"{'b' * 64}  another.exe\n{checksum}  installer/SpoolTagStudio-Setup-0.4.0.exe\n"

    assert parse_checksum_file(contents, "SpoolTagStudio-Setup-0.4.0.exe") == checksum


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_download_verifies_checksum_before_publishing_file(tmp_path, monkeypatch):
    installer = b"verified installer bytes"
    checksum = hashlib.sha256(installer).hexdigest()
    update = evaluate_release(release_payload(), current_version=APP_VERSION)
    checksum_file = f"{checksum}  installer/{update['installer_name']}\n".encode()
    progress = []

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("SHA256SUMS.txt"):
            return FakeResponse(checksum_file)
        return FakeResponse(installer)

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    with patch("anycubic_nfc_app.updater.urlopen", side_effect=fake_urlopen):
        destination = download_update(update, progress=progress.append)

    assert destination.read_bytes() == installer
    assert destination.name == update["installer_name"]
    assert progress[-1] == 100


def test_installer_version_matches_application_version():
    script = Path("installer/SpoolTagStudio.iss").read_text(encoding="utf-8")
    match = re.search(r'#define MyAppVersion "([^"]+)"', script)

    assert match and match.group(1) == APP_VERSION
