from dataclasses import dataclass

from anycubic_nfc_app.nfc_manager import nfc_reader
from anycubic_nfc_app.nfc_manager.chameleon_ultra import ChameleonPort
from anycubic_nfc_app.nfc_manager.nfc_reader import CardData, NFCReader


@dataclass
class FakeReader:
    name: str


def make_reader(selected_reader=None):
    instance = NFCReader.__new__(NFCReader)
    instance.waiting_for_tag = False
    instance.selected_reader = selected_reader
    instance.reader = None
    return instance


def test_supported_reader_profiles():
    assert NFCReader.is_supported("ACS ACR122U PICC Interface 0")
    assert NFCReader.is_supported("ACS ACR1252 1S CL Reader PICC 0")
    assert not NFCReader.is_supported("ACS ACR1252 SAM Reader 0")
    assert not NFCReader.is_supported("Generic USB Contactless Reader")


def test_automatic_selection_ignores_untested_reader(monkeypatch):
    untested = FakeReader("Generic PCSC Reader 0")
    supported = FakeReader("ACS ACR122U PICC Interface 0")
    monkeypatch.setattr(nfc_reader, "readers", lambda: [untested, supported])

    assert make_reader()._get_reader() is supported


def test_exact_selection_does_not_fall_back(monkeypatch):
    supported = FakeReader("ACS ACR122U PICC Interface 0")
    monkeypatch.setattr(nfc_reader, "readers", lambda: [supported])

    assert make_reader("Missing reader")._get_reader() is None
    assert make_reader(supported.name)._get_reader() is supported


def test_reader_inventory_marks_tested_devices(monkeypatch):
    monkeypatch.setattr(nfc_reader, "find_chameleon_ports", lambda: [])
    monkeypatch.setattr(nfc_reader, "readers", lambda: [
        FakeReader("ACS ACR1552 PICC Reader 0"),
        FakeReader("Generic Reader 0"),
    ])

    assert NFCReader.get_available_readers() == [
        {
            "id": "ACS ACR1552 PICC Reader 0", "name": "ACS ACR1552 PICC Reader 0",
            "kind": "pcsc", "supported": True,
        },
        {
            "id": "Generic Reader 0", "name": "Generic Reader 0",
            "kind": "pcsc", "supported": False,
        },
    ]


def test_reader_inventory_survives_pcsc_service_error(monkeypatch):
    def fail_to_list_readers():
        raise RuntimeError("PC/SC service unavailable")

    monkeypatch.setattr(nfc_reader, "readers", fail_to_list_readers)
    monkeypatch.setattr(nfc_reader, "find_chameleon_ports", lambda: [])

    assert NFCReader.get_available_readers() == []
    assert make_reader()._get_reader() is None


def test_chameleon_can_be_selected_by_serial_port(monkeypatch):
    reader = make_reader("chameleon:COM15")
    monkeypatch.setattr(nfc_reader, "find_chameleon_ports", lambda: [
        ChameleonPort("COM15", "USB Serial Device")
    ])

    reader._refresh_active_reader()

    assert reader.is_connected()
    assert reader.reader is None
    assert reader.chameleon_port == "COM15"
    assert reader.get_active_reader_name() == "Chameleon Ultra (COM15)"


def test_chameleon_write_is_read_back_and_verified(monkeypatch):
    class FakeChameleon:
        def __init__(self, port):
            self.pages = [bytes([page]) * 4 for page in range(45)]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def set_reader_mode(self):
            pass

        def read_pages(self, start_page):
            pages = self.pages[start_page:start_page + 4]
            while len(pages) < 4:
                pages.append(b"\x00" * 4)
            return b"".join(pages)

        def write_page(self, page, data):
            self.pages[page] = data
            return True

    monkeypatch.setattr(nfc_reader, "ChameleonUltraDevice", FakeChameleon)
    reader = make_reader("chameleon:COM15")
    reader.chameleon_port = "COM15"
    card = CardData()
    card.pages = [bytes([255 - page]) * 4 for page in range(45)]

    assert reader._write_card_chameleon(card, 45)
