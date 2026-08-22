import os
import shutil
import subprocess
import sys
import webbrowser


def external_environment() -> dict[str, str]:
    """Return an environment safe for launching system tools from PyInstaller."""
    environment = os.environ.copy()
    if sys.platform.startswith("linux") and getattr(sys, "frozen", False):
        original_library_path = environment.get("LD_LIBRARY_PATH_ORIG")
        if original_library_path:
            environment["LD_LIBRARY_PATH"] = original_library_path
        else:
            environment.pop("LD_LIBRARY_PATH", None)
    return environment


def open_external_url(url: str) -> bool:
    """Open a URL without leaking bundled Linux libraries into the browser."""
    if sys.platform.startswith("linux"):
        if opener := shutil.which("xdg-open"):
            subprocess.Popen([opener, url], close_fds=True, env=external_environment(), start_new_session=True)
            return True
        if opener := shutil.which("gio"):
            subprocess.Popen(
                [opener, "open", url], close_fds=True, env=external_environment(), start_new_session=True
            )
            return True
    return webbrowser.open(url)
