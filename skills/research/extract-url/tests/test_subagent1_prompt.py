from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent / 'references' / 'subagent1-fetch-prompt.md'


def test_subagent1_prompt_keeps_dedup_check_contract():
    content = PROMPT_PATH.read_text(encoding='utf-8')
    assert 'dedup_check.py' in content
    assert "'CHECK_URL':" in content
    assert 'ALREADY_FETCHED' in content


def test_subagent1_prompt_no_sqlite_mention():
    content = PROMPT_PATH.read_text(encoding='utf-8')
    assert 'sqlite' not in content.lower()
