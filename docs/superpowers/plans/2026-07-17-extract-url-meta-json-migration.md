# extract-url 索引改为 meta.json + 合并迁移 实施计划

**目标：** 把 extract-url skill 的索引存储从集中式 SQLite（`url-index.db`）改为每篇文章目录下的 `meta.json`，并把这次迁移与上一版本尚未对真实 Vault 数据执行的目录结构迁移（flat → `<hash8>/{Origin,Translation,Image}/`）合并成一次迁移，对真实 Vault 数据一并执行。

**架构：** 去重查询从 SQL 精确匹配改为「`<hash8>` 目录名即索引键、`meta.json` 存在性即索引条目」的文件系统方案，不再需要数据库。运行时读写路径（`article_utils.py`/`dedup_check.py`/`validate_article.py`/三个 `playwright_*.py`）和离线迁移脚本（`migrate_to_folder_structure.py`）复用同一套 `meta.json` 写入语义。合并迁移脚本沿用已有的「先 plan 预览、再 apply 执行」两阶段人工确认节奏。

**技术栈：** Python 3、pytest、PyYAML（无需新增依赖，去掉 `sqlite3` 依赖）。

**设计文档：** `docs/superpowers/specs/2026-07-16-extract-url-meta-json-migration-design.md`

**对已批准设计的两处范围修正**（写计划时发现，均为缩小范围，非新增决策）：
1. 设计文档提到 `repair_frontmatter` 的假阳性问题（原文永远缺 `description`）需要一并修——已在计划里通过新增 `skip_remaining_fields` 参数解决（见 Task 1）。
2. 设计文档描述 `subagent1-fetch-prompt.md` 要「新增写临时 issues 文件一步」——实际读代码后发现这一步完全发生在 Python 脚本内部（`playwright_web.py` 等自己调用 `record_fetch_issues`），提示词本身不需要新增步骤，只需把「查 SQLite 去重」的文案改成「查 meta.json 去重」（见 Task 8）。

---

### Task 1: article_utils.py — meta.json 读写函数 + repair_frontmatter 排除字段参数

**文件：**
- 修改: `skills/research/extract-url/references/article_utils.py`
- 测试: `skills/research/extract-url/tests/test_article_utils_meta.py`（新建）

- [ ] **Step 1: 编写失败的测试**

创建 `skills/research/extract-url/tests/test_article_utils_meta.py`：

```python
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'references'))
from article_utils import repair_frontmatter, record_fetch_issues, write_meta_json


def test_repair_frontmatter_skips_excluded_fields_from_remaining(tmp_path):
    fp = tmp_path / 'origin.md'
    fp.write_text(
        "---\npublish_date: 2026-01-01\nauthor: Someone\nsource_url: https://example.com/x\n"
        "origin_title: \"X\"\n---\n\nBody\n",
        encoding='utf-8'
    )
    fm, fixed, remaining = repair_frontmatter(fp, 'https://example.com/x', skip_remaining_fields={'description'})
    assert 'description空' not in remaining


def test_repair_frontmatter_still_flags_description_when_not_skipped(tmp_path):
    fp = tmp_path / 'origin.md'
    fp.write_text(
        "---\npublish_date: 2026-01-01\nauthor: Someone\nsource_url: https://example.com/x\n"
        "origin_title: \"X\"\n---\n\nBody\n",
        encoding='utf-8'
    )
    fm, fixed, remaining = repair_frontmatter(fp, 'https://example.com/x')
    assert 'description空' in remaining


def test_record_fetch_issues_writes_temp_file(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_dir.mkdir()
    record_fetch_issues('author空', article_dir)
    assert (article_dir / '.fetch_issues.tmp').read_text(encoding='utf-8') == 'author空'


def test_record_fetch_issues_clears_temp_file_when_no_issues(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_dir.mkdir()
    (article_dir / '.fetch_issues.tmp').write_text('stale issue', encoding='utf-8')
    record_fetch_issues('', article_dir)
    assert not (article_dir / '.fetch_issues.tmp').exists()


def test_write_meta_json_creates_file_with_expected_fields(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_dir.mkdir()
    article_path = article_dir / 'article.md'
    article_path.write_text("---\ncategory: tech\n---\n\nBody\n", encoding='utf-8')
    meta_path = article_dir / 'meta.json'

    write_meta_json('https://example.com/x', meta_path, article_path)

    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['source_url'] == 'https://example.com/x'
    assert meta['title'] == 'article.md'
    assert meta['category'] == 'tech'
    assert meta['issues'] == ''


def test_write_meta_json_merges_pending_fetch_issues(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_dir.mkdir()
    (article_dir / '.fetch_issues.tmp').write_text('author空', encoding='utf-8')
    article_path = article_dir / 'article.md'
    article_path.write_text("---\n---\n\nBody\n", encoding='utf-8')
    meta_path = article_dir / 'meta.json'

    write_meta_json('https://example.com/y', meta_path, article_path)

    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['issues'] == 'author空'
    assert not (article_dir / '.fetch_issues.tmp').exists()


def test_write_meta_json_creates_parent_dir_if_missing(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_path = tmp_path / 'article.md'
    article_path.write_text("---\n---\n\nBody\n", encoding='utf-8')
    meta_path = article_dir / 'meta.json'

    write_meta_json('https://example.com/z', meta_path, article_path)

    assert meta_path.exists()
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_article_utils_meta.py -v`
预期: FAIL（`record_fetch_issues`/`write_meta_json` 不存在，`repair_frontmatter` 不接受 `skip_remaining_fields` 参数）

- [ ] **Step 3: 编写最小实现**

修改 `skills/research/extract-url/references/article_utils.py` 第 4 行导入，去掉 `sqlite3`，加 `pathlib`：

旧：
```python
import re, os, json, sqlite3, yaml
from datetime import datetime, timezone, timedelta
```

新：
```python
import re, os, json, yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path
```

第 116 行 `repair_frontmatter` 签名加参数：

旧：
```python
def repair_frontmatter(fp, url, defaults=None):
```

新：
```python
def repair_frontmatter(fp, url, defaults=None, skip_remaining_fields=None):
```

第 238-247 行「检查剩余问题」块：

旧：
```python
    # 检查剩余问题
    for fld in ['publish_date', 'author', 'source_url']:
        if not fm.get(fld, '').strip():
            remaining.append(f'{fld}空')
    if 'origin_title' not in fm or not fm.get('origin_title', '').strip():
        remaining.append('origin_title空')
    if 'description' not in fm or not fm.get('description', '').strip():
        remaining.append('description空')

    return fm, fixed, remaining
```

新：
```python
    # 检查剩余问题
    skip = set(skip_remaining_fields or ())
    for fld in ['publish_date', 'author', 'source_url']:
        if fld not in skip and not fm.get(fld, '').strip():
            remaining.append(f'{fld}空')
    if 'origin_title' not in skip and ('origin_title' not in fm or not fm.get('origin_title', '').strip()):
        remaining.append('origin_title空')
    if 'description' not in skip and ('description' not in fm or not fm.get('description', '').strip()):
        remaining.append('description空')

    return fm, fixed, remaining
```

第 250-287 行（`record_issues` + `write_url_index` 两个函数）整体替换：

旧：
```python
# ------------------------------------------------------------
# 5. record_issues: 写入 issues 字段
# ------------------------------------------------------------
def record_issues(url, issues_text, db_path=None):
    """将 issues 写入 SQLite"""
    if db_path is None:
        raise ValueError("db_path is required")
    conn = sqlite3.connect(db_path)
    conn.execute('UPDATE url_index SET issues=? WHERE source_url=?',
                 (issues_text, url))
    conn.commit()


# ------------------------------------------------------------
# 6. write_url_index: 写入 SQLite url_index 表
# ------------------------------------------------------------
def write_url_index(url, origin_path, article_path, db_path, category=''):
    """Insert or replace a URL index entry after successful fetch+translate."""
    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    fm = {}
    try:
        with open(article_path, encoding='utf-8') as f:
            content = f.read()
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        pass
    cat = category or (fm.get('category') or '')
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO url_index "
        "(source_url, title, fetched_at, issues, category, origin_path, article_path) "
        "VALUES (?,?,?,?,?,?,?)",
        (url, os.path.basename(article_path), fetch_date, '', cat, origin_path, article_path)
    )
    conn.commit()
```

新：
```python
# ------------------------------------------------------------
# 5. record_fetch_issues: Subagent 1 阶段的问题写入临时文件，供 write_meta_json 合并
# ------------------------------------------------------------
def record_fetch_issues(issues_text, article_dir):
    """将 Subagent 1 阶段校验问题写入 <article_dir>/.fetch_issues.tmp，供 write_meta_json 合并。"""
    tmp_path = Path(article_dir) / '.fetch_issues.tmp'
    if issues_text:
        tmp_path.write_text(issues_text, encoding='utf-8')
    elif tmp_path.exists():
        tmp_path.unlink()


# ------------------------------------------------------------
# 6. write_meta_json: 写入 <hash8>/meta.json
# ------------------------------------------------------------
def write_meta_json(url, meta_path, article_path, category=''):
    """Write (or overwrite) meta.json after successful fetch+translate, merging any pending fetch-stage issues."""
    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    fm = {}
    try:
        with open(article_path, encoding='utf-8') as f:
            content = f.read()
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        pass
    cat = category or (fm.get('category') or '')

    meta_path = Path(meta_path)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_issues_path = meta_path.parent / '.fetch_issues.tmp'
    issues = ''
    if tmp_issues_path.exists():
        issues = tmp_issues_path.read_text(encoding='utf-8').strip()
        tmp_issues_path.unlink()

    meta = {
        'source_url': url,
        'title': os.path.basename(article_path),
        'category': cat,
        'fetched_at': fetch_date,
        'issues': issues,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_article_utils_meta.py -v`
预期: PASS（7 个测试全部通过）

- [ ] **Step 5: 提交**

```bash
git add skills/research/extract-url/references/article_utils.py skills/research/extract-url/tests/test_article_utils_meta.py
git commit -m "feat(extract-url): add meta.json read/write functions to article_utils"
```

---

### Task 2: dedup_check.py — 改为 meta.json 存在性检查 + conftest.py 基础设施更新

**文件：**
- 修改: `skills/research/extract-url/scripts/dedup_check.py`
- 修改: `skills/research/extract-url/tests/conftest.py`
- 修改: `skills/research/extract-url/tests/test_dedup_check.py`

- [ ] **Step 1: 编写失败的测试**

先重写 `skills/research/extract-url/tests/conftest.py`（去掉 `url_index_db` fixture，新增 `write_meta_json_fixture` 工厂 fixture，`valid_article_files` 不再依赖 `url_index_db`）：

```python
import json, os, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from config import get_url_hash

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def skill_config(tmp_path):
    """Temp vault + config.json + env with HSKILL_EXTRACT_URL_CONFIG set."""
    vault = tmp_path / 'vault'
    vault.mkdir()
    (vault / 'Origin').mkdir()
    (vault / 'Image').mkdir()
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({
        'VAULT_PATH': str(vault),
        'CHROME_PROFILE': str(tmp_path / 'chrome-profile'),
    }), encoding='utf-8')
    env = os.environ.copy()
    env['HSKILL_EXTRACT_URL_CONFIG'] = str(cfg)
    return {'config_path': cfg, 'vault': vault, 'env': env, 'tmp': tmp_path}


@pytest.fixture
def write_meta_json_fixture(skill_config):
    """Factory: write a meta.json for a given URL into the vault's <hash8> dir."""
    def _write(url, **fields):
        hash8 = get_url_hash(url)
        article_dir = skill_config['vault'] / hash8
        article_dir.mkdir(parents=True, exist_ok=True)
        meta = {'source_url': url, 'title': '', 'category': '', 'fetched_at': '', 'issues': ''}
        meta.update(fields)
        meta_path = article_dir / 'meta.json'
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
        return meta_path
    return _write


_ARTICLE_CONTENT = """\
---
publish_date: 2024-01-01
fetch_date: 2024-01-02
author: Test Author
source_url: {url}
origin_title: "Test Article"
description: A test article for validation.
tags:
  - test
---

# Test Article

This paragraph has more than ten characters and serves as content for testing.
"""


@pytest.fixture
def valid_article_files(skill_config):
    """Create origin + translated article files with valid frontmatter."""
    url = 'https://example.com/test-article'
    content = _ARTICLE_CONTENT.format(url=url)
    origin = skill_config['vault'] / 'Origin' / 'test-article.md'
    article = skill_config['vault'] / 'test-article.md'
    origin.write_text(content, encoding='utf-8')
    article.write_text(content, encoding='utf-8')
    return {'origin': origin, 'article': article, 'url': url}
```

再重写 `skills/research/extract-url/tests/test_dedup_check.py`：

```python
import json, subprocess, os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


def test_dedup_check_ok_new_url(skill_config):
    """New URL returns OK on stdout."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': 'https://example.com/new'},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'OK'


def test_dedup_check_already_fetched(skill_config, write_meta_json_fixture):
    """URL with existing meta.json returns ALREADY_FETCHED."""
    url = 'https://example.com/existing'
    write_meta_json_fixture(url)

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': url},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ALREADY_FETCHED'


def test_dedup_check_hash_collision_url_mismatch_returns_ok(skill_config):
    """meta.json exists but source_url differs (hash collision) still returns OK."""
    from config import get_url_hash
    url = 'https://example.com/collision-check'
    hash8 = get_url_hash(url)
    article_dir = skill_config['vault'] / hash8
    article_dir.mkdir(parents=True)
    (article_dir / 'meta.json').write_text(
        json.dumps({'source_url': 'https://example.com/a-different-url'}), encoding='utf-8'
    )

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': url},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'OK'


def test_dedup_check_partial_state_no_meta_json_returns_ok(skill_config):
    """Origin exists (Subagent 1 done) but meta.json not yet written (Subagent 2 pending) -> OK, allow retry."""
    from config import get_url_hash
    url = 'https://example.com/partial'
    hash8 = get_url_hash(url)
    (skill_config['vault'] / hash8 / 'Origin').mkdir(parents=True)

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': url},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'OK'


def test_dedup_check_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={
            **os.environ,
            'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
            'CHECK_URL': 'https://example.com/test',
            'PATH': os.environ.get('PATH', ''),
        },
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert '配置文件不存在' in result.stderr
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_dedup_check.py -v`
预期: FAIL（`dedup_check.py` 仍是 SQLite 实现，不认识 meta.json）

- [ ] **Step 3: 编写最小实现**

用以下内容整体替换 `skills/research/extract-url/scripts/dedup_check.py`：

```python
#!/usr/bin/env python3
"""
Check URL dedup via meta.json existence.
Parameter via env var to avoid shell injection:
  CHECK_URL - URL to check
Reads VAULT_PATH from ~/.hskill/url-extract/config.json to locate <hash8>/meta.json.
Prints: ALREADY_FETCHED or OK
"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import get_vault_path, get_url_hash

url = os.environ['CHECK_URL']
vault_path = get_vault_path()
meta_path = Path(vault_path) / get_url_hash(url) / 'meta.json'

already_fetched = False
if meta_path.exists():
    try:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        already_fetched = meta.get('source_url') == url
    except (json.JSONDecodeError, OSError):
        already_fetched = False

print('ALREADY_FETCHED' if already_fetched else 'OK')
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_dedup_check.py tests/test_config.py tests/test_article_utils_tags.py -v`
预期: PASS（`test_dedup_check.py` 全部通过；连带跑一遍不依赖本任务改动的 `test_config.py`/`test_article_utils_tags.py` 确认 conftest.py 改动没有破坏其他测试）

- [ ] **Step 5: 提交**

```bash
git add skills/research/extract-url/scripts/dedup_check.py skills/research/extract-url/tests/conftest.py skills/research/extract-url/tests/test_dedup_check.py
git commit -m "feat(extract-url): switch dedup_check to meta.json existence check"
```

---

### Task 3: validate_article.py — 切换为 write_meta_json

**文件：**
- 修改: `skills/research/extract-url/scripts/validate_article.py`
- 修改: `skills/research/extract-url/tests/test_validate_article.py`

- [ ] **Step 1: 编写失败的测试**

用以下内容整体替换 `skills/research/extract-url/tests/test_validate_article.py`：

```python
import json, subprocess, os, yaml
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


def test_validate_article_success(skill_config, valid_article_files):
    """Valid article exits 0 and writes meta.json."""
    env = {
        **skill_config['env'],
        'ARTICLE_URL':    valid_article_files['url'],
        'ARTICLE_ORIGIN': str(valid_article_files['origin']),
        'ARTICLE_PATH':   str(valid_article_files['article']),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    from config import get_url_hash
    meta_path = skill_config['vault'] / get_url_hash(valid_article_files['url']) / 'meta.json'
    assert meta_path.exists(), 'meta.json should be written after successful validation'
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['source_url'] == valid_article_files['url']


def test_validate_article_no_article_db_env_needed(skill_config, valid_article_files):
    """Regression: ARTICLE_DB env var must NOT be required."""
    env = {
        **skill_config['env'],
        'ARTICLE_URL':    'https://example.com/no-db-test',
        'ARTICLE_ORIGIN': str(valid_article_files['origin']),
        'ARTICLE_PATH':   str(valid_article_files['article']),
        'PATH': os.environ.get('PATH', ''),
    }
    env.pop('ARTICLE_DB', None)

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, \
        f'Should work without ARTICLE_DB env var. stderr: {result.stderr}'


def test_validate_article_no_skill_dir_env_needed(skill_config, valid_article_files):
    """Regression: ARTICLE_SKILL_DIR env var must NOT be required."""
    env = {
        **skill_config['env'],
        'ARTICLE_URL':    'https://example.com/no-skill-dir-test',
        'ARTICLE_ORIGIN': str(valid_article_files['origin']),
        'ARTICLE_PATH':   str(valid_article_files['article']),
        'PATH': os.environ.get('PATH', ''),
    }
    env.pop('ARTICLE_SKILL_DIR', None)

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, \
        f'Should work without ARTICLE_SKILL_DIR env var. stderr: {result.stderr}'


def test_validate_article_missing_article_path(skill_config):
    """Exits 1 when ARTICLE_PATH does not exist."""
    env = {
        **skill_config['env'],
        'ARTICLE_URL':    'https://example.com/missing',
        'ARTICLE_ORIGIN': str(skill_config['vault'] / 'Origin' / 'missing.md'),
        'ARTICLE_PATH':   str(skill_config['vault'] / 'missing.md'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert 'not found' in result.stderr


def test_validate_article_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    env = {
        **os.environ,
        'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
        'ARTICLE_URL':    'https://example.com/test',
        'ARTICLE_ORIGIN': str(tmp_path / 'origin.md'),
        'ARTICLE_PATH':   str(tmp_path / 'article.md'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode != 0


_ARTICLE_WITH_MISPLACED_TAG = """\
---
publish_date: 2024-01-01
fetch_date: 2024-01-02
author: Test Author
source_url: {url}
origin_title: "Test Article"
tags: []
candidate_tags:
  - loop-engineering
  - novel-concept
description: A test article for validation.
---

[[Origin/test-article.md]]

---

# Test Article

This paragraph has more than ten characters and serves as content for testing.
"""


def test_validate_moves_fixed_tag_from_candidate(skill_config, tmp_path):
    """validate_article.py が fixed_tags にある candidate_tag を tags に移動する。"""
    url = 'https://example.com/tag-move-test'
    content = _ARTICLE_WITH_MISPLACED_TAG.format(url=url)
    origin = skill_config['vault'] / 'Origin' / 'tag-move-test.md'
    article = skill_config['vault'] / 'tag-move-test.md'
    origin.write_text(content, encoding='utf-8')
    article.write_text(content, encoding='utf-8')

    fixed = tmp_path / 'fixed_tags.txt'
    fixed.write_text('# topic\nloop-engineering\nai\n', encoding='utf-8')

    env = {
        **skill_config['env'],
        'ARTICLE_URL':    url,
        'ARTICLE_ORIGIN': str(origin),
        'ARTICLE_PATH':   str(article),
        'FIXED_TAGS_PATH': str(fixed),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    parts = article.read_text(encoding='utf-8').split('---', 2)
    fm = yaml.safe_load(parts[1])
    assert 'loop-engineering' in fm['tags']
    assert 'loop-engineering' not in fm.get('candidate_tags', [])
    assert 'novel-concept' in fm['candidate_tags']
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_validate_article.py -v`
预期: FAIL（`validate_article.py` 仍导入 `record_issues`/`write_url_index`，且 `url_index_db` fixture 已被删除会导致 fixture 报错）

- [ ] **Step 3: 编写最小实现**

用以下内容整体替换 `skills/research/extract-url/scripts/validate_article.py`：

```python
#!/usr/bin/env python3
"""
Post-translate validation + meta.json write for Subagent 2.
Parameters via environment variables:
  ARTICLE_URL       - source URL
  ARTICLE_ORIGIN    - path to origin .md file
  ARTICLE_PATH      - path to translated article .md file
  ARTICLE_CATEGORY  - (optional) category tag
  FIXED_TAGS_PATH   - (optional) override path for fixed_tags.txt
Reads VAULT_PATH from ~/.hskill/url-extract/config.json to locate <hash8>/meta.json.
"""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import get_vault_path, get_url_hash

url          = os.environ['ARTICLE_URL']
origin_path  = os.environ['ARTICLE_ORIGIN']
article_path = os.environ['ARTICLE_PATH']
category     = os.environ.get('ARTICLE_CATEGORY', '')

skill_dir  = str(Path(__file__).parent.parent)
vault_path = get_vault_path()
meta_path  = str(Path(vault_path) / get_url_hash(url) / 'meta.json')

sys.path.insert(0, os.path.join(skill_dir, 'references'))
from article_utils import repair_frontmatter, write_meta_json, enforce_tag_separation

if not os.path.exists(article_path):
    print(f"ERROR: article file not found: {article_path}", file=sys.stderr)
    sys.exit(1)

fm, fixed_fields, remaining = repair_frontmatter(article_path, url)
if remaining:
    print(f"ERROR: 校验未通过：{remaining}", file=sys.stderr)
    sys.exit(1)

# 兜底移位：candidate_tags 中命中固定词表的条目移入 tags
fixed_tags_path = os.environ.get(
    'FIXED_TAGS_PATH',
    str(Path.home() / '.hskill' / 'url-extract' / 'fixed_tags.txt')
)
enforce_tag_separation(article_path, fixed_tags_path)

write_meta_json(url, meta_path, article_path, category=category)
print(f"翻译完成：{article_path}")
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_validate_article.py -v`
预期: PASS（6 个测试全部通过）

- [ ] **Step 5: 提交**

```bash
git add skills/research/extract-url/scripts/validate_article.py skills/research/extract-url/tests/test_validate_article.py
git commit -m "feat(extract-url): switch validate_article to write_meta_json"
```

---

### Task 4: playwright_web.py — 切换 issues 记录方式

**文件：**
- 修改: `skills/research/extract-url/scripts/playwright_web.py`
- 修改: `skills/research/extract-url/tests/test_playwright_web.py`

- [ ] **Step 1: 编写失败的测试**

用以下内容整体替换 `skills/research/extract-url/tests/test_playwright_web.py`：

```python
import subprocess, os, pytest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'

try:
    from playwright.sync_api import sync_playwright as _sp  # noqa: F401
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

requires_playwright = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — run: pip install playwright && playwright install chromium"
)

_TEST_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <title>E2E Test Article</title>
  <meta name="author" content="E2E Author">
  <meta property="article:published_time" content="2024-06-01">
</head>
<body>
  <article>
    <h1>E2E Test Article</h1>
    <p>First paragraph with sufficient content to be captured by the playwright_web scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
  </article>
</body>
</html>
"""

_TEST_HTML_NO_AUTHOR = """\
<!DOCTYPE html>
<html>
<head>
  <title>No Author Article</title>
</head>
<body>
  <article>
    <h1>No Author Article</h1>
    <p>First paragraph with sufficient content to be captured by the playwright_web scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
  </article>
</body>
</html>
"""


def test_playwright_web_invalid_url_scheme(skill_config, tmp_path):
    """Security check rejects non-http/https URLs before reading config."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'file:///etc/passwd', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert 'Rejected URL' in result.stderr


def test_playwright_web_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    env = {
        **os.environ,
        'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'https://example.com', str(html)],
        env=env, capture_output=True, text=True
    )
    assert result.returncode != 0


def test_playwright_web_too_few_args(skill_config):
    """Script exits non-zero when html_path argument is missing."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'https://example.com'],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0


@requires_playwright
def test_playwright_web_e2e(skill_config, tmp_path):
    """Full e2e: HTML file → ORIGIN_PATH in stdout + file saved to vault."""
    html = tmp_path / 'article.html'
    html.write_text(_TEST_HTML, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'https://example.com/e2e-test', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True,
        timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert 'ORIGIN_PATH:' in result.stdout

    origin_path = next(
        line.split('ORIGIN_PATH:', 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith('ORIGIN_PATH:')
    )
    origin_file = Path(origin_path)
    assert origin_file.exists(), f'Origin file not found at {origin_path}'

    content = origin_file.read_text(encoding='utf-8')
    assert 'E2E Test Article' in content
    assert 'source_url: https://example.com/e2e-test' in content

    import hashlib
    expected_hash = hashlib.md5('https://example.com/e2e-test'.encode()).hexdigest()[:8]
    assert origin_file.parent.name == 'Origin'
    assert origin_file.parent.parent.name == expected_hash
    assert origin_file.parent.parent.parent == skill_config['vault']

    # author/date/source_url/origin_title 都齐全，description 已从原文校验里排除
    # → remaining 应为空 → 不应留下临时 issues 文件
    assert not (origin_file.parent.parent / '.fetch_issues.tmp').exists()


@requires_playwright
def test_playwright_web_e2e_writes_fetch_issues_tmp_when_incomplete(skill_config, tmp_path):
    """When origin frontmatter has real gaps (missing author/date), a temp issues file is written."""
    html = tmp_path / 'no-author.html'
    html.write_text(_TEST_HTML_NO_AUTHOR, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'https://example.com/no-author-test', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True,
        timeout=60
    )
    assert result.returncode == 0, result.stderr

    origin_path = next(
        line.split('ORIGIN_PATH:', 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith('ORIGIN_PATH:')
    )
    article_dir = Path(origin_path).parent.parent
    tmp_issues = article_dir / '.fetch_issues.tmp'
    assert tmp_issues.exists()
    text = tmp_issues.read_text(encoding='utf-8')
    assert 'author空' in text
    assert 'publish_date空' in text
    assert 'description空' not in text
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_web.py -v`
预期: FAIL（`playwright_web.py` 仍导入/调用 `record_issues`，`.fetch_issues.tmp` 断言失败）

- [ ] **Step 3: 编写最小实现**

修改 `skills/research/extract-url/scripts/playwright_web.py` 第 37 行导入：

旧：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_issues
```

新：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_fetch_issues
```

删除第 139 行：
```python
db_path = os.path.join(vault_path, 'url-index.db')
```

修改第 220-227 行「--- Validate ---」块：

旧：
```python
# --- Validate ---
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date})
if remaining:
    record_issues(url, '; '.join(remaining), db_path)
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_issues(url, '', db_path)

print(f"ORIGIN_PATH: {origin_path}")
```

新：
```python
# --- Validate ---
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date}, skip_remaining_fields={'description'})
if remaining:
    record_fetch_issues('; '.join(remaining), paths['article_dir'])
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_fetch_issues('', paths['article_dir'])

print(f"ORIGIN_PATH: {origin_path}")
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_web.py -v`
预期: PASS（6 个测试全部通过；两个 `@requires_playwright` 测试若本地无 playwright 会被跳过，不算失败）

- [ ] **Step 5: 提交**

```bash
git add skills/research/extract-url/scripts/playwright_web.py skills/research/extract-url/tests/test_playwright_web.py
git commit -m "feat(extract-url): switch playwright_web issues recording to meta.json temp file"
```

---

### Task 5: playwright_web_arxiv.py — 切换 issues 记录方式

**文件：**
- 修改: `skills/research/extract-url/scripts/playwright_web_arxiv.py`
- 修改: `skills/research/extract-url/tests/test_playwright_web_arxiv.py`

- [ ] **Step 1: 编写失败的测试**

用以下内容整体替换 `skills/research/extract-url/tests/test_playwright_web_arxiv.py`：

```python
import subprocess, os, pytest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'

try:
    from playwright.sync_api import sync_playwright as _sp  # noqa: F401
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

requires_playwright = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — run: pip install playwright && playwright install chromium"
)

_TEST_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <title>arXiv Test Article</title>
  <meta name="author" content="arXiv Author">
  <meta property="article:published_time" content="2024-06-01">
</head>
<body>
  <article>
    <h1>arXiv Test Article</h1>
    <p>First paragraph with sufficient content to be captured by the playwright_web_arxiv scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
  </article>
</body>
</html>
"""

_TEST_HTML_NO_AUTHOR = """\
<!DOCTYPE html>
<html>
<head>
  <title>arXiv No Author Article</title>
</head>
<body>
  <article>
    <h1>arXiv No Author Article</h1>
    <p>First paragraph with sufficient content to be captured by the playwright_web_arxiv scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
  </article>
</body>
</html>
"""


def test_playwright_web_arxiv_invalid_url_scheme(skill_config, tmp_path):
    """Security check rejects non-http/https URLs before reading config."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'file:///etc/passwd', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert 'Rejected URL' in result.stderr


def test_playwright_web_arxiv_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    env = {
        **os.environ,
        'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'https://arxiv.org/html/2024.01234', str(html)],
        env=env, capture_output=True, text=True
    )
    assert result.returncode != 0


def test_playwright_web_arxiv_too_few_args(skill_config):
    """Script exits non-zero when html_path argument is missing."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'https://arxiv.org/html/2024.01234'],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0


@requires_playwright
def test_playwright_web_arxiv_e2e(skill_config, tmp_path):
    """Full e2e: HTML file → ORIGIN_PATH in stdout + file saved to vault."""
    html = tmp_path / 'article.html'
    html.write_text(_TEST_HTML, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'https://arxiv.org/html/2024.06001', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True,
        timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert 'ORIGIN_PATH:' in result.stdout

    origin_path = next(
        line.split('ORIGIN_PATH:', 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith('ORIGIN_PATH:')
    )
    origin_file = Path(origin_path)
    assert origin_file.exists(), f'Origin file not found at {origin_path}'

    content = origin_file.read_text(encoding='utf-8')
    assert 'arXiv Test Article' in content
    assert 'source_url: https://arxiv.org/html/2024.06001' in content

    import hashlib
    expected_hash = hashlib.md5('https://arxiv.org/html/2024.06001'.encode()).hexdigest()[:8]
    assert origin_file.parent.name == 'Origin'
    assert origin_file.parent.parent.name == expected_hash
    assert origin_file.parent.parent.parent == skill_config['vault']

    assert not (origin_file.parent.parent / '.fetch_issues.tmp').exists()


@requires_playwright
def test_playwright_web_arxiv_e2e_writes_fetch_issues_tmp_when_incomplete(skill_config, tmp_path):
    """When origin frontmatter has real gaps (missing author/date), a temp issues file is written."""
    html = tmp_path / 'no-author.html'
    html.write_text(_TEST_HTML_NO_AUTHOR, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'https://arxiv.org/html/2024.07002', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True,
        timeout=60
    )
    assert result.returncode == 0, result.stderr

    origin_path = next(
        line.split('ORIGIN_PATH:', 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith('ORIGIN_PATH:')
    )
    article_dir = Path(origin_path).parent.parent
    tmp_issues = article_dir / '.fetch_issues.tmp'
    assert tmp_issues.exists()
    text = tmp_issues.read_text(encoding='utf-8')
    assert 'author空' in text
    assert 'publish_date空' in text
    assert 'description空' not in text
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_web_arxiv.py -v`
预期: FAIL

- [ ] **Step 3: 编写最小实现**

修改 `skills/research/extract-url/scripts/playwright_web_arxiv.py` 第 45 行导入：

旧：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_issues
```

新：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_fetch_issues
```

删除第 188 行：
```python
db_path = os.path.join(vault_path, 'url-index.db')
```

修改第 277-283 行「--- Validate ---」块：

旧：
```python
# --- Validate ---
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date})
if remaining:
    record_issues(url, '; '.join(remaining), db_path)
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_issues(url, '', db_path)

print(f"ORIGIN_PATH: {origin_path}")
```

新：
```python
# --- Validate ---
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date}, skip_remaining_fields={'description'})
if remaining:
    record_fetch_issues('; '.join(remaining), paths['article_dir'])
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_fetch_issues('', paths['article_dir'])

print(f"ORIGIN_PATH: {origin_path}")
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_web_arxiv.py -v`
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/research/extract-url/scripts/playwright_web_arxiv.py skills/research/extract-url/tests/test_playwright_web_arxiv.py
git commit -m "feat(extract-url): switch playwright_web_arxiv issues recording to meta.json temp file"
```

---

### Task 6: playwright_xcom.py — 切换 issues 记录方式

**文件：**
- 修改: `skills/research/extract-url/scripts/playwright_xcom.py`

`tests/test_playwright_xcom.py` 现有测试均不涉及 `record_issues`/db（已核实，其 e2e 路径在测试环境下总是在到达 Validate 代码前因缺少真实 Chrome cookies 而失败），无需修改测试文件；本任务只做源码替换，用现有测试回归验证不引入新故障。

- [ ] **Step 1: 确认现有测试作为回归基线**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_xcom.py -v`
预期: PASS（改动前的基线，全部通过）

- [ ] **Step 2: 编写最小实现**

修改 `skills/research/extract-url/scripts/playwright_xcom.py` 第 34 行导入：

旧：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_issues
```

新：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_fetch_issues
```

删除第 36 行：
```python
db_path = os.path.join(vault_path, 'url-index.db')
```

修改第 462-469 行「--- Validate ---」块：

旧：
```python
# --- Validate ---
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date})
if remaining:
    record_issues(url, '; '.join(remaining), db_path)
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_issues(url, '', db_path)

print(f"ORIGIN_PATH: {origin_path}")
```

新：
```python
# --- Validate ---
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date}, skip_remaining_fields={'description'})
if remaining:
    record_fetch_issues('; '.join(remaining), paths['article_dir'])
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_fetch_issues('', paths['article_dir'])

print(f"ORIGIN_PATH: {origin_path}")
```

- [ ] **Step 3: 运行测试确认仍通过**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_xcom.py -v`
预期: PASS（与 Step 1 基线一致，无新增失败）

- [ ] **Step 4: 提交**

```bash
git add skills/research/extract-url/scripts/playwright_xcom.py
git commit -m "feat(extract-url): switch playwright_xcom issues recording to meta.json temp file"
```

---

### Task 7: migrate_to_folder_structure.py — 合并迁移脚本改造

**文件：**
- 修改: `skills/research/extract-url/scripts/migrate_to_folder_structure.py`
- 修改: `skills/research/extract-url/tests/test_migrate_to_folder_structure.py`

- [ ] **Step 1: 编写失败的测试**

在 `skills/research/extract-url/tests/test_migrate_to_folder_structure.py` 顶部，把第 1 行导入：

旧：
```python
import sqlite3, sys
from pathlib import Path
```

新：
```python
import json, sqlite3, sys
from pathlib import Path
```

删除/替换下列既有测试（按函数名定位）：

1. `test_apply_plan_moves_files_strips_hash_prefix_and_rewrites_links` 内的调用从 `migrate.apply_plan(vault, plan, db_path)` 改为 `migrate.apply_plan(vault, plan)`，并删掉该函数体里不再需要的 `db_path = vault / 'url-index.db'` 行。

2. `test_apply_plan_writes_url_index_db` 整个函数删除，替换为：

```python
def test_apply_plan_then_write_meta_jsons_creates_meta_json(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/i', 'Article I', 'article-i')
    plan = migrate.build_plan(vault)

    migrate.apply_plan(vault, plan)
    written = migrate._write_meta_jsons(vault, plan, vault / 'url-index.db')

    assert written == ['https://example.com/i']
    url_hash = migrate.get_url_hash('https://example.com/i')
    meta_path = vault / url_hash / 'meta.json'
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['source_url'] == 'https://example.com/i'
    assert meta['title'] == 'article-i'


def test_write_meta_jsons_prefers_frontmatter_category_over_old_db(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/k', 'Article K', 'article-k')
    t_path = vault / 'article-k.md'
    content = t_path.read_text(encoding='utf-8')
    content = content.replace('tags: []', 'tags: []\ncategory: from-frontmatter')
    t_path.write_text(content, encoding='utf-8')

    plan = migrate.build_plan(vault)
    migrate.apply_plan(vault, plan)

    old_db = vault / 'url-index.db'
    conn = sqlite3.connect(str(old_db))
    conn.execute("CREATE TABLE url_index (source_url TEXT PRIMARY KEY, category TEXT, fetched_at TEXT, issues TEXT)")
    conn.execute("INSERT INTO url_index (source_url, category, fetched_at, issues) VALUES (?,?,?,?)",
                 ('https://example.com/k', 'from-old-db', '2020-01-01', 'old issue'))
    conn.commit()
    conn.close()

    migrate._write_meta_jsons(vault, plan, old_db)

    url_hash = migrate.get_url_hash('https://example.com/k')
    meta = json.loads((vault / url_hash / 'meta.json').read_text(encoding='utf-8'))
    assert meta['category'] == 'from-frontmatter'


def test_write_meta_jsons_falls_back_to_old_db_when_frontmatter_incomplete(tmp_path):
    vault = _make_vault(tmp_path)
    url = 'https://example.com/m'
    origin_content = (
        "---\npublish_date: 2026-01-01\nfetch_date:\nauthor: Test Author\n"
        f"source_url: {url}\norigin_title: \"Article M\"\n---\n\n# Article M\n\nBody text here.\n"
    )
    (vault / 'Origin' / 'article-m.md').write_text(origin_content, encoding='utf-8')
    translation_content = (
        "---\npublish_date: 2026-01-01\nfetch_date:\nauthor: Test Author\n"
        f"source_url: {url}\norigin_title: \"Article M\"\ntags: []\ndescription: A test article.\n---\n\n"
        "[[Origin/article-m.md]]\n\n---\n\n# Article M（译文）\n\n正文内容。\n"
    )
    (vault / 'article-m.md').write_text(translation_content, encoding='utf-8')

    plan = migrate.build_plan(vault)
    migrate.apply_plan(vault, plan)

    old_db = vault / 'url-index.db'
    conn = sqlite3.connect(str(old_db))
    conn.execute("CREATE TABLE url_index (source_url TEXT PRIMARY KEY, category TEXT, fetched_at TEXT, issues TEXT)")
    conn.execute("INSERT INTO url_index (source_url, category, fetched_at, issues) VALUES (?,?,?,?)",
                 (url, 'db-category', '2020-05-05', 'db issue'))
    conn.commit()
    conn.close()

    migrate._write_meta_jsons(vault, plan, old_db)

    url_hash = migrate.get_url_hash(url)
    meta = json.loads((vault / url_hash / 'meta.json').read_text(encoding='utf-8'))
    assert meta['category'] == 'db-category'
    assert meta['fetched_at'] == '2020-05-05'
    assert meta['issues'] == 'db issue'


def test_write_meta_jsons_handles_missing_old_db(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/n', 'Article N', 'article-n')
    plan = migrate.build_plan(vault)
    migrate.apply_plan(vault, plan)

    written = migrate._write_meta_jsons(vault, plan, vault / 'does-not-exist.db')

    assert written == ['https://example.com/n']
```

3. `test_apply_plan_is_idempotent_on_rerun` 内的两处 `migrate.apply_plan(vault, plan1, db_path)` / `migrate.apply_plan(vault, plan2, db_path)` 改为 `migrate.apply_plan(vault, plan1)` / `migrate.apply_plan(vault, plan2)`，删掉不再需要的 `db_path = vault / 'url-index.db'` 行。

4. 在文件末尾追加以下新测试（清理遗留文件 + apply-merge 生成 meta.json）：

```python
def test_cleanup_legacy_files_removes_known_names_and_sync_conflicts(tmp_path):
    vault = _make_vault(tmp_path)
    (vault / 'url-index.db').write_bytes(b'db')
    (vault / 'url_index.db').write_bytes(b'db')
    (vault / 'reading.db').write_bytes(b'db')
    (vault / 'unrelated.db').write_bytes(b'db')
    (vault / 'article.sync-conflict-20260101-ABC.md').write_text('x', encoding='utf-8')
    (vault / 'Image' / 'photo.sync-conflict-20260101-ABC.jpg').write_bytes(b'img')

    removed = migrate._cleanup_legacy_files(vault)

    assert not (vault / 'url-index.db').exists()
    assert not (vault / 'url_index.db').exists()
    assert not (vault / 'reading.db').exists()
    assert (vault / 'unrelated.db').exists()
    assert not (vault / 'article.sync-conflict-20260101-ABC.md').exists()
    assert not (vault / 'Image' / 'photo.sync-conflict-20260101-ABC.jpg').exists()
    assert len(removed) == 5


def test_apply_merge_writes_meta_json_when_both_sides_present(tmp_path):
    vault = _make_vault(tmp_path)
    url = 'https://example.com/t'
    hash_a = migrate.get_url_hash(url + '?utm_source=x')
    hash_b = migrate.get_url_hash(url)
    (vault / hash_a / 'Origin').mkdir(parents=True)
    (vault / hash_a / 'Origin' / 'article-t.md').write_text(
        ORIGIN_TMPL.format(url=url + '?utm_source=x', title='Article T', img_line=''), encoding='utf-8'
    )
    (vault / hash_b / 'Translation').mkdir(parents=True)
    (vault / hash_b / 'Translation' / 'article-t.md').write_text(
        TRANSLATION_TMPL.format(url=url, title='Article T', wikilink='[[Origin/article-t.md]]', img_line=''),
        encoding='utf-8'
    )

    migrate.apply_merge(vault, keep_hash=hash_a, drop_hash=hash_b)

    meta_path = vault / hash_a / 'meta.json'
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['source_url'] == url
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_migrate_to_folder_structure.py -v`
预期: FAIL（`apply_plan` 签名不匹配，`_write_meta_jsons`/`_cleanup_legacy_files` 不存在）

- [ ] **Step 3: 编写最小实现**

修改 `skills/research/extract-url/scripts/migrate_to_folder_structure.py` 第 14 行导入，加 `json`：

旧：
```python
import argparse, os, re, shutil, sqlite3, sys, tarfile, time
```

新：
```python
import argparse, json, os, re, shutil, sqlite3, sys, tarfile, time
```

第 216-262 行（`_rebuild_db` + `apply_plan`）整体替换：

旧：
```python
def _rebuild_db(db_path, plan):
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS url_index (
            source_url   TEXT PRIMARY KEY,
            title        TEXT,
            fetched_at   TEXT,
            issues       TEXT,
            category     TEXT,
            origin_path  TEXT,
            article_path TEXT
        )
    """)
    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    for entry in plan['complete'] + plan['partial']:
        if 'new_origin_path' not in entry and 'new_translation_path' not in entry:
            continue
        origin_e = entry.get('origin')
        translation_e = entry.get('translation')
        fm = (translation_e or origin_e)['frontmatter']
        title_path = entry.get('new_translation_path') or entry.get('new_origin_path')
        conn.execute(
            "INSERT OR REPLACE INTO url_index "
            "(source_url, title, fetched_at, issues, category, origin_path, article_path) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                entry['source_url'], Path(title_path).stem, fetch_date, '',
                fm.get('category') or '',
                entry.get('new_origin_path') or '',
                entry.get('new_translation_path') or '',
            )
        )
    conn.commit()
    conn.close()


def apply_plan(vault_path, plan, db_path):
    moved, failed = [], []
    for entry in plan['complete'] + plan['partial']:
        try:
            _migrate_entry(vault_path, entry)
            moved.append(entry['source_url'])
        except Exception as exc:
            failed.append({'source_url': entry['source_url'], 'error': str(exc)})

    _rebuild_db(db_path, plan)
    return {'moved': moved, 'failed': failed}
```

新：
```python
def apply_plan(vault_path, plan):
    moved, failed = [], []
    for entry in plan['complete'] + plan['partial']:
        try:
            _migrate_entry(vault_path, entry)
            moved.append(entry['source_url'])
        except Exception as exc:
            failed.append({'source_url': entry['source_url'], 'error': str(exc)})
    return {'moved': moved, 'failed': failed}


def _read_old_index_rows(old_db_path):
    """Read legacy url_index rows keyed by source_url, for use as a fallback data source."""
    if not old_db_path or not Path(old_db_path).exists():
        return {}
    conn = sqlite3.connect(str(old_db_path))
    conn.row_factory = sqlite3.Row
    try:
        cols = {r[1] for r in conn.execute('PRAGMA table_info(url_index)')}
        if 'source_url' not in cols:
            return {}
        return {r['source_url']: dict(r) for r in conn.execute('SELECT * FROM url_index')}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def _write_meta_jsons(vault_path, plan, old_db_path):
    """Write <hash8>/meta.json for every migrated entry. Frontmatter is the primary
    data source; the legacy url_index row (if any) fills in fields the frontmatter
    lacks."""
    old_rows = _read_old_index_rows(old_db_path)
    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    written = []
    for entry in plan['complete'] + plan['partial']:
        if 'new_origin_path' not in entry and 'new_translation_path' not in entry:
            continue
        origin_e = entry.get('origin')
        translation_e = entry.get('translation')
        fm = (translation_e or origin_e)['frontmatter']
        old_row = old_rows.get(entry['source_url'], {})
        title_path = entry.get('new_translation_path') or entry.get('new_origin_path')

        meta = {
            'source_url': entry['source_url'],
            'title': Path(title_path).stem,
            'category': fm.get('category') or old_row.get('category') or '',
            'fetched_at': fm.get('fetch_date') or old_row.get('fetched_at') or fetch_date,
            'issues': old_row.get('issues') or '',
        }
        article_dir = Path(vault_path) / entry['url_hash']
        (article_dir / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        written.append(entry['source_url'])
    return written


_LEGACY_DB_NAMES = [
    'url-index.db', 'url_index.db', 'reading.db', 'reading_index.db',
    '.fetch_history.db', 'articles.db', 'cursor-articles.db', 'article_fetch_log.sqlite',
]


def _cleanup_legacy_files(vault_path):
    """Remove the old centralized index db and any leftover iCloud sync-conflict files."""
    vault_path = Path(vault_path)
    removed = []
    for name in _LEGACY_DB_NAMES:
        p = vault_path / name
        if p.exists():
            p.unlink()
            removed.append(str(p))
    for p in list(vault_path.rglob('*sync-conflict*')):
        if p.is_file():
            p.unlink()
            removed.append(str(p))
    return removed
```

第 337-360 行 `apply_merge` 函数体末尾追加 meta.json 生成：

旧：
```python
def apply_merge(vault_path, keep_hash, drop_hash):
    if keep_hash == drop_hash:
        raise ValueError('keep_hash and drop_hash must be different')

    vault_path = Path(vault_path)
    keep_dir = vault_path / keep_hash
    drop_dir = vault_path / drop_hash

    for side in ('Origin', 'Translation', 'Image'):
        src_dir = drop_dir / side
        if not src_dir.exists():
            continue
        _move_dir_contents(src_dir, keep_dir / side)

    shutil.rmtree(drop_dir, ignore_errors=True)

    translation_files = list((keep_dir / 'Translation').glob('*.md')) if (keep_dir / 'Translation').exists() else []
    origin_files = list((keep_dir / 'Origin').glob('*.md')) if (keep_dir / 'Origin').exists() else []
    if translation_files and origin_files:
        t_path = translation_files[0]
        content = t_path.read_text(encoding='utf-8')
        content = _rewrite_wikilink(content, keep_hash, origin_files[0].name)
        t_path.write_text(content, encoding='utf-8')
```

新：
```python
def apply_merge(vault_path, keep_hash, drop_hash):
    if keep_hash == drop_hash:
        raise ValueError('keep_hash and drop_hash must be different')

    vault_path = Path(vault_path)
    keep_dir = vault_path / keep_hash
    drop_dir = vault_path / drop_hash

    for side in ('Origin', 'Translation', 'Image'):
        src_dir = drop_dir / side
        if not src_dir.exists():
            continue
        _move_dir_contents(src_dir, keep_dir / side)

    shutil.rmtree(drop_dir, ignore_errors=True)

    translation_files = list((keep_dir / 'Translation').glob('*.md')) if (keep_dir / 'Translation').exists() else []
    origin_files = list((keep_dir / 'Origin').glob('*.md')) if (keep_dir / 'Origin').exists() else []
    if translation_files and origin_files:
        t_path = translation_files[0]
        content = t_path.read_text(encoding='utf-8')
        content = _rewrite_wikilink(content, keep_hash, origin_files[0].name)
        t_path.write_text(content, encoding='utf-8')

        fm = _read_frontmatter(t_path)
        meta = {
            'source_url': fm.get('source_url', ''),
            'title': t_path.stem,
            'category': fm.get('category') or '',
            'fetched_at': fm.get('fetch_date') or datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d'),
            'issues': '',
        }
        (keep_dir / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
```

第 370-409 行 `main()` 整体替换：

旧：
```python
def main():
    parser = argparse.ArgumentParser(description='Migrate extract-url Vault to per-article folder structure')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('plan')
    p_apply = sub.add_parser('apply')
    p_apply.add_argument('--no-backup', action='store_true')
    sub.add_parser('find-merges')
    p_merge = sub.add_parser('apply-merge')
    p_merge.add_argument('--keep', required=True)
    p_merge.add_argument('--drop', required=True)
    p_merge.add_argument('--no-backup', action='store_true')

    args = parser.parse_args()
    vault_path = get_vault_path()
    db_path = os.path.join(vault_path, 'url-index.db')

    if args.command == 'plan':
        _print_plan_summary(build_plan(vault_path))
    elif args.command == 'apply':
        plan = build_plan(vault_path)
        _print_plan_summary(plan)
        if not args.no_backup:
            print(f'备份已创建：{_backup_vault(vault_path)}')
        result = apply_plan(vault_path, plan, db_path)
        print(f"迁移完成：{len(result['moved'])} 篇成功，{len(result['failed'])} 篇失败")
        for f in result['failed']:
            print(f"  失败：{f['source_url']} - {f['error']}")
    elif args.command == 'find-merges':
        candidates = find_merge_candidates(vault_path)
        if not candidates:
            print('未发现合并候选')
        for c in candidates:
            print(f"候选：{c['a']['hash']} ({c['a']['side']}) <-> {c['b']['hash']} ({c['b']['side']})")
            print(f"  URL A: {c['a']['source_url']}")
            print(f"  URL B: {c['b']['source_url']}")
    elif args.command == 'apply-merge':
        if not args.no_backup:
            print(f'备份已创建：{_backup_vault(vault_path)}')
        apply_merge(vault_path, args.keep, args.drop)
        print(f'已合并 {args.drop} → {args.keep}')
```

新：
```python
def main():
    parser = argparse.ArgumentParser(description='Migrate extract-url Vault to per-article folder structure')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('plan')
    p_apply = sub.add_parser('apply')
    p_apply.add_argument('--no-backup', action='store_true')
    sub.add_parser('find-merges')
    p_merge = sub.add_parser('apply-merge')
    p_merge.add_argument('--keep', required=True)
    p_merge.add_argument('--drop', required=True)
    p_merge.add_argument('--no-backup', action='store_true')

    args = parser.parse_args()
    vault_path = get_vault_path()
    old_db_path = os.path.join(vault_path, 'url-index.db')

    if args.command == 'plan':
        _print_plan_summary(build_plan(vault_path))
    elif args.command == 'apply':
        plan = build_plan(vault_path)
        _print_plan_summary(plan)
        if not args.no_backup:
            print(f'备份已创建：{_backup_vault(vault_path)}')
        result = apply_plan(vault_path, plan)
        written = _write_meta_jsons(vault_path, plan, old_db_path)
        removed = _cleanup_legacy_files(vault_path)
        print(f"迁移完成：{len(result['moved'])} 篇成功，{len(result['failed'])} 篇失败")
        for f in result['failed']:
            print(f"  失败：{f['source_url']} - {f['error']}")
        print(f"meta.json 写入：{len(written)} 篇")
        print(f"清理遗留文件：{len(removed)} 个")
        for r in removed:
            print(f"  已删除：{r}")
    elif args.command == 'find-merges':
        candidates = find_merge_candidates(vault_path)
        if not candidates:
            print('未发现合并候选')
        for c in candidates:
            print(f"候选：{c['a']['hash']} ({c['a']['side']}) <-> {c['b']['hash']} ({c['b']['side']})")
            print(f"  URL A: {c['a']['source_url']}")
            print(f"  URL B: {c['b']['source_url']}")
    elif args.command == 'apply-merge':
        if not args.no_backup:
            print(f'备份已创建：{_backup_vault(vault_path)}')
        apply_merge(vault_path, args.keep, args.drop)
        print(f'已合并 {args.drop} → {args.keep}')
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_migrate_to_folder_structure.py -v`
预期: PASS（全部测试通过，包括新增的 `_write_meta_jsons`/`_cleanup_legacy_files`/`apply_merge` meta.json 测试）

- [ ] **Step 5: 提交**

```bash
git add skills/research/extract-url/scripts/migrate_to_folder_structure.py skills/research/extract-url/tests/test_migrate_to_folder_structure.py
git commit -m "feat(extract-url): merge folder-structure migration with meta.json generation and legacy cleanup"
```

---

### Task 8: SKILL.md + 两份 subagent 提示词 — 文档更新

**文件：**
- 修改: `skills/research/extract-url/SKILL.md`
- 修改: `skills/research/extract-url/references/subagent1-fetch-prompt.md`
- 修改: `skills/research/extract-url/references/subagent2-tag-translate-prompt.md`
- 修改: `skills/research/extract-url/tests/test_subagent2_prompt.py`
- 测试: `skills/research/extract-url/tests/test_subagent1_prompt.py`（新建）

- [ ] **Step 1: 编写失败的测试**

创建 `skills/research/extract-url/tests/test_subagent1_prompt.py`：

```python
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
```

在 `skills/research/extract-url/tests/test_subagent2_prompt.py` 末尾追加：

```python
def test_subagent2_prompt_writes_meta_json_not_sqlite():
    content = PROMPT_PATH.read_text(encoding='utf-8')
    assert 'meta.json' in content
    assert 'sqlite' not in content.lower()
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_subagent1_prompt.py tests/test_subagent2_prompt.py -v`
预期: FAIL（两份提示词仍含「SQLite」字样）

- [ ] **Step 3: 编写最小实现**

`references/subagent1-fetch-prompt.md` 第 13 行：

旧：
```
1. 查 SQLite 去重（通过 env var 传参，避免 URL 中特殊字符破坏 Python 语法）：
```

新：
```
1. 查 meta.json 去重（通过 env var 传参，避免 URL 中特殊字符破坏 Python 语法）：
```

`references/subagent2-tag-translate-prompt.md` 第 74 行：

旧：
```
7. 执行校验并写入 SQLite 索引：
```

新：
```
7. 执行校验并写入 meta.json：
```

`SKILL.md` 第 3 行版本号：

旧：
```
version: "2.5.0"
```

新：
```
version: "2.6.0"
```

`SKILL.md` 第 75-84 行路径变量表：

旧：
```
Config:      ~/.hskill/url-extract/config.json
Base:        VAULT_PATH   (脚本从 config.json 读取)
ArticleDir:  VAULT_PATH/<hash8>   (hash8 = md5(source_url)[:8]，由 scripts/config.py 的 get_article_paths() 统一计算)
Origin:      ArticleDir/Origin
Translation: ArticleDir/Translation
Image:       ArticleDir/Image
DB:          VAULT_PATH/url-index.db
SkillDir:    平台固定值（见平台补丁）
```

新：
```
Config:      ~/.hskill/url-extract/config.json
Base:        VAULT_PATH   (脚本从 config.json 读取)
ArticleDir:  VAULT_PATH/<hash8>   (hash8 = md5(source_url)[:8]，由 scripts/config.py 的 get_article_paths() 统一计算)
Origin:      ArticleDir/Origin
Translation: ArticleDir/Translation
Image:       ArticleDir/Image
Meta:        ArticleDir/meta.json
SkillDir:    平台固定值（见平台补丁）
```

`SKILL.md` 第 88-102 行「## URL 去重索引（SQLite）」整节：

旧：
```markdown
## URL 去重索引（SQLite）

**数据库路径：** `VAULT_PATH/url-index.db`

```sql
CREATE TABLE IF NOT EXISTS url_index (
    source_url   TEXT PRIMARY KEY,
    title        TEXT,
    fetched_at   TEXT,
    issues       TEXT,
    category     TEXT,
    origin_path  TEXT,
    article_path TEXT
);
```
```

新：
```markdown
## URL 去重索引（meta.json）

**索引路径：** `VAULT_PATH/<hash8>/meta.json`（`hash8` 由 URL 派生，去重时直接检查该路径是否存在，无需数据库）

```json
{
  "source_url": "https://example.com/article",
  "title": "文章标题",
  "category": "分类",
  "fetched_at": "2026-07-17",
  "issues": ""
}
```
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd skills/research/extract-url && python3 -m pytest tests/test_subagent1_prompt.py tests/test_subagent2_prompt.py -v`
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/research/extract-url/SKILL.md skills/research/extract-url/references/subagent1-fetch-prompt.md skills/research/extract-url/references/subagent2-tag-translate-prompt.md skills/research/extract-url/tests/test_subagent1_prompt.py skills/research/extract-url/tests/test_subagent2_prompt.py
git commit -m "docs(extract-url): update SKILL.md and subagent prompts for meta.json index"
```

---

### Task 9: 真实 Vault 数据执行合并迁移（人工操作，需用户在场）

不涉及代码改动，是对 `/Users/harveyzhang96/Vault/Product/Reading/` 真实数据执行 Task 1-7 已实现并测试通过的合并迁移脚本。**执行前必须让用户在场完成第 1、2、6 步。**

- [ ] **Step 1: 关闭 Obsidian**

用户手动关闭 Obsidian 应用，避免迁移过程中的文件锁定/索引冲突。

- [ ] **Step 2: 暂停 iCloud 同步**

用户手动暂停 iCloud Drive 同步（系统设置 → Apple ID → iCloud → iCloud Drive，或菜单栏 iCloud 图标），避免迁移中的文件移动与云同步产生新的 `.sync-conflict-*` 冲突。

- [ ] **Step 3: 预览迁移计划**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/skills/research/extract-url/scripts
python3 migrate_to_folder_structure.py plan
```

核对输出的「完整配对」「部分完成」「异常」「孤儿图片」数量是否与调研阶段观察到的规模吻合（Origin 365、Image 1937、根目录译文 288）。若「异常」数量远超预期，先排查再继续。

- [ ] **Step 4: 人工确认后执行迁移**

在用户明确同意后执行：

```bash
python3 migrate_to_folder_structure.py apply
```

该命令会依次：打印计划摘要 → 创建 `.tar.gz` 备份（位于 `Reading/` 同级目录）→ 移动文件到 `<hash8>/{Origin,Translation,Image}/` 并改写双链/图片引用 → 为每篇成功迁移的文章写入 `<hash8>/meta.json`（frontmatter 为主、旧 `url-index.db` 补充缺失字段）→ 删除 `url-index.db` 及其余历史遗留 db 文件、8 个已知的 `.sync-conflict-*` 冲突文件 → 打印迁移/清理结果统计。

- [ ] **Step 5: 校验迁移结果**

```bash
find /Users/harveyzhang96/Vault/Product/Reading -maxdepth 1 -type d -regex '.*/[0-9a-f]\{8\}$' | wc -l
ls /Users/harveyzhang96/Vault/Product/Reading/url-index.db 2>/dev/null && echo "STILL EXISTS (unexpected)" || echo "removed as expected"
python3 -c "
import json, os
from pathlib import Path
vault = Path('/Users/harveyzhang96/Vault/Product/Reading')
sample = next(vault.glob('*/meta.json'))
print(sample)
print(json.loads(sample.read_text(encoding='utf-8')))
"
```

抽查若干篇文章：在 Obsidian 中重新打开 Vault，确认双链能正常跳转到对应 `<hash8>/Origin/` 文件、图片正常显示。用 `python3 dedup_check.py`（设置 `CHECK_URL` 为已迁移文章的 `source_url`）确认返回 `ALREADY_FETCHED`。

- [ ] **Step 6: 恢复 iCloud 同步**

用户手动恢复 iCloud Drive 同步。若 Step 5 校验发现问题，先处理完再恢复同步，避免带着问题状态同步到其他设备。

- [ ] **Step 7: 若合并候选清单非空，人工确认合并**

```bash
python3 migrate_to_folder_structure.py find-merges
```

若输出非空，逐条与用户确认候选是否应合并（同一 URL 因归一化差异被分到两个 hash8 目录的情况），确认后执行：

```bash
python3 migrate_to_folder_structure.py apply-merge --keep <hash8> --drop <hash8>
```

---

## 执行完成后（不属于本计划任务，仅作提示）

全部 9 个 Task 完成、合并到目标分支后，运行 `/publish-skill extract-url` 更新 `skills-index.json` 里的 `contentHash`/`contentVersion`（沿用上次存储结构重构时的流程，不在本计划里手动编辑该文件）。
