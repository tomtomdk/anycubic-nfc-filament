import struct

import pytest

from anycubic_nfc_app.nfc_manager.chameleon_ultra import (
    ChameleonError,
    ChameleonUltraDevice,
)


class FakeSerial:
    def __init__(self, response: bytes):
        self.response = bytearray(response)
        self.written = bytearray()

    def write(self, data: bytes) -> int:
        self.written.extend(data)
        return len(data)

    def flush(self) -> None:
        pass

    def read(self, length: int) -> bytes:
        data = self.response[:length]
        del self.response[:length]
        return bytes(data)


def response_frame(command: int, status: int, data: bytes = b"") -> bytes:
    return ChameleonUltraDevice._make_frame(command, data, status)


def test_command_frame_has_valid_checksums():
    frame = ChameleonUltraDevice._make_frame(1001, b"\x01")

    assert frame[0] == 0x11
    assert frame[1] == ChameleonUltraDevice._lrc(frame[:1])
    assert frame[8] == ChameleonUltraDevice._lrc(frame[:8])
    assert frame[-1] == ChameleonUltraDevice._lrc(frame[:-1])
    assert struct.unpack("!H", frame[2:4])[0] == 1001


def test_version_command_round_trip():
    device = ChameleonUltraDevice("COM_TEST")
    device.serial = FakeSerial(response_frame(1000, 0x68, b"\x02\x02"))

    assert device.get_version() == (2, 2)
    assert struct.unpack("!H", device.serial.written[2:4])[0] == 1000


def test_read_pages_uses_ntag_read_command():
    page_data = bytes(range(16))
    device = ChameleonUltraDevice("COM_TEST")
    device.serial = FakeSerial(response_frame(2010, 0x00, page_data))

    assert device.read_pages(4) == page_data
    payload_length = struct.unpack("!H", device.serial.written[6:8])[0]
    payload = device.serial.written[9:9 + payload_length]
    assert payload[0] == 0x74
    assert payload[-2:] == b"\x30\x04"


def test_empty_success_response_means_no_tag():
    device = ChameleonUltraDevice("COM_TEST")
    device.serial = FakeSerial(response_frame(2010, 0x00))

    assert device.read_pages(0) is None


def test_write_page_requires_tag_ack():
    device = ChameleonUltraDevice("COM_TEST")
    device.serial = FakeSerial(response_frame(2010, 0x00, b"\x0a"))
    assert device.write_page(4, b"data")

    device.serial = FakeSerial(response_frame(2010, 0x00, b"\x00"))
    assert not device.write_page(4, b"data")

    payload_length = struct.unpack("!H", device.serial.written[6:8])[0]
    payload = device.serial.written[9:9 + payload_length]
    assert payload[0] == 0x70


def test_response_checksum_is_validated():
    damaged = bytearray(response_frame(1000, 0x68, b"\x02\x02"))
    damaged[-1] ^= 0xFF
    device = ChameleonUltraDevice("COM_TEST")
    device.serial = FakeSerial(bytes(damaged))

    with pytest.raises(ChameleonError, match="checksum"):
        device.get_version()


def test_page_timeout_identifies_operation_and_page():
    device = ChameleonUltraDevice("COM_TEST")
    device.serial = FakeSerial(b"")

    with pytest.raises(TimeoutError, match="reading NTAG page 12 on COM_TEST"):
        device.read_pages(12)
