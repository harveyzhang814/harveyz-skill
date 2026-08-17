import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from render_view import load_archives, render_view
from conftest import write_config, set_config_path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "render_view.py"


def _run(data_dir: Path) -> subprocess.CompletedProcess:
    config_path = data_dir.parent / "config.json"
    write_config(config_path, data_dir)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={**os.environ, "HSKILL_SYNC_XTIMELINE_CONFIG": str(config_path)},
        capture_output=True, text=True, timeout=10,
    )


def _write_archive(data_dir: Path, handle: str, tweets: list[dict]) -> None:
    tweets_dir = data_dir / "tweets"
    tweets_dir.mkdir(parents=True, exist_ok=True)
    (tweets_dir / f"{handle}.json").write_text(json.dumps(tweets), encoding="utf-8")


def test_load_archives_empty_when_no_tweets_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    write_config(tmp_path / "config.json", data_dir)
    set_config_path(monkeypatch, tmp_path / "config.json")
    assert load_archives() == {}


def test_load_archives_sorts_newest_first_by_tweet_id(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    write_config(tmp_path / "config.json", data_dir)
    set_config_path(monkeypatch, tmp_path / "config.json")
    _write_archive(data_dir, "alice", [
        {"tweet_id": "1", "url": "u1", "text": "old", "timestamp": "t1"},
        {"tweet_id": "3", "url": "u3", "text": "new", "timestamp": "t3"},
        {"tweet_id": "2", "url": "u2", "text": "mid", "timestamp": "t2"},
    ])
    archives = load_archives()
    assert [t["tweet_id"] for t in archives["alice"]] == ["3", "2", "1"]


def test_render_view_groups_by_handle_and_shows_translated_text():
    archives = {
        "alice": [{"tweet_id": "2", "url": "https://x.com/alice/status/2", "text": "hi",
                    "timestamp": "t2", "translated": "你好"}],
        "bob": [{"tweet_id": "1", "url": "https://x.com/bob/status/1", "text": "yo",
                  "timestamp": "t1", "translated": "哟"}],
    }
    html = render_view(archives)
    assert "@alice" in html and "@bob" in html
    assert "你好" in html
    assert "哟" in html
    assert "https://x.com/alice/status/2" in html


def test_render_view_falls_back_to_original_text_when_translated_missing():
    archives = {"alice": [{"tweet_id": "1", "url": "u1", "text": "raw text", "timestamp": "t1"}]}
    html = render_view(archives)
    assert "raw text" in html


def test_render_view_includes_type_suffix():
    archives = {
        "alice": [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1",
                    "translated": "嗨", "type": "reply", "reply_to_handle": "@dave"}],
    }
    html = render_view(archives)
    assert "回复 @dave" in html


def test_render_view_escapes_html_in_tweet_text():
    archives = {"alice": [{"tweet_id": "1", "url": "u1", "text": "<script>x</script>", "timestamp": "t1"}]}
    html = render_view(archives)
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_view_empty_archives_shows_placeholder():
    html = render_view({})
    assert "暂无归档推文" in html


def test_cli_empty_prints_empty(tmp_path):
    result = _run(tmp_path / "data")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EMPTY"


def test_cli_writes_view_html(tmp_path):
    data_dir = tmp_path / "data"
    _write_archive(data_dir, "alice", [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1"}])
    result = _run(data_dir)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.exists()
    assert written_path.name == "view.html"
    assert "@alice" in written_path.read_text(encoding="utf-8")
