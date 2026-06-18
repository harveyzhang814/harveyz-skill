from unittest.mock import patch, MagicMock
import pytest
from sync_agent.syncthing import SyncthingClient, SyncthingError


BASE = "http://127.0.0.1:8384"
KEY = "testkey"


def make_response(json_data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data
    m.text = str(json_data)
    return m


@pytest.fixture
def client():
    return SyncthingClient(BASE, KEY)


def test_ping_returns_true_on_pong(client):
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.return_value = make_response({"ping": "pong"})
        assert client.ping() is True


def test_ping_returns_false_on_error(client):
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.side_effect = Exception("connection refused")
        assert client.ping() is False


def test_get_folders_returns_list(client):
    folders = [{"id": "f1", "path": "/tmp/docs"}]
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.return_value = make_response(folders)
        result = client.get_folders()
    assert result == folders


def test_add_folder_posts_to_api(client):
    folder = {"id": "f1", "path": "/tmp/docs", "label": "Docs"}
    with patch("sync_agent.syncthing.requests.post") as mock_post:
        mock_post.return_value = make_response({})
        client.add_folder(folder)
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == folder


def test_add_folder_raises_on_error(client):
    with patch("sync_agent.syncthing.requests.post") as mock_post:
        mock_post.return_value = make_response({"error": "bad"}, status=400)
        with pytest.raises(SyncthingError) as exc_info:
            client.add_folder({"id": "f1", "path": "/tmp"})
    assert "400" in str(exc_info.value)


def test_remove_folder_sends_delete(client):
    with patch("sync_agent.syncthing.requests.delete") as mock_del:
        mock_del.return_value = make_response({})
        client.remove_folder("f1")
    mock_del.assert_called_once()
    assert "f1" in mock_del.call_args[0][0]


def test_get_my_device_id(client):
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.return_value = make_response({"myID": "ABC-DEF-GHI"})
        assert client.get_my_device_id() == "ABC-DEF-GHI"


def test_get_completion(client):
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.return_value = make_response({"completion": 87.5})
        assert client.get_completion("f1") == 87.5


def test_shutdown_posts(client):
    with patch("sync_agent.syncthing.requests.post") as mock_post:
        mock_post.return_value = make_response({})
        client.shutdown()
    mock_post.assert_called_once()
    assert "shutdown" in mock_post.call_args[0][0]
