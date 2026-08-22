import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from anycubic_nfc_app.desktop import _prepare_linux_typelib_path, _show_interface


def test_linux_typelib_path_keeps_bundle_and_custom_system_path():
    with patch.dict(
        os.environ,
        {"GI_TYPELIB_PATH": "bundled-typelibs", "SPOOLTAG_GI_TYPELIB_PATH": "system-typelibs"},
    ):
        _prepare_linux_typelib_path()

        paths = os.environ["GI_TYPELIB_PATH"].split(os.pathsep)

    assert paths[:2] == ["bundled-typelibs", "system-typelibs"]


def test_browser_option_skips_native_window():
    with patch("anycubic_nfc_app.desktop.open_external_url") as open_url:
        result = _show_interface("http://127.0.0.1:8080", browser_requested=True)

    assert result == "browser"
    open_url.assert_called_once_with("http://127.0.0.1:8080")


def test_linux_uses_native_gtk_window():
    webview = SimpleNamespace(create_window=Mock(), start=Mock())

    with patch.dict(sys.modules, {"webview": webview}), patch(
        "anycubic_nfc_app.desktop.sys.platform", "linux"
    ), patch("anycubic_nfc_app.desktop._prepare_linux_typelib_path") as prepare_typelibs, patch(
        "anycubic_nfc_app.desktop.open_external_url"
    ) as open_url:
        result = _show_interface("http://127.0.0.1:8080")

    assert result == "native"
    webview.create_window.assert_called_once()
    webview.start.assert_called_once_with(gui="gtk")
    prepare_typelibs.assert_called_once_with()
    open_url.assert_not_called()


def test_native_window_failure_falls_back_to_browser():
    webview = SimpleNamespace(create_window=Mock(), start=Mock(side_effect=RuntimeError("no display")))

    with patch.dict(sys.modules, {"webview": webview}), patch(
        "anycubic_nfc_app.desktop.sys.platform", "linux"
    ), patch("anycubic_nfc_app.desktop._prepare_linux_typelib_path"), patch(
        "anycubic_nfc_app.desktop.open_external_url"
    ) as open_url:
        result = _show_interface("http://127.0.0.1:8080")

    assert result == "browser"
    open_url.assert_called_once_with("http://127.0.0.1:8080")
