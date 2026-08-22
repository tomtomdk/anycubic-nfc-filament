import json
import os
from pathlib import Path
from typing import Any


APP_NAME = "SpoolTag Studio"


def _settings_path() -> Path:
    if appdata := os.environ.get("APPDATA"):
        base = Path(appdata)
    elif xdg_config_home := os.environ.get("XDG_CONFIG_HOME"):
        base = Path(xdg_config_home)
    else:
        base = Path.home() / ".config"
    return base / APP_NAME / "settings.json"


def load_settings() -> dict[str, Any]:
    try:
        return json.loads(_settings_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    temporary_path.replace(path)
