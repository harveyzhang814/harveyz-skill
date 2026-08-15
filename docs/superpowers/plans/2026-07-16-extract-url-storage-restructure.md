# extract-url 存储结构改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 extract-url skill 的产物从"扁平共享目录（Vault 根/Origin/Image）"改造成"文章专属文件夹（`<hash8>/Origin,Translation,Image`）"，路径计算集中到 `scripts/config.py`，并提供迁移脚本把存量数据搬进新结构。

**Architecture:** 新增 `config.get_url_hash()` / `config.get_article_paths()` 作为路径计算的唯一来源，三个 playwright 抓取脚本和 Subagent 2 翻译 prompt 都改用它；新增独立的 `scripts/migrate_to_folder_structure.py` 处理存量数据搬迁（含两阶段：flat→folder 迁移，以及归一化 URL 合并候选检测）。

**Tech Stack:** Python 3、pytest、SQLite（`sqlite3` 标准库）、PyYAML。

## Global Constraints

- 最小改动原则：不修改 `dedup_check.py` / `count_article_stats.py` / `validate_article.py` / `tests/conftest.py`（已核实它们只透传路径参数，不关心路径格式，改动会引入不必要风险）
- 不清理 `url-index.db` 里未使用的 `urls`/`articles` 遗留表（out of scope，见 spec）
- 新代码风格与现有脚本保持一致：不引入 dataclass，函数签名沿用 `config.py` 已有的 `-> str` / `-> dict` 类型注解风格，其余脚本不加类型注解
- 图片文件名去掉 hash 前缀（如 `img_1.jpg` 而非 `abcd1234_img_1.jpg`），因为文件夹已经按 hash 分区
- 双链格式固定为 `[[<hash8>/Origin/<origin_title>.md]]`（带 `.md` 后缀，已核实是 Obsidian 现有生效写法）
- 图片引用固定为 `![](../Image/<filename>)`（Origin/Translation 都在 hash 文件夹下一层，相对路径一致）
- 迁移脚本默认 dry-run，必须显式传 `apply` 子命令才会写文件；`apply` 前自动打 tar 备份
- 参考 spec：`docs/superpowers/specs/2026-07-16-extract-url-storage-restructure-design.md`

---

### Task 1: config.py — 共享路径计算函数

**Files:**
- Modify: `skills/research/extract-url/scripts/config.py`
- Test: `skills/research/extract-url/tests/test_config.py`

**Interfaces:**
- Produces: `config.get_url_hash(source_url: str) -> str`，`config.get_article_paths(source_url: str, origin_title: str) -> dict`，返回 dict 含 key：`url_hash`, `article_dir`, `origin_dir`, `translation_dir`, `image_dir`, `origin_path`, `translation_path`（均为 str）

- [ ] **Step 1: 写失败的测试**

在 `skills/research/extract-url/tests/test_config.py` 末尾追加：

```python
def test_get_url_hash_matches_md5_first_8_hex(tmp_path):
    import hashlib
    url = 'https://example.com/a'
    assert config.get_url_hash(url) == hashlib.md5(url.encode()).hexdigest()[:8]


def test_get_article_paths_returns_expected_keys(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'VAULT_PATH': str(tmp_path / 'vault'), 'CHROME_PROFILE': '/p'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        paths = config.get_article_paths('https://example.com/a', 'My Article')
    assert set(paths.keys()) == {
        'url_hash', 'article_dir', 'origin_dir', 'translation_dir',
        'image_dir', 'origin_path', 'translation_path',
    }


def test_get_article_paths_uses_url_hash_as_folder_name(tmp_path):
    cfg = tmp_path / 'config.json'
    vault = tmp_path / 'vault'
    cfg.write_text(json.dumps({'VAULT_PATH': str(vault), 'CHROME_PROFILE': '/p'}))
    url = 'https://example.com/a'
    with patch.object(config, 'CONFIG_PATH', cfg):
        paths = config.get_article_paths(url, 'My Article')
    assert paths['url_hash'] == config.get_url_hash(url)
    assert paths['article_dir'] == str(vault / paths['url_hash'])
    assert paths['origin_dir'] == str(vault / paths['url_hash'] / 'Origin')
    assert paths['translation_dir'] == str(vault / paths['url_hash'] / 'Translation')
    assert paths['image_dir'] == str(vault / paths['url_hash'] / 'Image')


def test_get_article_paths_sanitizes_title_for_filename(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'VAULT_PATH': str(tmp_path / 'vault'), 'CHROME_PROFILE': '/p'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        paths = config.get_article_paths('https://example.com/a', 'A/B:C*D?E')
    assert Path(paths['origin_path']).name == 'ABCDE.md'


def test_get_article_paths_translation_reuses_origin_filename(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'VAULT_PATH': str(tmp_path / 'vault'), 'CHROME_PROFILE': '/p'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        paths = config.get_article_paths('https://example.com/a', 'My Article')
    assert Path(paths['origin_path']).name == Path(paths['translation_path']).name == 'My Article.md'
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_config.py -v -k "get_url_hash or get_article_paths"`
Expected: FAIL，报 `AttributeError: module 'config' has no attribute 'get_url_hash'`

- [ ] **Step 3: 实现 `get_url_hash` 和 `get_article_paths`**

在 `skills/research/extract-url/scripts/config.py` 顶部 import 区加 `hashlib`：

```python
import json, os, hashlib
from pathlib import Path
```

在 `set_config` 函数之前（`get_chrome_profile` 之后）插入：

```python
def get_url_hash(source_url: str) -> str:
    return hashlib.md5(source_url.encode()).hexdigest()[:8]


def get_article_paths(source_url: str, origin_title: str) -> dict:
    """文章专属文件夹路径：VAULT_PATH/<url_hash>/{Origin,Translation,Image}/"""
    import sys as _sys
    references_dir = str(Path(__file__).parent.parent / 'references')
    if references_dir not in _sys.path:
        _sys.path.insert(0, references_dir)
    from article_utils import sanitize_filename

    vault_path = get_vault_path()
    url_hash = get_url_hash(source_url)
    article_dir = os.path.join(vault_path, url_hash)
    filename = sanitize_filename(origin_title) + '.md'
    origin_dir = os.path.join(article_dir, 'Origin')
    translation_dir = os.path.join(article_dir, 'Translation')
    image_dir = os.path.join(article_dir, 'Image')
    return {
        'url_hash': url_hash,
        'article_dir': article_dir,
        'origin_dir': origin_dir,
        'translation_dir': translation_dir,
        'image_dir': image_dir,
        'origin_path': os.path.join(origin_dir, filename),
        'translation_path': os.path.join(translation_dir, filename),
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_config.py -v`
Expected: PASS（全部，包括原有测试）

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/scripts/config.py skills/research/extract-url/tests/test_config.py
git commit -m "feat(extract-url): add get_url_hash/get_article_paths shared path resolver"
```

---

### Task 2: playwright_web.py — 改用共享路径 + 新链接格式

**Files:**
- Modify: `skills/research/extract-url/scripts/playwright_web.py`
- Test: `skills/research/extract-url/tests/test_playwright_web.py`

**Interfaces:**
- Consumes: `config.get_article_paths(source_url, origin_title) -> dict`（Task 1）

- [ ] **Step 1: 写失败的测试（e2e 断言新目录结构）**

在 `test_playwright_web_e2e` 函数末尾（`assert 'source_url: https://example.com/e2e-test' in content` 之后）追加：

```python
    import hashlib
    expected_hash = hashlib.md5('https://example.com/e2e-test'.encode()).hexdigest()[:8]
    assert origin_file.parent.name == 'Origin'
    assert origin_file.parent.parent.name == expected_hash
    assert origin_file.parent.parent.parent == skill_config['vault']
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_web.py -v -k e2e`
Expected: FAIL（若本机装了 playwright；未装则 SKIPPED——若 SKIPPED 无法验证红灯，直接进入 Step 3 后用 Step 4 确认绿灯或 SKIPPED）

- [ ] **Step 3: 修改 `playwright_web.py`**

修改 import 行（原第 28 行）：

```python
from config import get_vault_path, get_chrome_profile
```
改为：
```python
from config import get_vault_path, get_chrome_profile, get_article_paths
```

修改 article_utils import 行（原第 37 行），去掉不再使用的 `sanitize_filename`：

```python
from article_utils import infer_ext, format_block, sanitize_filename, repair_frontmatter, record_issues
```
改为：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_issues
```

替换原第 139-145 行：

```python
url_hash   = hashlib.md5(url.encode()).hexdigest()[:8]
image_dir  = os.path.join(vault_path, 'Image')
origin_dir = os.path.join(vault_path, 'Origin')
db_path    = os.path.join(vault_path, 'url-index.db')

os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)
```
改为：
```python
db_path = os.path.join(vault_path, 'url-index.db')
```

在 `if _is_thin(result): ...` 块（原第 158-163 行）之后、`# --- Download images ---` 之前插入：

```python
title = result.get('title', 'Untitled')
paths = get_article_paths(url, title)
image_dir   = paths['image_dir']
origin_dir  = paths['origin_dir']
origin_path = paths['origin_path']
os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)
```

修改图片文件名（原第 172 行）：
```python
    fname = f"{url_hash}_img_{i+1}{ext}"
```
改为：
```python
    fname = f"img_{i+1}{ext}"
```

删除原第 187-194 行中重复计算 `title`/`origin_filename`/`origin_path` 的部分：

```python
blocks       = result['blocks']
title        = result.get('title', 'Untitled')
author       = result.get('author', '')
publish_date = (result.get('publishDate') or '')[:10]
fetch_date   = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

origin_filename = sanitize_filename(title) + '.md'
origin_path     = os.path.join(origin_dir, origin_filename)
```
改为（`title` 已在上面赋值，不再重复）：
```python
blocks       = result['blocks']
author       = result.get('author', '')
publish_date = (result.get('publishDate') or '')[:10]
fetch_date   = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
```

修改图片引用格式（原第 201 行）：
```python
            parts.append(f'![](Image/{img["filename"]})')
```
改为：
```python
            parts.append(f'![](../Image/{img["filename"]})')
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_web.py -v`
Expected: PASS（`test_playwright_web_e2e` PASS 或因未装 playwright 而 SKIPPED，其余用例 PASS）

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/scripts/playwright_web.py skills/research/extract-url/tests/test_playwright_web.py
git commit -m "feat(extract-url): playwright_web.py uses get_article_paths for nested folder layout"
```

---

### Task 3: playwright_web_arxiv.py — 同样的路径改造

**Files:**
- Modify: `skills/research/extract-url/scripts/playwright_web_arxiv.py`

**Interfaces:**
- Consumes: `config.get_article_paths(source_url, origin_title) -> dict`（Task 1）

无既有测试文件覆盖此脚本（现状如此，不在本次新增，遵循最小改动原则）；本任务只做与 Task 2 完全对称的路径改造，靠人工核对 diff 与 Task 2 一致。

- [ ] **Step 1: 修改 import**

原第 36 行：
```python
from config import get_vault_path, get_chrome_profile
```
改为：
```python
from config import get_vault_path, get_chrome_profile, get_article_paths
```

原第 45 行：
```python
from article_utils import infer_ext, format_block, sanitize_filename, repair_frontmatter, record_issues
```
改为：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_issues
```

- [ ] **Step 2: 替换路径计算块**

原第 188-194 行：
```python
url_hash   = hashlib.md5(url.encode()).hexdigest()[:8]
image_dir  = os.path.join(vault_path, 'Image')
origin_dir = os.path.join(vault_path, 'Origin')
db_path    = os.path.join(vault_path, 'url-index.db')

os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)
```
改为：
```python
db_path = os.path.join(vault_path, 'url-index.db')
```

在 `if _is_thin(result): ...` 块（原第 215-220 行）之后、`# --- Download images ---` 之前插入：
```python
title = result.get('title', 'Untitled')
paths = get_article_paths(url, title)
image_dir   = paths['image_dir']
origin_dir  = paths['origin_dir']
origin_path = paths['origin_path']
os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)
```

- [ ] **Step 3: 图片文件名与引用格式**

原第 229 行：
```python
    fname = f"{url_hash}_img_{i+1}{ext}"
```
改为：
```python
    fname = f"img_{i+1}{ext}"
```

原第 244-251 行：
```python
blocks       = result['blocks']
title        = result.get('title', 'Untitled')
author       = result.get('author', '')
publish_date = (result.get('publishDate') or '')[:10]
fetch_date   = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

origin_filename = sanitize_filename(title) + '.md'
origin_path     = os.path.join(origin_dir, origin_filename)
```
改为：
```python
blocks       = result['blocks']
author       = result.get('author', '')
publish_date = (result.get('publishDate') or '')[:10]
fetch_date   = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
```

原第 258 行：
```python
            parts.append(f'![](Image/{img["filename"]})')
```
改为：
```python
            parts.append(f'![](../Image/{img["filename"]})')
```

- [ ] **Step 4: 语法自检**

Run: `python3 -m py_compile skills/research/extract-url/scripts/playwright_web_arxiv.py`
Expected: 无输出，退出码 0

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/scripts/playwright_web_arxiv.py
git commit -m "feat(extract-url): playwright_web_arxiv.py uses get_article_paths for nested folder layout"
```

---

### Task 4: playwright_xcom.py — 同样的路径改造

**Files:**
- Modify: `skills/research/extract-url/scripts/playwright_xcom.py`
- Test: `skills/research/extract-url/tests/test_playwright_xcom.py`

**Interfaces:**
- Consumes: `config.get_article_paths(source_url, origin_title) -> dict`（Task 1）

此脚本的路径计算块在抓取（`_do_scrape`）**之前**，但 `title` 只有抓取完成后才知道，所以要把路径计算挪到抓取完成之后（原 `image_dir`/`origin_dir` 计算与后续代码之间无依赖，可安全移动）。

- [ ] **Step 1: 写失败的测试**

在 `skills/research/extract-url/tests/test_playwright_xcom.py` 末尾追加：

```python
def test_playwright_xcom_imports_get_article_paths():
    """Regression: script must import get_article_paths, not compute url_hash/Image/Origin inline."""
    content = (SCRIPTS_DIR / 'playwright_xcom.py').read_text(encoding='utf-8')
    assert 'get_article_paths' in content
    assert "os.path.join(vault_path, 'Image')" not in content
    assert "os.path.join(vault_path, 'Origin')" not in content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_xcom.py -v -k get_article_paths`
Expected: FAIL（`assert 'get_article_paths' in content` 失败）

- [ ] **Step 3: 修改 `playwright_xcom.py`**

原第 22 行：
```python
from config import get_vault_path, get_chrome_profile
```
改为：
```python
from config import get_vault_path, get_chrome_profile, get_article_paths
```

原第 34 行：
```python
from article_utils import infer_ext, format_block, sanitize_filename, repair_frontmatter, record_issues
```
改为：
```python
from article_utils import infer_ext, format_block, repair_frontmatter, record_issues
```

原第 36-42 行：
```python
url_hash   = hashlib.md5(url.encode()).hexdigest()[:8]
image_dir  = os.path.join(vault_path, 'Image')
origin_dir = os.path.join(vault_path, 'Origin')
db_path    = os.path.join(vault_path, 'url-index.db')

os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)
```
改为：
```python
db_path = os.path.join(vault_path, 'url-index.db')
```

原第 402-404 行（`if result.get('error'): ...` 块）之后、`# --- Download images ---` 之前插入：
```python
title = result.get('title', 'Untitled')
paths = get_article_paths(url, title)
image_dir   = paths['image_dir']
origin_dir  = paths['origin_dir']
origin_path = paths['origin_path']
os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)
```

原第 413 行：
```python
    fname = f"{url_hash}_img_{i+1}{ext}"
```
改为：
```python
    fname = f"img_{i+1}{ext}"
```

原第 429-436 行：
```python
blocks       = result['blocks']
title        = result.get('title', 'Untitled')
author       = result.get('author', '')
publish_date = result.get('publishDate', '')[:10]
fetch_date   = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

origin_filename = sanitize_filename(title) + '.md'
origin_path     = os.path.join(origin_dir, origin_filename)
```
改为：
```python
blocks       = result['blocks']
author       = result.get('author', '')
publish_date = result.get('publishDate', '')[:10]
fetch_date   = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
```

原第 443 行：
```python
            parts.append(f'![](Image/{img["filename"]})')
```
改为：
```python
            parts.append(f'![](../Image/{img["filename"]})')
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_playwright_xcom.py -v`
Expected: PASS（全部）

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/scripts/playwright_xcom.py skills/research/extract-url/tests/test_playwright_xcom.py
git commit -m "feat(extract-url): playwright_xcom.py uses get_article_paths for nested folder layout"
```

---

### Task 5: Subagent 2 翻译 prompt — 改用共享路径 + 新双链格式

**Files:**
- Modify: `skills/research/extract-url/references/subagent2-tag-translate-prompt.md`
- Test: `skills/research/extract-url/tests/test_subagent2_prompt.py`（新增）

**Interfaces:**
- Consumes: `config.get_article_paths(source_url, origin_title) -> dict`（Task 1，subagent 在执行环境里 `sys.path.insert(0, f'{skill_dir}/scripts')` 后 import）

Prompt 文本无法用 pytest 直接执行验证语义，用"内容断言测试"防止未来又退回旧的重复逻辑。

- [ ] **Step 1: 写失败的测试（新文件）**

创建 `skills/research/extract-url/tests/test_subagent2_prompt.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_subagent2_prompt.py -v`
Expected: FAIL（当前文件内容不含 `get_article_paths`）

- [ ] **Step 3: 修改 prompt 文件**

替换第 16-21 行：
```
   import json, os
   from pathlib import Path
   _cfg       = json.loads((Path.home() / '.hskill' / 'url-extract' / 'config.json').read_text())
   vault_path = _cfg['VAULT_PATH']
   skill_dir  = 'SKILL_DIR'
```
改为：
```
   import sys
   from pathlib import Path
   skill_dir = 'SKILL_DIR'
   sys.path.insert(0, f'{skill_dir}/scripts')
   from config import get_vault_path, get_article_paths
   vault_path   = get_vault_path()
   origin_title = Path(origin_path).stem
   paths        = get_article_paths(url, origin_title)
```

替换第 62-67 行：
```
6. 保存译文到 vault_path/<文件名>：
   - 文件名与 Origin 文件名相同
   - frontmatter：publish_date、fetch_date、author、source_url、origin_title、
     category（如有）、fetch_type（默认 manual）、tags（阶段 1b 输出）、
     candidate_tags（阶段 1a 输出）、description（阶段 1a 输出）
   - 正文首行插入双向链接 [[Origin/<文件名>]]
```
改为：
```
6. 保存译文到 paths['translation_path']（先 mkdir -p paths['translation_dir']）：
   - 文件名与 Origin 文件名相同（paths['translation_path'] 已是完整目标路径）
   - frontmatter：publish_date、fetch_date、author、source_url、origin_title、
     category（如有）、fetch_type（默认 manual）、tags（阶段 1b 输出）、
     candidate_tags（阶段 1a 输出）、description（阶段 1a 输出）
   - 正文首行插入双向链接 [[{paths['url_hash']}/Origin/<文件名>]]
   - 正文中从原文复制来的图片引用（`![](../Image/xxx)`）原样保留、无需改路径——
     Origin 和 Translation 是同级目录，相对路径天然一致
```

替换第 69-72 行：
```
7. 执行校验并写入 SQLite 索引：
   import subprocess, os
   from pathlib import Path
   article_path = str(Path(vault_path) / os.path.basename(origin_path))
```
改为：
```
7. 执行校验并写入 SQLite 索引：
   import subprocess, os
   article_path = paths['translation_path']
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_subagent2_prompt.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/references/subagent2-tag-translate-prompt.md skills/research/extract-url/tests/test_subagent2_prompt.py
git commit -m "feat(extract-url): subagent2 prompt uses get_article_paths, new hash-prefixed wikilink"
```

---

### Task 6: 文档更新（SKILL.md / file-format.md）+ 版本号

**Files:**
- Modify: `skills/research/extract-url/SKILL.md`
- Modify: `skills/research/extract-url/references/file-format.md`

无自动化测试（纯文档）；验证方式是人工核对与 Task 1-5 实现的路径/链接格式完全一致。

- [ ] **Step 1: 更新 SKILL.md 版本号**

frontmatter 第 3 行：
```yaml
version: "2.4.0"
```
改为：
```yaml
version: "2.5.0"
```

- [ ] **Step 2: 更新「路径变量」章节**

原第 73-82 行：
```
## 路径变量（脚本自读 config.json，无需 Agent 传参）

```
Config:   ~/.hskill/url-extract/config.json
Base:     VAULT_PATH   (脚本从 config.json 读取)
Origin:   VAULT_PATH/Origin
Image:    VAULT_PATH/Image
DB:       VAULT_PATH/url-index.db
SkillDir: 平台固定值（见平台补丁）
```
```
改为：
```
## 路径变量（脚本自读 config.json，无需 Agent 传参）

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
```

- [ ] **Step 3: 更新完成卡片示例**

原「成功」卡片示例中：
```
路径  /Vault/Reading/article.md
```
改为：
```
路径  /Vault/Reading/a1b2c3d4/Translation/article.md
```

原「部分完成」卡片示例中：
```
路径  /Vault/Origin/article.md（仅原文）
```
改为：
```
路径  /Vault/Reading/a1b2c3d4/Origin/article.md（仅原文）
```

- [ ] **Step 4: 更新 file-format.md 保存路径表**

原第 68-75 行：
```
## 保存路径

| 类型 | 路径 |
|------|------|
| 原文 | `Origin/<origin_title>.md` |
| 译文 | `<title>.md`（无 Origin 子文件夹） |
| 图片 | `Image/<url_hash>_img_N.ext` |
```
改为：
```
## 保存路径

文章专属文件夹：`<hash8>/`，其中 `hash8 = md5(source_url).hexdigest()[:8]`，统一由 `scripts/config.py` 的 `get_article_paths()` 计算（图片、原文/译文文件名共用同一算法）。

| 类型 | 路径 |
|------|------|
| 原文 | `<hash8>/Origin/<origin_title>.md` |
| 译文 | `<hash8>/Translation/<origin_title>.md`（与原文同名） |
| 图片 | `<hash8>/Image/img_N.ext` |

双链示例（译文首行）：`[[<hash8>/Origin/<origin_title>.md]]`
图片引用示例（原文/译文正文内）：`![](../Image/img_1.jpg)`
```

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/SKILL.md skills/research/extract-url/references/file-format.md
git commit -m "docs(extract-url): document per-article folder layout, bump version to 2.5.0"
```

---

### Task 7: 迁移脚本第一阶段 — plan / apply

**Files:**
- Create: `skills/research/extract-url/scripts/migrate_to_folder_structure.py`
- Test: `skills/research/extract-url/tests/test_migrate_to_folder_structure.py`

**Interfaces:**
- Consumes: `config.get_vault_path() -> str`，`config.get_url_hash(source_url) -> str`（Task 1）
- Produces: `migrate.build_plan(vault_path) -> dict`（keys: `complete`, `partial`, `anomalies`, `orphan_images`），`migrate.apply_plan(vault_path, plan, db_path) -> dict`（keys: `moved`, `failed`），`migrate.get_url_hash(source_url) -> str`（re-export）。Task 8 会在此基础上追加 `find_merge_candidates` / `apply_merge`。

- [ ] **Step 1: 写失败的测试（新文件）**

创建 `skills/research/extract-url/tests/test_migrate_to_folder_structure.py`：

```python
import sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
import migrate_to_folder_structure as migrate

ORIGIN_TMPL = """---
publish_date: 2026-01-01
fetch_date: 2026-01-02
author: Test Author
source_url: {url}
origin_title: "{title}"
---

# {title}

Body text here.
{img_line}
"""

TRANSLATION_TMPL = """---
publish_date: 2026-01-01
fetch_date: 2026-01-02
author: Test Author
source_url: {url}
origin_title: "{title}"
tags: []
description: A test article.
---

{wikilink}

---

# {title}（译文）

正文内容。
{img_line}
"""


def _make_vault(tmp_path):
    vault = tmp_path / 'vault'
    (vault / 'Origin').mkdir(parents=True)
    (vault / 'Image').mkdir(parents=True)
    return vault


def _write_pair(vault, url, title, filename, image_names=None,
                 wikilink_target=None, translation_filename=None):
    image_names = image_names or []
    img_line = '\n'.join(f'![](Image/{n})' for n in image_names)
    origin_content = ORIGIN_TMPL.format(url=url, title=title, img_line=img_line)
    (vault / 'Origin' / f'{filename}.md').write_text(origin_content, encoding='utf-8')

    for n in image_names:
        (vault / 'Image' / n).write_bytes(b'fake-image-bytes')

    t_filename = translation_filename or filename
    wikilink = f'[[Origin/{wikilink_target or filename}.md]]'
    translation_content = TRANSLATION_TMPL.format(url=url, title=title, wikilink=wikilink, img_line=img_line)
    (vault / f'{t_filename}.md').write_text(translation_content, encoding='utf-8')


def test_build_plan_pairs_complete_article(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/a', 'Article A', 'article-a',
                image_names=['abcd1234_img_1.jpg'])

    plan = migrate.build_plan(vault)

    assert len(plan['complete']) == 1
    assert len(plan['partial']) == 0
    assert plan['complete'][0]['source_url'] == 'https://example.com/a'
    assert plan['complete'][0]['url_hash'] == migrate.get_url_hash('https://example.com/a')


def test_build_plan_pairs_by_own_url_even_if_filename_differs(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/b', 'Article B', 'article-b',
                translation_filename='article-b-translated-title')

    plan = migrate.build_plan(vault)

    assert len(plan['complete']) == 1
    assert plan['complete'][0]['origin']['path'].name == 'article-b.md'
    assert plan['complete'][0]['translation']['path'].name == 'article-b-translated-title.md'


def test_build_plan_detects_partial_origin_only(tmp_path):
    vault = _make_vault(tmp_path)
    origin_content = ORIGIN_TMPL.format(url='https://example.com/c', title='Article C', img_line='')
    (vault / 'Origin' / 'article-c.md').write_text(origin_content, encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['partial']) == 1
    assert plan['partial'][0]['origin'] is not None
    assert plan['partial'][0]['translation'] is None


def test_build_plan_detects_partial_translation_only(tmp_path):
    vault = _make_vault(tmp_path)
    translation_content = TRANSLATION_TMPL.format(
        url='https://example.com/d', title='Article D', wikilink='[[Origin/article-d.md]]', img_line=''
    )
    (vault / 'article-d.md').write_text(translation_content, encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['partial']) == 1
    assert plan['partial'][0]['translation'] is not None
    assert plan['partial'][0]['origin'] is None
    assert plan['anomalies']['missing_link'] == [str(vault / 'article-d.md')]


def test_build_plan_flags_missing_source_url(tmp_path):
    vault = _make_vault(tmp_path)
    (vault / 'Origin' / 'no-url.md').write_text('---\ntitle: x\n---\nbody', encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert str(vault / 'Origin' / 'no-url.md') in plan['anomalies']['missing_source_url']
    assert len(plan['complete']) == 0
    assert len(plan['partial']) == 0


def test_build_plan_flags_link_url_mismatch(tmp_path):
    vault = _make_vault(tmp_path)
    origin_content = ORIGIN_TMPL.format(url='https://example.com/e-origin', title='Article E', img_line='')
    (vault / 'Origin' / 'article-e.md').write_text(origin_content, encoding='utf-8')
    translation_content = TRANSLATION_TMPL.format(
        url='https://example.com/e-translation', title='Article E',
        wikilink='[[Origin/article-e.md]]', img_line=''
    )
    (vault / 'article-e.md').write_text(translation_content, encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['anomalies']['link_url_mismatch']) == 1
    mismatch = plan['anomalies']['link_url_mismatch'][0]
    assert mismatch['translation_url'] == 'https://example.com/e-translation'
    assert mismatch['linked_origin_url'] == 'https://example.com/e-origin'
    assert len(plan['partial']) == 2


def test_build_plan_skips_sync_conflict_files(tmp_path):
    vault = _make_vault(tmp_path)
    (vault / 'article-f.sync-conflict-20260101-abc.md').write_text('irrelevant', encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['complete']) == 0
    assert len(plan['partial']) == 0
    assert all(v == [] for v in plan['anomalies'].values())


def test_build_plan_finds_orphan_images(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/g', 'Article G', 'article-g',
                image_names=['abcd1234_img_1.jpg'])
    (vault / 'Image' / 'orphan_img.jpg').write_bytes(b'orphan')

    plan = migrate.build_plan(vault)

    assert plan['orphan_images'] == ['orphan_img.jpg']


def test_apply_plan_moves_files_strips_hash_prefix_and_rewrites_links(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/h', 'Article H', 'article-h',
                image_names=['deadbeef_img_1.jpg'])
    plan = migrate.build_plan(vault)
    db_path = vault / 'url-index.db'

    result = migrate.apply_plan(vault, plan, db_path)

    assert result['failed'] == []
    url_hash = migrate.get_url_hash('https://example.com/h')
    article_dir = vault / url_hash

    origin_file = article_dir / 'Origin' / 'article-h.md'
    translation_file = article_dir / 'Translation' / 'article-h.md'
    image_file = article_dir / 'Image' / 'img_1.jpg'
    assert origin_file.exists()
    assert translation_file.exists()
    assert image_file.exists()
    assert not (vault / 'Origin' / 'article-h.md').exists()
    assert not (vault / 'article-h.md').exists()
    assert not (vault / 'Image' / 'deadbeef_img_1.jpg').exists()

    origin_content = origin_file.read_text(encoding='utf-8')
    translation_content = translation_file.read_text(encoding='utf-8')
    assert '![](../Image/img_1.jpg)' in origin_content
    assert '![](../Image/img_1.jpg)' in translation_content
    assert f'[[{url_hash}/Origin/article-h.md]]' in translation_content


def test_apply_plan_writes_url_index_db(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/i', 'Article I', 'article-i')
    plan = migrate.build_plan(vault)
    db_path = vault / 'url-index.db'

    migrate.apply_plan(vault, plan, db_path)

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        'SELECT origin_path, article_path FROM url_index WHERE source_url=?',
        ('https://example.com/i',)
    ).fetchone()
    conn.close()
    assert row is not None
    url_hash = migrate.get_url_hash('https://example.com/i')
    assert row[0] == str(vault / url_hash / 'Origin' / 'article-i.md')
    assert row[1] == str(vault / url_hash / 'Translation' / 'article-i.md')


def test_apply_plan_is_idempotent_on_rerun(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/j', 'Article J', 'article-j')
    db_path = vault / 'url-index.db'

    plan1 = migrate.build_plan(vault)
    migrate.apply_plan(vault, plan1, db_path)

    plan2 = migrate.build_plan(vault)
    assert plan2['complete'] == []
    assert plan2['partial'] == []
    result2 = migrate.apply_plan(vault, plan2, db_path)
    assert result2['moved'] == []
    assert result2['failed'] == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_migrate_to_folder_structure.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'migrate_to_folder_structure'`）

- [ ] **Step 3: 实现 `migrate_to_folder_structure.py`**

创建 `skills/research/extract-url/scripts/migrate_to_folder_structure.py`：

```python
#!/usr/bin/env python3
"""
Migrate extract-url Vault from flat structure (root .md + Origin/ + shared Image/)
to per-article folders (<hash8>/{Origin,Translation,Image}/).

Usage:
  python3 migrate_to_folder_structure.py plan
  python3 migrate_to_folder_structure.py apply [--no-backup]
  python3 migrate_to_folder_structure.py find-merges
  python3 migrate_to_folder_structure.py apply-merge --keep <hash8> --drop <hash8>

Reads VAULT_PATH from ~/.hskill/url-extract/config.json (via config.get_vault_path()).
"""
import argparse, os, re, shutil, sqlite3, sys, tarfile, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from config import get_vault_path, get_url_hash

_IMG_RE = re.compile(r'!\[([^\]]*)\]\(\.{0,2}/?Image/([^)]+)\)')
_WIKILINK_RE = re.compile(r'\[\[Origin/([^\]]+)\]\]')
_HASH_PREFIX_RE = re.compile(r'^[0-9a-f]{8}_(img_\d+\..+)$')


def _read_frontmatter(path):
    text = Path(path).read_text(encoding='utf-8')
    if not text.startswith('---'):
        return {}
    parts = text.split('---', 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _extract_origin_link_target(content):
    m = _WIKILINK_RE.search(content)
    if not m:
        return None
    name = m.group(1)
    if not name.endswith('.md'):
        name += '.md'
    return name


def _extract_image_filenames(content):
    return [m.group(2) for m in _IMG_RE.finditer(content)]


def _strip_hash_prefix(filename):
    m = _HASH_PREFIX_RE.match(filename)
    return m.group(1) if m else filename


def _rewrite_image_refs(content, filename_map):
    def _sub(m):
        alt, old_name = m.group(1), m.group(2)
        new_name = filename_map.get(old_name, old_name)
        return f'![{alt}](../Image/{new_name})'
    return _IMG_RE.sub(_sub, content)


def _rewrite_wikilink(content, url_hash, origin_filename):
    new_link = f'[[{url_hash}/Origin/{origin_filename}]]'
    return _WIKILINK_RE.sub(new_link, content, count=1)


def _scan_dir(dir_path, pattern='*.md'):
    entries = []
    dir_path = Path(dir_path)
    if not dir_path.exists():
        return entries
    for p in sorted(dir_path.glob(pattern)):
        if '.sync-conflict-' in p.name:
            continue
        fm = _read_frontmatter(p)
        entries.append({'path': p, 'source_url': fm.get('source_url'), 'frontmatter': fm})
    return entries


def _find_orphan_images(vault_path, origin_entries, translation_entries):
    referenced = set()
    for e in origin_entries + translation_entries:
        content = e['path'].read_text(encoding='utf-8')
        referenced.update(_extract_image_filenames(content))
    image_dir = Path(vault_path) / 'Image'
    if not image_dir.exists():
        return []
    all_images = {p.name for p in image_dir.glob('*') if p.is_file()}
    return sorted(all_images - referenced)


def build_plan(vault_path):
    vault_path = Path(vault_path)
    origin_entries = _scan_dir(vault_path / 'Origin')
    translation_entries = _scan_dir(vault_path, pattern='*.md')

    anomalies = {'missing_source_url': [], 'link_url_mismatch': [], 'missing_link': []}

    origin_by_url = {}
    for e in origin_entries:
        if not e['source_url']:
            anomalies['missing_source_url'].append(str(e['path']))
            continue
        origin_by_url[e['source_url']] = e

    translation_by_url = {}
    for e in translation_entries:
        if not e['source_url']:
            anomalies['missing_source_url'].append(str(e['path']))
            continue
        translation_by_url[e['source_url']] = e

        content = e['path'].read_text(encoding='utf-8')
        link_target = _extract_origin_link_target(content)
        if link_target is None:
            anomalies['missing_link'].append(str(e['path']))
            continue
        linked_origin_path = vault_path / 'Origin' / link_target
        if not linked_origin_path.exists():
            anomalies['missing_link'].append(str(e['path']))
            continue
        linked_fm = _read_frontmatter(linked_origin_path)
        if linked_fm.get('source_url') != e['source_url']:
            anomalies['link_url_mismatch'].append({
                'translation': str(e['path']),
                'linked_origin': str(linked_origin_path),
                'translation_url': e['source_url'],
                'linked_origin_url': linked_fm.get('source_url'),
            })

    all_urls = set(origin_by_url) | set(translation_by_url)
    complete, partial = [], []
    for url in sorted(all_urls):
        origin_e = origin_by_url.get(url)
        translation_e = translation_by_url.get(url)
        entry = {
            'source_url': url,
            'url_hash': get_url_hash(url),
            'origin': origin_e,
            'translation': translation_e,
        }
        (complete if (origin_e and translation_e) else partial).append(entry)

    return {
        'complete': complete,
        'partial': partial,
        'anomalies': anomalies,
        'orphan_images': _find_orphan_images(vault_path, origin_entries, translation_entries),
    }


def _migrate_entry(vault_path, entry):
    url_hash = entry['url_hash']
    article_dir = Path(vault_path) / url_hash
    origin_e = entry['origin']
    translation_e = entry['translation']

    origin_content = origin_e['path'].read_text(encoding='utf-8') if origin_e else ''
    translation_content = translation_e['path'].read_text(encoding='utf-8') if translation_e else ''

    image_filename_map = {}
    for content in (origin_content, translation_content):
        for old_name in _extract_image_filenames(content):
            image_filename_map[old_name] = _strip_hash_prefix(old_name)

    if image_filename_map:
        image_dir = article_dir / 'Image'
        image_dir.mkdir(parents=True, exist_ok=True)
        src_image_dir = Path(vault_path) / 'Image'
        for old_name, new_name in image_filename_map.items():
            src = src_image_dir / old_name
            if src.exists():
                shutil.move(str(src), str(image_dir / new_name))

    if origin_e:
        origin_dir = article_dir / 'Origin'
        origin_dir.mkdir(parents=True, exist_ok=True)
        new_content = _rewrite_image_refs(origin_content, image_filename_map)
        target = origin_dir / origin_e['path'].name
        target.write_text(new_content, encoding='utf-8')
        origin_e['path'].unlink()
        entry['new_origin_path'] = str(target)

    if translation_e:
        translation_dir = article_dir / 'Translation'
        translation_dir.mkdir(parents=True, exist_ok=True)
        new_content = _rewrite_image_refs(translation_content, image_filename_map)
        if origin_e:
            new_content = _rewrite_wikilink(new_content, url_hash, origin_e['path'].name)
        target = translation_dir / translation_e['path'].name
        target.write_text(new_content, encoding='utf-8')
        translation_e['path'].unlink()
        entry['new_translation_path'] = str(target)


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


def _backup_vault(vault_path):
    vault_path = Path(vault_path)
    ts = time.strftime('%Y%m%d-%H%M%S')
    backup_path = vault_path.parent / f'{vault_path.name}-backup-{ts}.tar.gz'
    with tarfile.open(backup_path, 'w:gz') as tar:
        tar.add(vault_path, arcname=vault_path.name)
    return str(backup_path)


def _print_plan_summary(plan):
    print(f"完整配对：{len(plan['complete'])}")
    print(f"部分完成：{len(plan['partial'])}")
    for k, v in plan['anomalies'].items():
        print(f"异常[{k}]：{len(v)}")
    print(f"孤儿图片：{len(plan['orphan_images'])}")


def main():
    parser = argparse.ArgumentParser(description='Migrate extract-url Vault to per-article folder structure')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('plan')
    p_apply = sub.add_parser('apply')
    p_apply.add_argument('--no-backup', action='store_true')

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


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_migrate_to_folder_structure.py -v`
Expected: PASS（全部）

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/scripts/migrate_to_folder_structure.py skills/research/extract-url/tests/test_migrate_to_folder_structure.py
git commit -m "feat(extract-url): add migrate_to_folder_structure.py plan/apply for legacy data"
```

---

### Task 8: 迁移脚本第二阶段 — find-merges / apply-merge（先测试后实现）

**Files:**
- Modify: `skills/research/extract-url/scripts/migrate_to_folder_structure.py`（新增函数 + CLI 子命令，Task 7 尚未实现这部分）
- Modify: `skills/research/extract-url/tests/test_migrate_to_folder_structure.py`（追加用例）

**Interfaces:**
- Consumes: 复用 Task 7 的 `_read_frontmatter`、`_rewrite_wikilink`、`get_vault_path`、`build_plan`、`apply_plan`、`_print_plan_summary`、`main()` 的 argparse 框架
- Produces: `migrate.find_merge_candidates(vault_path) -> list[dict]`（每项 `{'a': {...}, 'b': {...}}`，子 dict 含 `hash`/`side`/`path`/`source_url`），`migrate.apply_merge(vault_path, keep_hash, drop_hash) -> None`

- [ ] **Step 1: 写失败的测试**

在 `test_migrate_to_folder_structure.py` 末尾追加：

```python
def _make_partial_article_folder(vault, url, title, side):
    url_hash = migrate.get_url_hash(url)
    article_dir = vault / url_hash
    sub = 'Origin' if side == 'origin' else 'Translation'
    (article_dir / sub).mkdir(parents=True)
    content = ORIGIN_TMPL.format(url=url, title=title, img_line='')
    filename = title.lower().replace(' ', '-') + '.md'
    (article_dir / sub / filename).write_text(content, encoding='utf-8')
    return url_hash


def test_find_merge_candidates_matches_normalized_urls(tmp_path):
    vault = _make_vault(tmp_path)
    hash_a = _make_partial_article_folder(
        vault, 'https://example.com/l?utm_source=newsletter', 'Article L', 'origin')
    hash_b = _make_partial_article_folder(vault, 'https://example.com/l', 'Article L', 'translation')

    candidates = migrate.find_merge_candidates(vault)

    assert len(candidates) == 1
    hashes = {candidates[0]['a']['hash'], candidates[0]['b']['hash']}
    assert hashes == {hash_a, hash_b}


def test_find_merge_candidates_ignores_same_side_pairs(tmp_path):
    vault = _make_vault(tmp_path)
    _make_partial_article_folder(vault, 'https://example.com/m', 'Article M', 'origin')
    _make_partial_article_folder(vault, 'https://example.com/m-different', 'Article M2', 'origin')

    assert migrate.find_merge_candidates(vault) == []


def test_find_merge_candidates_no_match_returns_empty(tmp_path):
    vault = _make_vault(tmp_path)
    _make_partial_article_folder(vault, 'https://example.com/n1', 'Article N1', 'origin')
    _make_partial_article_folder(vault, 'https://example.com/n2', 'Article N2', 'translation')

    assert migrate.find_merge_candidates(vault) == []


def test_apply_merge_combines_origin_and_translation_folders(tmp_path):
    vault = _make_vault(tmp_path)
    hash_a = _make_partial_article_folder(
        vault, 'https://example.com/o?utm_source=x', 'Article O', 'origin')
    hash_b = _make_partial_article_folder(vault, 'https://example.com/o', 'Article O', 'translation')

    migrate.apply_merge(vault, keep_hash=hash_a, drop_hash=hash_b)

    assert (vault / hash_a / 'Origin').exists()
    assert (vault / hash_a / 'Translation').exists()
    assert not (vault / hash_b).exists()


def test_apply_merge_rewrites_wikilink_to_keep_hash(tmp_path):
    vault = _make_vault(tmp_path)
    url = 'https://example.com/p'
    hash_a = migrate.get_url_hash(url)
    (vault / hash_a / 'Origin').mkdir(parents=True)
    (vault / hash_a / 'Origin' / 'article-p.md').write_text(
        ORIGIN_TMPL.format(url=url, title='Article P', img_line=''), encoding='utf-8'
    )
    hash_b = migrate.get_url_hash(url + '?utm_source=x')
    (vault / hash_b / 'Translation').mkdir(parents=True)
    (vault / hash_b / 'Translation' / 'article-p.md').write_text(
        TRANSLATION_TMPL.format(
            url=url + '?utm_source=x', title='Article P',
            wikilink='[[Origin/some-other-name.md]]', img_line=''
        ),
        encoding='utf-8'
    )

    migrate.apply_merge(vault, keep_hash=hash_a, drop_hash=hash_b)

    merged_content = (vault / hash_a / 'Translation' / 'article-p.md').read_text(encoding='utf-8')
    assert f'[[{hash_a}/Origin/article-p.md]]' in merged_content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_migrate_to_folder_structure.py -v -k "merge"`
Expected: FAIL，报 `AttributeError: module 'migrate_to_folder_structure' has no attribute 'find_merge_candidates'`

- [ ] **Step 3: 实现 `find_merge_candidates` / `apply_merge`**

在 `skills/research/extract-url/scripts/migrate_to_folder_structure.py` 顶部 import 区加 `urlparse`：

原：
```python
import argparse, os, re, shutil, sqlite3, sys, tarfile, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml
```
改为：
```python
import argparse, os, re, shutil, sqlite3, sys, tarfile, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import yaml
```

在 `_print_plan_summary` 函数**之前**插入：

```python
def _normalize_url(url):
    p = urlparse(url or '')
    netloc = p.netloc.lower()
    path = p.path.rstrip('/')
    query = '&'.join(
        kv for kv in p.query.split('&')
        if kv and not kv.split('=')[0].startswith('utm_')
    )
    normalized = f'{netloc}{path}'
    if query:
        normalized += f'?{query}'
    return normalized


def find_merge_candidates(vault_path):
    vault_path = Path(vault_path)
    partial_folders = []
    for d in sorted(vault_path.iterdir()):
        if not d.is_dir() or len(d.name) != 8:
            continue
        has_origin = (d / 'Origin').exists() and any((d / 'Origin').glob('*.md'))
        has_translation = (d / 'Translation').exists() and any((d / 'Translation').glob('*.md'))
        if has_origin and not has_translation:
            side = 'origin'
        elif has_translation and not has_origin:
            side = 'translation'
        else:
            continue
        sub = 'Origin' if side == 'origin' else 'Translation'
        md_file = next((d / sub).glob('*.md'))
        fm = _read_frontmatter(md_file)
        partial_folders.append({
            'hash': d.name, 'side': side, 'path': str(md_file),
            'source_url': fm.get('source_url', ''),
        })

    candidates = []
    for i, a in enumerate(partial_folders):
        for b in partial_folders[i + 1:]:
            if a['side'] == b['side']:
                continue
            if _normalize_url(a['source_url']) == _normalize_url(b['source_url']):
                candidates.append({'a': a, 'b': b})
    return candidates


def apply_merge(vault_path, keep_hash, drop_hash):
    vault_path = Path(vault_path)
    keep_dir = vault_path / keep_hash
    drop_dir = vault_path / drop_hash

    for side in ('Origin', 'Translation'):
        src_dir = drop_dir / side
        if not src_dir.exists():
            continue
        dst_dir = keep_dir / side
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in src_dir.glob('*.md'):
            shutil.move(str(f), str(dst_dir / f.name))

    drop_image_dir = drop_dir / 'Image'
    if drop_image_dir.exists():
        keep_image_dir = keep_dir / 'Image'
        keep_image_dir.mkdir(parents=True, exist_ok=True)
        for f in drop_image_dir.glob('*'):
            shutil.move(str(f), str(keep_image_dir / f.name))

    shutil.rmtree(drop_dir, ignore_errors=True)

    translation_files = list((keep_dir / 'Translation').glob('*.md')) if (keep_dir / 'Translation').exists() else []
    origin_files = list((keep_dir / 'Origin').glob('*.md')) if (keep_dir / 'Origin').exists() else []
    if translation_files and origin_files:
        t_path = translation_files[0]
        content = t_path.read_text(encoding='utf-8')
        content = _rewrite_wikilink(content, keep_hash, origin_files[0].name)
        t_path.write_text(content, encoding='utf-8')
```

在 `main()` 里把 `plan`/`apply` 两个子命令的注册和分支替换为包含 `find-merges`/`apply-merge` 的完整版本：

原：
```python
    sub.add_parser('plan')
    p_apply = sub.add_parser('apply')
    p_apply.add_argument('--no-backup', action='store_true')

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


if __name__ == '__main__':
    main()
```
改为：
```python
    sub.add_parser('plan')
    p_apply = sub.add_parser('apply')
    p_apply.add_argument('--no-backup', action='store_true')
    sub.add_parser('find-merges')
    p_merge = sub.add_parser('apply-merge')
    p_merge.add_argument('--keep', required=True)
    p_merge.add_argument('--drop', required=True)

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
        apply_merge(vault_path, args.keep, args.drop)
        print(f'已合并 {args.drop} → {args.keep}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd skills/research/extract-url && python3 -m pytest tests/test_migrate_to_folder_structure.py -v`
Expected: PASS（全部，含 Task 7 的用例）

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/scripts/migrate_to_folder_structure.py skills/research/extract-url/tests/test_migrate_to_folder_structure.py
git commit -m "feat(extract-url): add find_merge_candidates/apply_merge for post-migration URL-variant dedup"
```

---

### Task 9: 对真实 Vault 执行迁移（人工操作，非编码任务）

**Files:** 无代码改动，仅操作真实 `/Users/harveyzhang96/Vault/Product/Reading`

前置条件：Task 1-8 已全部完成、测试全绿、已合并到 `staging`。

- [ ] **Step 1: Dry-run 检查**

```bash
python3 /Users/harveyzhang96/Projects/harveyz-skill/skills/research/extract-url/scripts/migrate_to_folder_structure.py plan
```
人工检查输出的完整配对数、部分完成数、三类异常数、孤儿图片数是否与预期量级相符（约 150-365 完整/部分配对，`missing_link` 预计集中在此前发现的那 11 篇 `../Image` 错误链接文件附近，需要人工抽查确认这些异常是否都可接受）。

- [ ] **Step 2: 关闭 Obsidian、暂停 iCloud 同步**

手动操作：退出 Obsidian App；在系统设置里暂停 iCloud Drive 同步（或至少确认 `Reading` 目录当前没有 `.sync-conflict-*` 新文件持续产生）。

- [ ] **Step 3: 执行迁移**

```bash
python3 /Users/harveyzhang96/Projects/harveyz-skill/skills/research/extract-url/scripts/migrate_to_folder_structure.py apply
```
确认输出的备份路径（`Reading-backup-<timestamp>.tar.gz`）确实生成且体积合理（数百 MB 量级，含全部原图片）。

- [ ] **Step 4: 抽查结果**

随机挑 3-5 个 `<hash8>/` 文件夹，在文本编辑器里打开其中的 Translation `.md`，确认：
- 首行双链格式为 `[[<hash8>/Origin/xxx.md]]`
- 正文图片引用为 `![](../Image/xxx)` 且对应文件确实存在于同一 `<hash8>/Image/` 下

- [ ] **Step 5: 处理合并候选**

```bash
python3 /Users/harveyzhang96/Projects/harveyz-skill/skills/research/extract-url/scripts/migrate_to_folder_structure.py find-merges
```
逐条人工核对候选（两个 hash 文件夹的 URL 是否确实是同一篇文章的不同 URL 变体），确认后逐个执行：
```bash
python3 /Users/harveyzhang96/Projects/harveyz-skill/skills/research/extract-url/scripts/migrate_to_folder_structure.py apply-merge --keep <保留的hash> --drop <合并掉的hash>
```

- [ ] **Step 6: 恢复 Obsidian 与同步**

重新打开 Obsidian，恢复 iCloud 同步；打开 2-3 篇迁移后的译文，确认双链可点击跳转、图片正常显示。

---

## Self-Review 记录

- **Spec 覆盖**：新目录结构（Task 1-4）、路径集中化（Task 1）、双链/图片格式（Task 2-5）、Subagent 2 改造（Task 5）、DB 存储格式不变但内容更新（Task 7 的 `_rebuild_db`）、迁移脚本安全性（dry-run 默认/tar 备份/幂等/失败不中断，Task 7）、第二轮合并候选人工确认（Task 8）、11 篇 `../Image` 历史 bug 顺带修复（Task 7 的 `_rewrite_image_refs` 对所有引用格式统一重写，天然覆盖）、文档更新（Task 6）——均有对应任务。
- **Placeholder 扫描**：全部 Step 均为可执行命令/完整代码，无 TBD/TODO。
- **类型一致性**：`get_article_paths` 返回 dict 的 key 名称（`url_hash`/`article_dir`/`origin_dir`/`translation_dir`/`image_dir`/`origin_path`/`translation_path`）在 Task 1-5、Task 7 中保持一致；`build_plan`/`apply_plan`/`find_merge_candidates`/`apply_merge` 的函数名与参数在 Task 7-9 中保持一致。
