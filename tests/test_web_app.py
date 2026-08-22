from anycubic_nfc_app.web_app import app, socketio


def test_root_is_self_contained_workspace():
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "SpoolTag Studio" in html
    assert 'id="readerSelect"' in html
    assert 'id="themeToggle"' in html
    assert 'id="writeButton"' in html
    assert "spooltag-theme" in html
    assert "cdn.jsdelivr.net" not in html
    assert "code.jquery.com" not in html


def test_socket_reports_reader_inventory():
    client = socketio.test_client(app)
    client.get_received()
    client.emit("ping")

    messages = client.get_received()
    state = next(message["args"][0] for message in messages if message["name"] == "nfc_state")
    assert set(state) == {
        "reader_connected", "selected_reader", "active_reader", "readers", "busy", "updates"
    }
    assert isinstance(state["readers"], list)
    assert state["updates"]["current_version"] == "0.3.1"
    assert isinstance(state["updates"]["automatic"], bool)
    client.disconnect()
