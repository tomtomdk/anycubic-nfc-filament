import threading
import time
from typing import List, Optional

from smartcard.CardConnection import CardConnection
from smartcard.System import readers
from smartcard.reader.Reader import Reader

from .chameleon_ultra import ChameleonUltraDevice, find_chameleon_ports


class CardData:
    """
    Card data
    """

    def __init__(self, page_count: int = 0x2d):
        """
        Create card data object
        :param page_count: Number of pages
        """
        self.pages: list[bytes] = page_count * [b"\x00\x00\x00\x00"]

    def dump(self) -> str:
        """
        Dump the data
        :return: The dump as string
        """
        pages: list[str] = []
        for page, page_data in enumerate(self.pages):
            hex_data: list[str] = [f"{x:02x}" for x in page_data]
            pages.append(f"[Page {page:02x}] {':'.join(hex_data)}")
        return "\n".join(pages)


class NFCReader:
    """
    A wrapper for NFC reader devices
    """

    # List of supported readers (each one has a list of strings that need to be part of its name)
    supported_readers: list[list[str]] = [
        ["acr122"],
        ["acr1252", "picc"],  # The ACR1252 will be recognized as two readers: PICC and SAM (SAM won`t work)
        ["acr1552", "picc"],  # The ACR1252 will be recognized as two readers: PICC and SAM (SAM won`t work)
    ]
    def __init__(self, selected_reader: Optional[str] = None):
        """
        Create an instance
        """
        self.waiting_for_tag: bool = False
        self.selected_reader: Optional[str] = selected_reader
        self.reader: Optional[Reader] = None
        self.chameleon_port: Optional[str] = None
        self._refresh_active_reader()
        checker_thread = threading.Thread(target=self.update_connection_state)
        checker_thread.daemon = True
        checker_thread.start()

    def update_connection_state(self) -> None:
        """
        Update the connection state
        """
        while True:
            self._refresh_active_reader()
            time.sleep(1)

    def _refresh_active_reader(self) -> None:
        """Resolve the selected PC/SC or Chameleon reader after hot-plug changes."""
        chameleon_ports = find_chameleon_ports()
        if self.selected_reader and self.selected_reader.startswith("chameleon:"):
            selected_port = self.selected_reader.partition(":")[2]
            self.reader = None
            self.chameleon_port = next(
                (port.device for port in chameleon_ports if port.device == selected_port),
                None,
            )
            return

        self.chameleon_port = None
        self.reader = self._get_reader()
        if not self.selected_reader and not self.reader and chameleon_ports:
            self.chameleon_port = chameleon_ports[0].device

    @classmethod
    def is_supported(cls, reader_name: str) -> bool:
        """Return whether a PC/SC reader matches a tested reader profile."""
        name = reader_name.lower()
        return any(all(part in name for part in parts) for parts in cls.supported_readers)

    @classmethod
    def get_available_readers(cls) -> list[dict[str, object]]:
        """Return all PC/SC readers, including devices without a tested profile."""
        available: list[dict[str, object]] = [
            {
                "id": reader.name,
                "name": reader.name,
                "kind": "pcsc",
                "supported": cls.is_supported(reader.name),
            }
            for reader in cls._list_readers()
        ]
        available.extend({
            "id": port.reader_id,
            "name": port.display_name,
            "kind": "chameleon",
            "supported": True,
        } for port in find_chameleon_ports())
        return available

    @staticmethod
    def _list_readers() -> list[Reader]:
        """Return PC/SC readers without failing when the smart-card service is unavailable."""
        try:
            return list(readers())
        except Exception as error:
            print(f"Unable to enumerate PC/SC readers: {error}")
            return []

    def select_reader(self, reader_name: Optional[str]) -> bool:
        """Select a reader by exact PC/SC name, or use automatic selection with None."""
        self.waiting_for_tag = False
        self.selected_reader = reader_name or None
        self._refresh_active_reader()
        return self.is_connected()

    def is_connected(self) -> bool:
        """Return whether the selected PC/SC or Chameleon reader is available."""
        return self.reader is not None or self.chameleon_port is not None

    def get_active_reader_name(self) -> Optional[str]:
        """Return the active reader's PC/SC name."""
        if self.reader:
            return self.reader.name
        if self.chameleon_port:
            return f"Chameleon Ultra ({self.chameleon_port})"
        return None

    def _get_reader(self) -> Optional[Reader]:
        """
        Get a connection to the reader device
        :return: Reader connection
        """
        available_readers: list[Reader] = self._list_readers()
        found_reader: Optional[Reader] = None

        # An explicit selection never falls back to another device.
        if self.selected_reader:
            for reader in available_readers:
                if self.selected_reader == reader.name:
                    return reader
            return None

        # Check supported readers
        if not found_reader:
            for reader in available_readers:
                # There are multiple supported readers
                for parts in self.supported_readers:
                    is_supported = True
                    # Each supported reader has multiple parts that the name needs to contain
                    for part in parts:
                        if part.lower() not in reader.name.lower():
                            is_supported = False
                    if is_supported:
                        found_reader = reader
        return found_reader

    def _read_card_chameleon(self, page_count: int) -> Optional[CardData]:
        if not self.chameleon_port:
            return None
        with ChameleonUltraDevice(self.chameleon_port) as device:
            device.set_reader_mode()
            self.waiting_for_tag = True
            first_pages: Optional[bytes] = None
            while self.waiting_for_tag and first_pages is None:
                first_pages = device.read_pages(0)
                if first_pages is None:
                    time.sleep(0.35)
            if not self.waiting_for_tag or first_pages is None:
                return None

            self.waiting_for_tag = False
            card_data = CardData(page_count)
            for start_page in range(0, page_count, 4):
                pages = first_pages if start_page == 0 else device.read_pages(start_page)
                if pages is None:
                    return None
                for offset in range(4):
                    page = start_page + offset
                    if page < page_count:
                        card_data.pages[page] = pages[offset * 4:(offset + 1) * 4]
            return card_data

    def _write_card_chameleon(self, card_data: CardData, page_count: int) -> bool:
        if not self.chameleon_port:
            return False
        with ChameleonUltraDevice(self.chameleon_port) as device:
            device.set_reader_mode()
            self.waiting_for_tag = True
            while self.waiting_for_tag:
                if device.read_pages(0) is not None:
                    break
                time.sleep(0.35)
            if not self.waiting_for_tag:
                return False

            self.waiting_for_tag = False
            for page, page_data in enumerate(card_data.pages):
                if 0x03 < page < page_count - 5:
                    if not device.write_page(page, page_data):
                        return False

            # Verify the writable application area after the tag acknowledges every page.
            for start_page in range(4, page_count - 5, 4):
                pages = device.read_pages(start_page)
                if pages is None:
                    return False
                for offset in range(4):
                    page = start_page + offset
                    if page < page_count - 5:
                        actual = pages[offset * 4:(offset + 1) * 4]
                        if actual != card_data.pages[page]:
                            return False
            return True

    @classmethod
    def _read_page(cls, connection: CardConnection, page: int) -> Optional[bytes]:
        """
        Read from page on card
        :param connection: Connection to the card
        :param page: Page number
        :return: The read data (4 bytes)
        """
        read_page_command: list[int] = [0xFF, 0xB0, 0x00, page, 0x04]
        response, sw1, sw2 = connection.transmit(read_page_command)
        if sw1 == 0x90 and sw2 == 0x00:
            return response
        else:
            return None

    @classmethod
    def _write_page(cls, connection: CardConnection, page: int, data: bytes) -> bool:
        """
        Write to page on card
        :param connection: Connection to the card
        :param page: Page number
        :param data: Data to write
        :return: Success state
        """
        write_page_command: List[int] = [0xFF, 0xD6, 0x00, page, 0x04] + list(data)
        response, sw1, sw2 = connection.transmit(write_page_command)
        if sw1 == 0x90 and sw2 == 0x00:
            return True
        else:
            return False

    def _wait_for_card(self) -> Optional[CardConnection]:
        """
        Wait for a card to be found
        :return: The connection to the card (if possible)
        """
        if not self.reader:
            return None
        connection: CardConnection = self.reader.createConnection()
        self.waiting_for_tag = True
        while self.waiting_for_tag:
            try:
                connection.connect()
                self.waiting_for_tag = False
                return connection
            except Exception:
                time.sleep(0.5)

    def read_card(self, page_count: int = 0x2d) -> Optional[CardData]:
        """
        Read data from card
        :param page_count: Number of pages on the card
        :return: The data of the card on success else None
        """
        if self.chameleon_port:
            return self._read_card_chameleon(page_count)
        connection: CardConnection = self._wait_for_card()
        if not connection:
            return None
        data: CardData = CardData(page_count)
        for page in range(0, page_count):
            d: bytes = self._read_page(connection, page)
            if d is None:
                print(f"[Error] Failed to read page {page}. Reading cancelled.")
                time.sleep(3)
                return None
            else:
                data.pages[page] = d
        return data

    def write_card(self, card_data: CardData, page_count: int = 0x2d) -> bool:
        """
        Write data to card
        :param card_data: Data to write
        :param page_count: Number of pages on the card
        :return: Success state
        """
        if self.chameleon_port:
            return self._write_card_chameleon(card_data, page_count)
        connection: CardConnection = self._wait_for_card()
        if not connection:
            return False
        for page, page_data in enumerate(card_data.pages):
            # Don't write to management data pages
            if 0x03 < page < page_count - 5:
                if not self._write_page(connection, page, page_data):
                    return False
        return True
