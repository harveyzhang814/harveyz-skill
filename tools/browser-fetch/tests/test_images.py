from pathlib import Path

import pytest

from browser_fetch.images import download_images, infer_ext, is_safe_image_url


@pytest.mark.parametrize(
    "src,expected",
    [
        ("https://example.com/img.png", True),
        ("http://example.com/img.png", True),
        ("file:///etc/passwd", False),
        ("ftp://example.com/img.png", False),
        ("http://127.0.0.1/img.png", False),
        ("http://169.254.169.254/latest/meta-data/", False),
        ("http://10.0.0.5/img.png", False),
        ("http://not-an-ip-hostname.example.com/img.png", True),
    ],
)
def test_is_safe_image_url(src, expected):
    assert is_safe_image_url(src) is expected


def test_infer_ext_from_url_extension():
    assert infer_ext("https://example.com/photo.png") == ".png"
    assert infer_ext("https://example.com/photo.jpeg") == ".jpg"
    assert infer_ext("https://example.com/photo.webp") == ".webp"


def test_infer_ext_from_content_type_takes_priority():
    assert infer_ext("https://example.com/photo", content_type="image/png") == ".png"


def test_infer_ext_defaults_to_jpg():
    assert infer_ext("https://example.com/photo") == ".jpg"


def test_download_images_skips_unsafe_url(tmp_path):
    blocks = [{"src": "file:///etc/passwd", "alt": "bad", "afterBlock": 0}]
    result = download_images(blocks, tmp_path)
    assert result == []


def test_download_images_real_network(tmp_path):
    blocks = [
        {"src": "https://www.python.org/static/img/python-logo.png", "alt": "logo", "afterBlock": -1}
    ]
    result = download_images(blocks, tmp_path)
    assert len(result) == 1
    assert result[0]["filename"] == "img_1.png"
    assert result[0]["alt"] == "logo"
    assert result[0]["after_block"] == -1
    downloaded_file = Path(tmp_path) / "Image" / "img_1.png"
    assert downloaded_file.exists()
    assert downloaded_file.stat().st_size > 0


def test_download_images_failed_download_still_returns_entry(tmp_path):
    """urlopen() raises HTTPError for a 404 before any bytes are written,
    so the file never gets created — but the entry is still returned so
    the caller can see which image failed."""
    blocks = [{"src": "https://example.com/definitely-does-not-exist-404.png", "alt": "", "afterBlock": 0}]
    result = download_images(blocks, tmp_path)
    assert len(result) == 1
    assert result[0]["filename"] == "img_1.png"
    assert not (Path(tmp_path) / "Image" / "img_1.png").exists()
