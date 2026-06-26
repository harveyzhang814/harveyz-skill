# extract-url Script Tests 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 extract-url skill 的四个 Python 脚本补充单元测试和 e2e 测试，并通过 `HSKILL_EXTRACT_URL_CONFIG` 环境变量覆盖机制让 e2e 测试无需污染用户真实 config。

**Architecture:** 在 `config.py` 加一行 env var 覆盖逻辑（`HSKILL_EXTRACT_URL_CONFIG` → 覆盖 CONFIG_PATH）；所有 e2e 测试通过 subprocess 调用脚本，传入指向 `tmp_path` 的 config.json，不触碰 `~/.hskill`；`conftest.py` 提供 `skill_config`（config + vault + env）和 `url_index_db`（建表）和 `valid_article_files`（创建测试文章）三个共享 fixture。

**Tech Stack:** Python 3, pytest, subprocess, sqlite3, Playwright（playwright_web e2e 需要）

## Global Constraints

- 测试文件全部放在 `skills/research/extract-url/tests/` 下
- e2e 测试通过 subprocess 调用脚本（完整进程隔离），不做 import-level mock
- 不触碰 `~/.hskill/url-extract/config.json`（用 HSKILL_EXTRACT_URL_CONFIG 覆盖）
- stdout 格式断言：`ALREADY_FETCHED`、`OK`、`ORIGIN_PATH:` 精确匹配
- 需要 Playwright 的测试加 `@requires_playwright` 跳过标记
- 回归测试命名含 `_no_X_env_needed`：验证移除的 env var 确实不再需要
- 每个脚本的测试文件独立，不跨文件导入
- 运行命令：`cd skills/research/extract-url && python -m pytest tests/ -v`

---

## File Structure

**修改：**
- `skills/research/extract-url/scripts/config.py` — 加 `HSKILL_EXTRACT_URL_CONFIG` env var 覆盖（2 行改动）
- `skills/research/extract-url/tests/conftest.py` — 加 `SCRIPTS_DIR` 常量 + 3 个 fixture
- `skills/research/extract-url/tests/test_config.py` — 加 1 个 subprocess 测试验证 env var 覆盖

**新增：**
- `skills/research/extract-url/tests/test_dedup_check.py` — 5 个测试
- `skills/research/extract-url/tests/test_validate_article.py` — 5 个测试
- `skills/research/extract-url/tests/test_playwright_web.py` — 4 个测试（1 个需 Playwright）
- `skills/research/extract-url/tests/test_playwright_xcom.py` — 3 个测试

---

### Task 1: config.py env var 覆盖 + test_config.py 验证（TDD）

**Files:**
- Modify: `skills/research/extract-url/scripts/config.py:1-9`
- Modify: `skills/research/extract-url/tests/test_config.py`

**Interfaces:**
- Produces: 当 `HSKILL_EXTRACT_URL_CONFIG=/path/to/config.json` 时，`CONFIG_PATH` 指向该路径

- [ ] **Step 1: 写失败测试，追加到 test_config.py 末尾**

  在 test_config.py 顶部已有 `import json, pytest` 和 `from unittest.mock import patch`，在文件末尾追加：

  ```python
  import subprocess, os
  from pathlib import Path as _Path
  _SCRIPTS_DIR = _Path(__file__).parent.parent / 'scripts'

  def test_config_path_env_override(tmp_path):
      cfg = tmp_path / 'custom.json'
      cfg.write_text(json.dumps({'VAULT_PATH': '/env/vault', 'CHROME_PROFILE': '/p'}))
      result = subprocess.run(
          ['python3', '-c', 'import config; print(config.get_vault_path())'],
          env={**os.environ, 'HSKILL_EXTRACT_URL_CONFIG': str(cfg)},
          capture_output=True, text=True,
          cwd=str(_SCRIPTS_DIR)
      )
      assert result.returncode == 0, result.stderr
      assert '/env/vault' in result.stdout.strip()
  ```

- [ ] **Step 2: 运行确认测试失败**

  ```bash
  cd skills/research/extract-url
  python -m pytest tests/test_config.py::test_config_path_env_override -v
  ```
  Expected: FAIL — `/env/vault` not in output（脚本忽略了 env var，读的还是真实 config 或不存在的默认 config）

- [ ] **Step 3: 修改 scripts/config.py — 加 env var 覆盖**

  将文件头部从：
  ```python
  import json
  from pathlib import Path

  CONFIG_PATH = Path.home() / '.hskill' / 'url-extract' / 'config.json'
  ```
  改为：
  ```python
  import json, os
  from pathlib import Path

  _env_cfg = os.environ.get('HSKILL_EXTRACT_URL_CONFIG')
  CONFIG_PATH = Path(_env_cfg) if _env_cfg else Path.home() / '.hskill' / 'url-extract' / 'config.json'
  ```
  其余函数完全不变。

- [ ] **Step 4: 运行确认 8 个测试全部通过**

  ```bash
  python -m pytest tests/test_config.py -v
  ```
  Expected: 8 PASSED（原 7 个 + 新 1 个）

- [ ] **Step 5: Commit**

  ```bash
  git add skills/research/extract-url/scripts/config.py skills/research/extract-url/tests/test_config.py
  git commit -m "test(extract-url): add HSKILL_EXTRACT_URL_CONFIG env override + test"
  ```

---

### Task 2: conftest.py fixtures + test_dedup_check.py

**Files:**
- Modify: `skills/research/extract-url/tests/conftest.py`
- Create: `skills/research/extract-url/tests/test_dedup_check.py`

**Interfaces:**
- Produces: `skill_config` fixture → `{'config_path', 'vault', 'env', 'tmp'}` dict
- Produces: `url_index_db` fixture → `Path` 指向已建表的 url-index.db
- Produces: `valid_article_files` fixture → `{'origin', 'article', 'url'}` dict（供 Task 3 使用）

- [ ] **Step 1: 完整替换 conftest.py**

  ```python
  import json, os, sqlite3, sys
  from pathlib import Path

  import pytest

  sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

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
  def url_index_db(skill_config):
      """Create url_index table in vault's SQLite DB; return db Path."""
      db_path = skill_config['vault'] / 'url-index.db'
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
      conn.commit()
      conn.close()
      return db_path


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
  def valid_article_files(skill_config, url_index_db):
      """Create origin + translated article files with valid frontmatter."""
      url = 'https://example.com/test-article'
      content = _ARTICLE_CONTENT.format(url=url)
      origin = skill_config['vault'] / 'Origin' / 'test-article.md'
      article = skill_config['vault'] / 'test-article.md'
      origin.write_text(content, encoding='utf-8')
      article.write_text(content, encoding='utf-8')
      return {'origin': origin, 'article': article, 'url': url}
  ```

- [ ] **Step 2: 创建 tests/test_dedup_check.py**

  ```python
  import sqlite3, subprocess, os
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


  def test_dedup_check_already_fetched(skill_config, url_index_db):
      """URL already in DB returns ALREADY_FETCHED."""
      url = 'https://example.com/existing'
      conn = sqlite3.connect(str(url_index_db))
      conn.execute("INSERT INTO url_index (source_url) VALUES (?)", (url,))
      conn.commit()
      conn.close()

      result = subprocess.run(
          ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
          env={**skill_config['env'], 'CHECK_URL': url},
          capture_output=True, text=True
      )
      assert result.returncode == 0, result.stderr
      assert result.stdout.strip() == 'ALREADY_FETCHED'


  def test_dedup_check_creates_db_file(skill_config):
      """Script creates url-index.db if it does not yet exist."""
      db_path = skill_config['vault'] / 'url-index.db'
      assert not db_path.exists()

      subprocess.run(
          ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
          env={**skill_config['env'], 'CHECK_URL': 'https://example.com/creates-db'},
          capture_output=True, text=True
      )
      assert db_path.exists()


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


  def test_dedup_check_no_db_path_env_needed(skill_config):
      """Regression: DB_PATH env var must NOT be required after refactor."""
      env = skill_config['env'].copy()
      env.pop('DB_PATH', None)
      env['CHECK_URL'] = 'https://example.com/no-db-path-test'

      result = subprocess.run(
          ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
          env=env, capture_output=True, text=True
      )
      assert result.returncode == 0, result.stderr
      assert result.stdout.strip() in ('OK', 'ALREADY_FETCHED')
  ```

- [ ] **Step 3: 运行确认 5 个测试全部通过**

  ```bash
  cd skills/research/extract-url
  python -m pytest tests/test_dedup_check.py -v
  ```
  Expected: 5 PASSED

- [ ] **Step 4: Commit**

  ```bash
  git add skills/research/extract-url/tests/conftest.py skills/research/extract-url/tests/test_dedup_check.py
  git commit -m "test(extract-url): add dedup_check e2e tests + shared fixtures"
  ```

---

### Task 3: test_validate_article.py

**Files:**
- Create: `skills/research/extract-url/tests/test_validate_article.py`

**Interfaces:**
- Consumes: `skill_config`, `url_index_db`, `valid_article_files` fixtures（来自 Task 2 的 conftest.py）

- [ ] **Step 1: 创建 tests/test_validate_article.py**

  ```python
  import sqlite3, subprocess, os
  from pathlib import Path

  SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


  def test_validate_article_success(skill_config, valid_article_files):
      """Valid article exits 0 and writes URL to SQLite."""
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

      db_path = skill_config['vault'] / 'url-index.db'
      conn = sqlite3.connect(str(db_path))
      row = conn.execute(
          'SELECT source_url FROM url_index WHERE source_url=?',
          (valid_article_files['url'],)
      ).fetchone()
      conn.close()
      assert row is not None, 'URL should be written to SQLite after successful validation'


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


  def test_validate_article_missing_article_path(skill_config, url_index_db):
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
  ```

- [ ] **Step 2: 运行确认 5 个测试全部通过**

  ```bash
  python -m pytest tests/test_validate_article.py -v
  ```
  Expected: 5 PASSED

  如果 `test_validate_article_success` 失败并报 frontmatter 错误，检查 `references/article_utils.py` 中 `repair_frontmatter` 的 required 字段（`publish_date`、`author`、`source_url`、`origin_title`、`description`），确保 `_ARTICLE_CONTENT` 模板包含所有必填字段。

- [ ] **Step 3: Commit**

  ```bash
  git add skills/research/extract-url/tests/test_validate_article.py
  git commit -m "test(extract-url): add validate_article e2e tests + regression tests"
  ```

---

### Task 4: test_playwright_web.py

**Files:**
- Create: `skills/research/extract-url/tests/test_playwright_web.py`

**Interfaces:**
- Consumes: `skill_config` fixture（来自 Task 2 的 conftest.py）

- [ ] **Step 1: 创建 tests/test_playwright_web.py**

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
  ```

- [ ] **Step 2: 运行确认测试通过**

  ```bash
  python -m pytest tests/test_playwright_web.py -v
  ```
  Expected（playwright 未安装时）: 3 PASSED, 1 SKIPPED
  Expected（playwright 已安装时）: 4 PASSED

  如果 `test_playwright_web_e2e` 失败并报 `playwright._impl._errors.Error: Executable doesn't exist`：
  ```bash
  python -m playwright install chromium
  ```
  然后重新运行。

- [ ] **Step 3: Commit**

  ```bash
  git add skills/research/extract-url/tests/test_playwright_web.py
  git commit -m "test(extract-url): add playwright_web e2e + error-path tests"
  ```

---

### Task 5: test_playwright_xcom.py

**Files:**
- Create: `skills/research/extract-url/tests/test_playwright_xcom.py`

**Interfaces:**
- Consumes: `skill_config` fixture（来自 Task 2 的 conftest.py）
- 注意：playwright_xcom 需要真实 X.com 登录态，happy path 不在自动化范围内

- [ ] **Step 1: 创建 tests/test_playwright_xcom.py**

  ```python
  import subprocess, os
  from pathlib import Path

  SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


  def test_playwright_xcom_invalid_scheme(skill_config):
      """Security check rejects non-http/https URLs before reading config."""
      result = subprocess.run(
          ['python3', str(SCRIPTS_DIR / 'playwright_xcom.py'),
           'javascript:alert(1)'],
          env=skill_config['env'],
          capture_output=True, text=True
      )
      assert result.returncode != 0
      assert 'Rejected URL' in result.stderr


  def test_playwright_xcom_missing_config(tmp_path):
      """Clear error when config.json does not exist."""
      env = {
          **os.environ,
          'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
          'PATH': os.environ.get('PATH', ''),
      }
      result = subprocess.run(
          ['python3', str(SCRIPTS_DIR / 'playwright_xcom.py'),
           'https://x.com/user/status/123456789'],
          env=env, capture_output=True, text=True
      )
      assert result.returncode != 0


  def test_playwright_xcom_no_args():
      """Script exits non-zero when URL argument is missing."""
      result = subprocess.run(
          ['python3', str(SCRIPTS_DIR / 'playwright_xcom.py')],
          env={**os.environ, 'PATH': os.environ.get('PATH', '')},
          capture_output=True, text=True
      )
      assert result.returncode != 0


  def test_playwright_xcom_only_one_arg_needed(skill_config):
      """Regression: script accepts single URL arg (old code needed 4 args).

      Verifies IndexError on argv[2] is NOT raised — failure mode shifts
      from arg-count error to config/network, not to missing argument.
      With valid config but missing Cookies file, error is at pycookiecheat level.
      """
      env = {
          **skill_config['env'],
          'PATH': os.environ.get('PATH', ''),
      }
      result = subprocess.run(
          ['python3', str(SCRIPTS_DIR / 'playwright_xcom.py'),
           'https://x.com/user/status/123456789'],
          env=env, capture_output=True, text=True,
          timeout=10
      )
      # Should fail at Cookies file level (pycookiecheat / chrome profile missing),
      # NOT at argument-count level (IndexError on argv[2]).
      # Either way, returncode != 0 — but stderr must NOT contain "IndexError"
      assert 'IndexError' not in result.stderr, \
          'Should not fail on argument count — old 4-arg interface was removed'
  ```

- [ ] **Step 2: 运行确认测试通过**

  ```bash
  python -m pytest tests/test_playwright_xcom.py -v
  ```
  Expected: 4 PASSED

  如果 `test_playwright_xcom_only_one_arg_needed` 超时（X.com 实际发了网络请求），减短 timeout 或改用一个肯定不存在的 fake URL scheme 更安全的测试 URL。

- [ ] **Step 3: 运行全套测试确认没有回归**

  ```bash
  python -m pytest tests/ -v
  ```
  Expected: 原 7 个 config 测试 + 新 17-18 个 = 24-25 PASSED（视 playwright 是否安装）

- [ ] **Step 4: Commit**

  ```bash
  git add skills/research/extract-url/tests/test_playwright_xcom.py
  git commit -m "test(extract-url): add playwright_xcom error-path + regression tests"
  ```

---

## Self-Review

**Spec coverage：**
- config.py env var 覆盖 ✅ Task 1
- HSKILL_EXTRACT_URL_CONFIG 在 subprocess e2e 中生效 ✅ Task 1
- dedup_check：OK / ALREADY_FETCHED / missing config / creates DB / no DB_PATH regression ✅ Task 2
- validate_article：success + SQLite write / no ARTICLE_DB regression / no ARTICLE_SKILL_DIR regression / missing file / missing config ✅ Task 3
- playwright_web：invalid scheme / missing config / too few args / e2e ✅ Task 4
- playwright_xcom：invalid scheme / missing config / no args / only 1 arg regression ✅ Task 5

**Placeholder 扫描：** 无 TBD / TODO / vague step，所有测试含完整代码。

**一致性：**
- `SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'` 在每个测试文件中独立定义（不跨文件导入）
- `skill_config['env']` 在所有测试中统一用于 subprocess env 注入
- `HSKILL_EXTRACT_URL_CONFIG` 拼写一致：config.py、conftest.py、各测试文件完全相同
- `test_playwright_xcom_missing_config` 中的 URL `https://x.com/user/status/123456789` 通过 URL scheme 检查（scheme=https, netloc 非空），可到达 config 读取阶段再失败
