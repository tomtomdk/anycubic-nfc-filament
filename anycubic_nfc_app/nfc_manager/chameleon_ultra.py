import struct
from dataclasses import dataclass
from typing import Optional

import serial
from serial.tools import list_ports


CHAMELEON_VID = 0x6868
CHAMELEON_PID = 0x8686
SERIAL_BAUD_RATE = 115200

CMD_GET_APP_VERSION = 1000
CMD_CHANGE_DEVICE_MODE = 1001
CMD_GET_DEVICE_MODEL = 1033
CMD_HF14A_RAW = 2010

STATUS_HF_TAG_OK = 0x00
STATUS_HF_TAG_NO = 0x01
STATUS_SUCCESS = 0x68


class ChameleonError(RuntimeError):
    """Raised when a Chameleon command or response is invalid."""


@dataclass(frozen=True)
class ChameleonPort:
    device: str
    description: str

    @property
    def reader_id(self) -> str:
        return f"chameleon:{self.device}"

    @property
    def display_name(self) -> str:
        return f"Chameleon Ultra ({self.device})"


@dataclass(frozen=True)
class ChameleonResponse:
    command: int
    status: int
    data: bytes


def find_chameleon_ports() -> list[ChameleonPort]:
    """Find Chameleon Ultra USB serial interfaces by their official VID/PID."""
    ports: list[ChameleonPort] = []
    try:
        available_ports = list_ports.comports()
    except Exception as error:
        print(f"Unable to enumerate serial ports: {error}")
        return ports

    for port in available_ports:
        if port.vid == CHAMELEON_VID and port.pid == CHAMELEON_PID:
            ports.append(ChameleonPort(port.device, port.description or "Chameleon Ultra"))
    return ports


class ChameleonUltraDevice:
    """Minimal USB transport for the Chameleon Ultra host protocol."""

    frame_start = 0x11
    max_data_length = 4096

    def __init__(self, port: str, timeout: float = 1.25):
        self.port = port
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None

    def __enter__(self) -> "ChameleonUltraDevice":
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _lrc(data: bytes | bytearray) -> int:
        return (-sum(data)) & 0xFF

    @classmethod
    def _make_frame(cls, command: int, data: bytes = b"", status: int = 0) -> bytes:
        if len(data) > cls.max_data_length:
            raise ValueError("Chameleon command data is too large")
        frame = bytearray(struct.pack(
            f"!BBHHHB{len(data)}sB",
            cls.frame_start, 0, command, status, len(data), 0, data, 0,
        ))
        frame[1] = cls._lrc(frame[:1])
        frame[8] = cls._lrc(frame[:8])
        frame[-1] = cls._lrc(frame[:-1])
        return bytes(frame)

    def open(self) -> None:
        if self.serial and self.serial.is_open:
            return
        self.serial = serial.Serial(
            port=self.port,
            baudrate=SERIAL_BAUD_RATE,
            timeout=self.timeout,
            write_timeout=1,
        )
        try:
            self.serial.dtr = True
        except (AttributeError, OSError):
            pass
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

    def close(self) -> None:
        if self.serial:
            self.serial.close()
            self.serial = None

    def _read_exactly(self, length: int) -> bytes:
        if not self.serial:
            raise ChameleonError("Chameleon serial port is not open")
        data = bytearray()
        while len(data) < length:
            chunk = self.serial.read(length - len(data))
            if not chunk:
                raise TimeoutError(f"Timed out waiting for Chameleon response on {self.port}")
            data.extend(chunk)
        return bytes(data)

    def _read_response(self) -> ChameleonResponse:
        # Discard noise until the start-of-frame byte is found.
        while self._read_exactly(1)[0] != self.frame_start:
            pass
        header = bytes([self.frame_start]) + self._read_exactly(8)
        if header[1] != self._lrc(header[:1]):
            raise ChameleonError("Invalid Chameleon start checksum")
        if header[8] != self._lrc(header[:8]):
            raise ChameleonError("Invalid Chameleon header checksum")

        _, _, command, status, data_length = struct.unpack("!BBHHH", header[:8])
        if data_length > self.max_data_length:
            raise ChameleonError("Chameleon response is too large")
        tail = self._read_exactly(data_length + 1)
        frame = header + tail
        if frame[-1] != self._lrc(frame[:-1]):
            raise ChameleonError("Invalid Chameleon response checksum")
        return ChameleonResponse(command, status, tail[:-1])

    def send_command(self, command: int, data: bytes = b"") -> ChameleonResponse:
        if not self.serial:
            raise ChameleonError("Chameleon serial port is not open")
        self.serial.write(self._make_frame(command, data))
        self.serial.flush()
        response = self._read_response()
        if response.command != command:
            raise ChameleonError(
                f"Unexpected Chameleon response {response.command} for command {command}"
            )
        return response

    def get_version(self) -> tuple[int, int]:
        response = self.send_command(CMD_GET_APP_VERSION)
        if response.status != STATUS_SUCCESS or len(response.data) != 2:
            raise ChameleonError("Unable to read Chameleon firmware version")
        return struct.unpack("!BB", response.data)

    def get_model(self) -> int:
        response = self.send_command(CMD_GET_DEVICE_MODEL)
        if response.status != STATUS_SUCCESS or len(response.data) != 1:
            raise ChameleonError("Unable to read Chameleon model")
        return response.data[0]

    def set_reader_mode(self) -> None:
        response = self.send_command(CMD_CHANGE_DEVICE_MODE, b"\x01")
        if response.status != STATUS_SUCCESS:
            raise ChameleonError(
                f"Chameleon refused reader mode (status 0x{response.status:02x})"
            )

    def _hf14a_raw(self, command: bytes, check_response_crc: bool) -> ChameleonResponse:
        # Firmware reads this as a big-endian bitfield: wait, CRC, auto-select,
        # and optionally response-CRC checking occupy bits 6, 5, 4, and 2.
        options = 0x70 | (0x04 if check_response_crc else 0)
        timeout_ms = 250
        payload = bytes([options]) + struct.pack("!HH", timeout_ms, len(command) * 8) + command
        return self.send_command(CMD_HF14A_RAW, payload)

    def read_pages(self, start_page: int) -> Optional[bytes]:
        """Read four consecutive NTAG pages, returning None when no tag is present."""
        try:
            response = self._hf14a_raw(bytes([0x30, start_page]), check_response_crc=True)
        except TimeoutError as error:
            raise TimeoutError(
                f"Chameleon timed out while reading NTAG page {start_page} on {self.port}"
            ) from error
        # Current firmware reports HF_TAG_OK with an empty payload when no tag answers.
        if response.status == STATUS_HF_TAG_NO or (
            response.status == STATUS_HF_TAG_OK and not response.data
        ):
            return None
        if response.status != STATUS_HF_TAG_OK or len(response.data) < 16:
            raise ChameleonError(
                f"NTAG read failed on page {start_page} (status 0x{response.status:02x})"
            )
        return response.data[:16]

    def write_page(self, page: int, data: bytes) -> bool:
        """Write one four-byte NTAG page and validate the tag ACK."""
        if len(data) != 4:
            raise ValueError("NTAG page data must contain exactly four bytes")
        try:
            response = self._hf14a_raw(bytes([0xA2, page]) + data, check_response_crc=False)
        except TimeoutError as error:
            raise TimeoutError(
                f"Chameleon timed out while writing NTAG page {page} on {self.port}"
            ) from error
        return (
            response.status == STATUS_HF_TAG_OK
            and len(response.data) >= 1
            and response.data[0] == 0x0A
        )
