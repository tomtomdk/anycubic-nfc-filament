import argparse
import threading
from typing import Any, Optional

from flask import Flask, render_template, request
from flask_socketio import SocketIO

from .filaments import FILAMENT_PRESETS
from .nfc_manager import SpoolReader, NFCReader
from .settings import load_settings, save_settings

# App settings
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # Max upload size of 1MB
socketio = SocketIO(app, async_mode="threading")


# Fix error handling
@socketio.on_error_default  # catches all unhandled errors
def default_error_handler(e):
    print("SocketIO error occurred:")
    import traceback
    traceback.print_exc()


settings = load_settings()
spool_reader: SpoolReader = SpoolReader(selected_reader=settings.get("selected_reader"))
operation_lock = threading.Lock()


@app.route("/", methods=["GET", "POST"])
def root():
    """
    Root page
    """
    return render_template("root.html", filament_presets=FILAMENT_PRESETS,
                           filament_types=SpoolReader.get_available_filament_types())


@socketio.on("ping")
def handle_ping():
    """
    Handle a ping from the client
    """
    socketio.emit("nfc_state", get_reader_state(), to=request.sid)


def get_reader_state() -> dict[str, Any]:
    """Build the reader state sent to the desktop client."""
    return {
        "reader_connected": spool_reader.get_connection_state(),
        "selected_reader": spool_reader.reader.selected_reader,
        "active_reader": spool_reader.reader.get_active_reader_name(),
        "readers": NFCReader.get_available_readers(),
        "busy": operation_lock.locked(),
    }


@socketio.on("select_reader")
def select_reader(data: dict[str, Any]):
    """Select a PC/SC reader by its exact name; an empty name enables automatic mode."""
    if operation_lock.locked():
        socketio.emit("reader_selected", {
            "success": False,
            "message": "Cancel the current NFC operation before changing readers.",
            "state": get_reader_state(),
        }, to=request.sid)
        return

    selected_reader = data.get("reader") or None
    known_reader_ids = {item["id"] for item in NFCReader.get_available_readers()}
    if selected_reader and selected_reader not in known_reader_ids:
        socketio.emit("reader_selected", {
            "success": False,
            "message": "That reader is no longer connected.",
            "state": get_reader_state(),
        }, to=request.sid)
        return

    spool_reader.reader.select_reader(selected_reader)
    settings["selected_reader"] = selected_reader
    try:
        save_settings(settings)
    except OSError as error:
        print(f"Unable to save settings: {error}")
    socketio.emit("reader_selected", {
        "success": True,
        "state": get_reader_state(),
    }, to=request.sid)


@socketio.on("cancel_nfc")
def cancel_nfc():
    """
    Cancel the current nfc action
    """
    spool_reader.cancel_wait_for_tag()
    socketio.emit("canceled")


@socketio.on("read_tag")
def read_tag():
    """
    Read from a tag
    """
    socketio.start_background_task(_read_tag_async, request.sid)


def _read_tag_async(socket_id):
    """
    Read from a tag (async)
    :param socket_id: Id of the socket to respond to
    """
    if not operation_lock.acquire(blocking=False):
        socketio.emit("read_done", {"success": False, "busy": True}, to=socket_id)
        return
    error_message = None
    try:
        spool_data: Optional[dict[str, Any]] = spool_reader.read_spool()
    except Exception as error:
        print(f"NFC read failed: {error}")
        spool_data = None
        error_message = str(error)
    finally:
        operation_lock.release()
    result: dict[str, Any] = {
        "success": spool_data is not None
    }
    if spool_data:
        result["data"] = spool_data
    if error_message:
        result["message"] = error_message
    socketio.emit("read_done", result, to=socket_id)


@socketio.on("write_tag")
def write_tag(tag_data: dict[str, Any]):
    """
    Write to a tag
    :param tag_data: Data to write to the tag
    """
    tag_data["diameter"] = 1.75
    tag_data["length"] = 330
    tag_data["weight"] = 1000
    socketio.start_background_task(_write_tag_async, tag_data, request.sid)


def _write_tag_async(tag_data: dict[str, Any], socket_id):
    """
    Write to a tag (async)
    :param tag_data: Date to write to the tag
    :param socket_id: Id of the socket to respond to
    """
    if not operation_lock.acquire(blocking=False):
        socketio.emit("write_done", {"success": False, "busy": True}, to=socket_id)
        return
    error_message = None
    try:
        success: bool = spool_reader.write_spool(spool_specs=tag_data)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        print(f"Invalid NFC write data: {error}")
        success = False
        error_message = "The filament profile contains invalid data."
    except Exception as error:
        print(f"NFC write failed: {error}")
        success = False
        error_message = str(error)
    finally:
        operation_lock.release()
    result: dict[str, Any] = {
        "success": success
    }
    if error_message:
        result["message"] = error_message
    socketio.emit("write_done", result, to=socket_id)


@socketio.on("create_dump")
def create_dump():
    """
    Create a dump of a tag
    """
    socketio.start_background_task(_create_dump_async, request.sid)


def _create_dump_async(socket_id):
    """
    Read from a tag (async)
    :param socket_id: Id of the socket to respond to
    """
    if not operation_lock.acquire(blocking=False):
        socketio.emit("dump_done", {"success": False, "busy": True}, to=socket_id)
        return
    error_message = None
    try:
        uid, dump_data = spool_reader.read_spool_raw()
    except Exception as error:
        print(f"NFC dump failed: {error}")
        uid, dump_data = None, None
        error_message = str(error)
    finally:
        operation_lock.release()
    result: dict[str, Any] = {
        "success": dump_data is not None
    }
    if dump_data:
        result["filename"] = f"spool_dump_{uid}.txt"
        result["data"] = dump_data
    if error_message:
        result["message"] = error_message
    socketio.emit("dump_done", result, to=socket_id)


def get_connected_readers() -> list[str]:
    """
    Get the connected readers
    :return: List of connected readers
    """
    return [item["name"] for item in NFCReader.get_available_readers()]


def set_preferred_reader(reader_filter: str) -> None:
    """
    Set the preferred reader
    :param reader_filter: String that the reader needs to contain
    """
    if not reader_filter:
        return
    matching_readers = [
        item for item in NFCReader.get_available_readers()
        if reader_filter.lower() in str(item["name"]).lower()
    ]
    if matching_readers:
        spool_reader.reader.select_reader(str(matching_readers[-1]["id"]))


def start_web_app(port: int = 8080, host: str = "127.0.0.1"):
    """
    Init point of the web app
    :param port: The server port
    """
    # Parse args
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--print_readers', action='store_true',
                        help='Add this flag to print connected readers on startup')
    parser.add_argument('--preferred_reader', type=str, default=None,
                        help='Default reader to select (the reader name must contain that)')
    args, _ = parser.parse_known_args()

    # Start web app
    if args.print_readers:
        print(f"Connected readers: {get_connected_readers()}\n")

    # Add extra supported reader
    if args.preferred_reader:
        print(f"Set '{args.preferred_reader}' as preferred reader (the reader name must contain that)\n")
        set_preferred_reader(args.preferred_reader)

    print(f"SpoolTag Studio started. Access it under http://{host}:{port}")
    print("Press Ctrl+C or just close this window to exit")
    socketio.run(app, port=port, host=host, allow_unsafe_werkzeug=True)
