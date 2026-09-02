import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import calibration_gate

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "calibration_gate.py"


def _article(title="A valid title", url="https://example.com/1", date_text="d"):
    return {"title": title, "url": url, "date_text": date_text}


def test_passes_with_three_valid_unique_items():
    articles = [_article(url=f"https://example.com/{i}") for i in range(3)]
    passed, reason = calibration_gate.check_gate(articles)
    assert passed is True
    assert reason == ""


def test_fails_when_fewer_than_three_items():
    passed, reason = calibration_gate.check_gate([_article(), _article(url="https://example.com/2")])
    assert passed is False
    assert "条目数" in reason


def test_fails_when_a_title_is_too_short():
    articles = [_article(title="Hi"), _article(url="https://example.com/2"), _article(url="https://example.com/3")]
    passed, reason = calibration_gate.check_gate(articles)
    assert passed is False
    assert "title" in reason


def test_fails_when_a_title_is_too_long():
    articles = [_article(title="x" * 201), _article(url="https://example.com/2"), _article(url="https://example.com/3")]
    passed, reason = calibration_gate.check_gate(articles)
    assert passed is False
    assert "title" in reason


def test_fails_when_a_url_is_relative():
    articles = [_article(url="/relative/path"), _article(url="https://example.com/2"), _article(url="https://example.com/3")]
    passed, reason = calibration_gate.check_gate(articles)
    assert passed is False
    assert "绝对链接" in reason


def test_fails_when_urls_have_duplicates():
    articles = [_article(url="https://example.com/1"), _article(url="https://example.com/1"), _article(url="https://example.com/2")]
    passed, reason = calibration_gate.check_gate(articles)
    assert passed is False
    assert "重复" in reason


def test_cli_reads_stdin_and_prints_pass_result():
    articles = [_article(url=f"https://example.com/{i}") for i in range(3)]
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(articles),
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"passed": True, "reason": ""}


def test_cli_reads_stdin_and_prints_fail_result():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps([_article()]),
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert "条目数" in payload["reason"]
