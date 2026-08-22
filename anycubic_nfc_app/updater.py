import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .platform_utils import external_environment
from .settings import APP_NAME
from .version import APP_VERSION


GITHUB_REPOSITORY = "tomtomdk/anycubic-nfc-filament"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
RELEASE_DOWNLOAD_PREFIX = f"https://github.com/{GITHUB_REPOSITORY}/releases/download/"
MAX_RELEASE_RESPONSE = 2 * 1024 * 1024
MAX_CHECKSUM_RESPONSE = 128 * 1024
MAX_INSTALLER_SIZE = 100 * 1024 * 1024


class UpdateError(RuntimeError):
    """Raised when update metadata or a downloaded update is invalid."""


def parse_version(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        raise UpdateError(f"Unsupported release version: {version}")
    return tuple(int(part) for part in match.groups())


def _installer_name(version: str, system: Optional[str] = None, machine: Optional[str] = None) -> str:
    current_system = system or platform.system()
    if current_system == "Windows":
        return f"SpoolTagStudio-Setup-{version}.exe"
    if current_system == "Linux":
        architecture = (machine or platform.machine()).lower()
        debian_architecture = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }.get(architecture)
        if debian_architecture:
            return f"SpoolTagStudio-{version}-linux-{debian_architecture}.deb"
        raise UpdateError(f"Automatic updates are not available for Linux {architecture}.")
    raise UpdateError(f"Automatic updates are not available on {current_system}.")


def evaluate_release(
    release: dict[str, Any],
    current_version: str = APP_VERSION,
    system: Optional[str] = None,
    machine: Optional[str] = None,
) -> dict[str, Any]:
    latest_version = str(release.get("tag_name", "")).removeprefix("v")
    available = parse_version(latest_version) > parse_version(current_version)
    result: dict[str, Any] = {
        "available": available,
        "current_version": current_version,
        "latest_version": latest_version,
        "release_url": str(release.get("html_url", "")),
    }
    if not available:
        return result

    assets = {str(asset.get("name", "")): asset for asset in release.get("assets", [])}
    installer_name = _installer_name(latest_version, system=system, machine=machine)
    if installer_name not in assets or "SHA256SUMS.txt" not in assets:
        raise UpdateError("The latest release does not contain a complete update for this system.")

    installer_url = str(assets[installer_name].get("browser_download_url", ""))
    checksums_url = str(assets["SHA256SUMS.txt"].get("browser_download_url", ""))
    for url in (installer_url, checksums_url):
        if not url.startswith(RELEASE_DOWNLOAD_PREFIX):
            raise UpdateError("The release contains an unexpected download location.")

    result.update({
        "installer_name": installer_name,
        "installer_url": installer_url,
        "checksums_url": checksums_url,
    })
    return result


def _read_url(url: str, maximum_size: int, timeout: float) -> bytes:
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"SpoolTagStudio/{APP_VERSION}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read(maximum_size + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise UpdateError("Could not reach GitHub Releases.") from error
    if len(data) > maximum_size:
        raise UpdateError("The update response exceeded the allowed size.")
    return data


def check_for_update(timeout: float = 8.0) -> dict[str, Any]:
    try:
        release = json.loads(_read_url(LATEST_RELEASE_API, MAX_RELEASE_RESPONSE, timeout))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise UpdateError("GitHub returned invalid release information.") from error
    if not isinstance(release, dict):
        raise UpdateError("GitHub returned invalid release information.")
    return evaluate_release(release)


def parse_checksum_file(contents: str, filename: str) -> str:
    for line in contents.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        checksum, listed_path = parts
        if Path(listed_path.lstrip("*")).name == filename and re.fullmatch(r"[a-fA-F0-9]{64}", checksum):
            return checksum.lower()
    raise UpdateError("The installer checksum is missing from the release.")


def _update_directory() -> Path:
    if local_appdata := os.environ.get("LOCALAPPDATA"):
        base = Path(local_appdata)
    elif xdg_cache_home := os.environ.get("XDG_CACHE_HOME"):
        base = Path(xdg_cache_home)
    else:
        base = Path.home() / ".cache"
    return base / APP_NAME / "updates"


def download_update(
    update: dict[str, Any],
    progress: Optional[Callable[[int], None]] = None,
    timeout: float = 30.0,
) -> Path:
    filename = str(update.get("installer_name", ""))
    version = str(update.get("latest_version", ""))
    expected_name = _installer_name(version)
    if Path(filename).name != filename or filename != expected_name:
        raise UpdateError("The release installer name is invalid.")

    checksum_bytes = _read_url(str(update["checksums_url"]), MAX_CHECKSUM_RESPONSE, timeout)
    try:
        expected_checksum = parse_checksum_file(checksum_bytes.decode("utf-8"), filename)
    except UnicodeDecodeError as error:
        raise UpdateError("The release checksum file is invalid.") from error

    update_directory = _update_directory()
    update_directory.mkdir(parents=True, exist_ok=True)
    destination = update_directory / filename
    temporary = destination.with_suffix(".part")
    request = Request(str(update["installer_url"]), headers={"User-Agent": f"SpoolTagStudio/{APP_VERSION}"})
    digest = hashlib.sha256()
    downloaded = 0
    last_progress = -1

    try:
        with urlopen(request, timeout=timeout) as response, temporary.open("wb") as output:
            total_header = response.headers.get("Content-Length")
            total = int(total_header) if total_header and total_header.isdigit() else 0
            if total > MAX_INSTALLER_SIZE:
                raise UpdateError("The release installer exceeded the allowed size.")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > MAX_INSTALLER_SIZE:
                    raise UpdateError("The release installer exceeded the allowed size.")
                output.write(chunk)
                digest.update(chunk)
                if progress and total:
                    percentage = min(100, downloaded * 100 // total)
                    if percentage != last_progress:
                        progress(percentage)
                        last_progress = percentage
    except UpdateError:
        temporary.unlink(missing_ok=True)
        raise
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        temporary.unlink(missing_ok=True)
        raise UpdateError("The update installer could not be downloaded.") from error

    if digest.hexdigest().lower() != expected_checksum:
        temporary.unlink(missing_ok=True)
        raise UpdateError("The downloaded installer failed its checksum verification.")
    temporary.replace(destination)
    if progress:
        progress(100)
    return destination


def launch_update_installer(installer_path: Path) -> None:
    if not installer_path.is_file():
        raise UpdateError("The update installer cannot be launched on this system.")

    current_system = platform.system()
    if current_system == "Windows" and installer_path.suffix.lower() == ".exe":
        command = [str(installer_path), "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"]
    elif current_system == "Linux" and installer_path.suffix.lower() == ".deb":
        if opener := shutil.which("xdg-open"):
            command = [opener, str(installer_path)]
        elif opener := shutil.which("gio"):
            command = [opener, "open", str(installer_path)]
        else:
            raise UpdateError(
                f"The package was downloaded to {installer_path}, but no graphical package opener is installed."
            )
    else:
        raise UpdateError("The update installer cannot be launched on this system.")

    try:
        subprocess.Popen(
            command,
            close_fds=True,
            env=external_environment(),
            start_new_session=current_system == "Linux",
        )
    except OSError as error:
        raise UpdateError("The operating system could not launch the update installer.") from error
