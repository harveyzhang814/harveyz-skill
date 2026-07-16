from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent / 'references' / 'subagent2-tag-translate-prompt.md'


def test_subagent2_prompt_uses_shared_path_resolver():
    content = PROMPT_PATH.read_text(encoding='utf-8')
    assert 'get_article_paths' in content
    assert "os.path.basename(origin_path)" not in content
    assert "json.loads((Path.home()" not in content


def test_subagent2_prompt_wikilink_includes_hash_prefix():
    content = PROMPT_PATH.read_text(encoding='utf-8')
    assert "[[{paths['url_hash']}/Origin/" in content or "paths['url_hash']}/Origin/" in content
    assert '[[Origin/<文件名>]]' not in content
