import argparse
import os
import socket
import sys
import threading
import time
from pathlib import Path

from .platform_utils import open_external_url
from .web_app import start_web_app


def _available_port(preferred_port: int) -> int:
    """Use the requested local port, or let the operating system choose one if occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", preferred_port))
        except OSError:
            probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_until_ready(port: int, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError("The local application server did not start in time.")


def _serve(port: int) -> None:
    start_web_app(port=port, host="127.0.0.1")


def _prepare_linux_typelib_path() -> None:
    paths: list[str] = []

    def add_paths(value: str) -> None:
        for item in value.split(os.pathsep):
            if item and item not in paths:
                paths.append(item)

    add_paths(os.environ.get("GI_TYPELIB_PATH", ""))
    add_paths(os.environ.get("SPOOLTAG_GI_TYPELIB_PATH", ""))
    for location in (
        Path("/usr/lib/girepository-1.0"),
        Path("/usr/local/lib/girepository-1.0"),
        *Path("/usr/lib").glob("*/girepository-1.0"),
        *Path("/usr/local/lib").glob("*/girepository-1.0"),
    ):
        if location.is_dir():
            add_paths(str(location))

    if paths:
        os.environ["GI_TYPELIB_PATH"] = os.pathsep.join(paths)


def _show_interface(url: str, browser_requested: bool = False) -> str:
    if browser_requested:
        open_external_url(url)
        return "browser"

    if sys.platform.startswith("linux"):
        _prepare_linux_typelib_path()

    try:
        import webview
    except ImportError:
        open_external_url(url)
        return "browser"

    try:
        webview.create_window(
            "SpoolTag Studio",
            url,
            width=1180,
            height=790,
            min_size=(820, 620),
            background_color="#f4f6f7",
        )
        if sys.platform.startswith("linux"):
            webview.start(gui="gtk")
        else:
            webview.start()
    except Exception as error:
        print(f"Native desktop window unavailable ({error}); opening the default browser.")
        open_external_url(url)
        return "browser"

    return "native"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create ACE-compatible NFC filament tags.")
    parser.add_argument("--browser", action="store_true", help="Open in the default browser instead of a desktop window")
    parser.add_argument("--port", type=int, default=8080, help="Preferred local server port")
    parser.add_argument("--print_readers", action="store_true", help="Print connected PC/SC reader names")
    parser.add_argument("--preferred_reader", type=str, default=None, help="Select the last reader containing this text")
    args = parser.parse_args()

    port = _available_port(args.port)
    server = threading.Thread(target=_serve, args=(port,), daemon=True, name="spooltag-server")
    server.start()
    _wait_until_ready(port)
    url = f"http://127.0.0.1:{port}"

    interface = _show_interface(url, browser_requested=args.browser)
    if interface == "browser":
        server.join()
