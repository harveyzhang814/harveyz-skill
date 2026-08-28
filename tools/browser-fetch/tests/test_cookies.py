from unittest.mock import patch

from browser_fetch.cookies import extract_cookies


def test_extract_cookies_missing_profile_returns_empty(tmp_path):
    missing_profile = tmp_path / "NoProfileHere"
    result = extract_cookies("https://example.com", str(missing_profile))
    assert result == {}


def test_extract_cookies_delegates_to_pycookiecheat(tmp_path):
    profile_dir = tmp_path / "Profile"
    profile_dir.mkdir()
    (profile_dir / "Cookies").write_bytes(b"fake-sqlite-bytes")

    with patch("browser_fetch.cookies.pycookiecheat.chrome_cookies") as mock_cc:
        mock_cc.return_value = {"session_id": "abc123"}
        result = extract_cookies("https://example.com", str(profile_dir))

    assert result == {"session_id": "abc123"}
    called_cookie_file = mock_cc.call_args.kwargs["cookie_file"]
    assert called_cookie_file != str(profile_dir / "Cookies")


def test_extract_cookies_empty_result_from_pycookiecheat(tmp_path):
    profile_dir = tmp_path / "Profile"
    profile_dir.mkdir()
    (profile_dir / "Cookies").write_bytes(b"fake-sqlite-bytes")

    with patch("browser_fetch.cookies.pycookiecheat.chrome_cookies") as mock_cc:
        mock_cc.return_value = {}
        result = extract_cookies("https://example.com", str(profile_dir))

    assert result == {}
