from unittest.mock import patch

from anycubic_nfc_app.platform_utils import external_environment, open_external_url


def test_frozen_linux_restores_library_path(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/pyinstaller")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/local/lib")

    with patch("anycubic_nfc_app.platform_utils.sys.platform", "linux"), patch(
        "anycubic_nfc_app.platform_utils.sys.frozen", True, create=True
    ):
        environment = external_environment()

    assert environment["LD_LIBRARY_PATH"] == "/usr/local/lib"


def test_linux_url_opener_uses_clean_environment():
    with patch("anycubic_nfc_app.platform_utils.sys.platform", "linux"), patch(
        "anycubic_nfc_app.platform_utils.shutil.which", return_value="/usr/bin/xdg-open"
    ), patch("anycubic_nfc_app.platform_utils.external_environment", return_value={"PATH": "/usr/bin"}), patch(
        "anycubic_nfc_app.platform_utils.subprocess.Popen"
    ) as popen:
        assert open_external_url("https://example.com") is True

    popen.assert_called_once_with(
        ["/usr/bin/xdg-open", "https://example.com"],
        close_fds=True,
        env={"PATH": "/usr/bin"},
        start_new_session=True,
    )
