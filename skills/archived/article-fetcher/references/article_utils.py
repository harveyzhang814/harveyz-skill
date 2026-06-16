"""
共享工具函数：格式化 block、构建文章、修复 frontmatter
"""
import re, os, json, sqlite3, yaml
from datetime import datetime, timezone, timedelta

# ------------------------------------------------------------
# 公共常量
# ------------------------------------------------------------
HEADING_PREFIX = {'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### '}
IMAGE_BASE_URL = 'Image/'

FETCH_DATE = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

# ------------------------------------------------------------
# 1. format_block: 将单个 block 转为 Markdown 字符串
# ------------------------------------------------------------
def format_block(block):
    """将 {tag, content} 转为 Markdown 格式"""
    tag = block.get('tag', 'p')
    content = block.get('content', '')
    if tag in HEADING_PREFIX:
        return HEADING_PREFIX[tag] + content
    if tag == 'pre':
        return f'```\n{content}\n```'
    if tag == 'li':
        return f'- {content}'
    # 内容以 # 开头且含 / 或 --- = SKILL.md 代码块
    if content.startswith('# ') and ('/' in content or '---' in content):
        return f'```\n{content}\n```'
    return content


# ------------------------------------------------------------
# 2. infer_ext: 从 URL 或 Content-Type 推断图片扩展名
# ------------------------------------------------------------
def infer_ext(url, content_type=''):
    """从 URL 或 Content-Type 推断图片扩展名"""
    ext_map = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif', 'image/webp': '.webp'}
    if content_type:
        return ext_map.get(content_type, '.jpg')
    url_lower = url.lower()
    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        if ext in url_lower:
            return '.jpg' if ext == '.jpeg' else ext
    return '.jpg'


# ------------------------------------------------------------
# 3. build_article_from_json: 从统一 JSON 构建文章
# ------------------------------------------------------------
def build_article_from_json(json_path, title, source_url, origin_filename,
                             tags, description, author='', publish_date='',
                             origin_path=None, article_path=None):
    """
    从 article_combined.json 构建原文/译文文件。

    JSON 结构：
        blocks: [{tag, content, blockIndex}]
        images: [{src, alt, afterBlock, filename}]
    """
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    blocks = data.get('blocks', [])
    images = data.get('images') or data.get('imageBlocks') or []  # 兼容 imageBlocks/image 两种 key

    # 按 afterBlock 插入图片
    body_units = []
    # afterBlock == -1 的图片插入文章最开头
    pre_imgs = [f'![]({IMAGE_BASE_URL}{img["filename"]})'
                for img in images if img.get('afterBlock') == -1]
    if pre_imgs:
        body_units.append('\n'.join(pre_imgs))

    for i, block in enumerate(blocks):
        unit_parts = [format_block(block)]
        for img in images:
            if img.get('afterBlock') == i:
                unit_parts.append(f'![]({IMAGE_BASE_URL}{img["filename"]})')
        body_units.append('\n'.join(unit_parts))

    body = '\n\n'.join(body_units)

    tags_str = '  - ' + '\n  - '.join(tags)

    fm = f"""---
publish_date: {publish_date}
fetch_date: {FETCH_DATE}
author: {author}
source_url: {source_url}
origin_title: "{origin_filename.replace('.md', '')}"
tags:
{tags_str}
description: {description}
---"""

    content = f"""{fm}

[[Origin/{origin_filename}]]

---

# {title}

{body}
"""
    return content


# ------------------------------------------------------------
# 4. repair_frontmatter: 自动修复 frontmatter 字段
# ------------------------------------------------------------
def repair_frontmatter(fp, url, defaults=None):
    """
    尝试自动补全缺失字段，返回 (fm_dict, 修复了哪些字段, 剩余问题列表)
    """
    defaults = defaults or {}
    with open(fp, encoding='utf-8') as f:
        content = f.read()

    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return {}, [], ['无frontmatter']

    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()

    fixed, remaining = [], []

    # 自动补全 defaults
    for field, value in defaults.items():
        if not fm.get(field, '').strip():
            fm[field] = value
            fixed.append(f'{field}={value}')

    # tags 格式修复：逗号分隔 → YAML 列表
    tags_raw = fm.get('tags', '')
    if tags_raw and ',' in tags_raw and not tags_raw.startswith('-'):
        raw_list = [t.strip() for t in tags_raw.split(',') if t.strip()]
        def _norm_tag(t):
            if re.search(r'[\u4e00-\u9fff]', t):
                return t.lower()
            return t.lower().replace(' ', '-')
        fm['tags'] = '\n  - ' + '\n  - '.join(_norm_tag(t) for t in raw_list)
        fixed.append('tags=YAML列表')

    # tags 大写修复
    if fm.get('tags', '').startswith('-'):
        tag_lines = [l for l in fm['tags'].strip().split('\n') if l.strip().startswith('-')]
        new_lines = []
        for tl in tag_lines:
            tag_val = tl.lstrip('- ').strip()
            if tag_val and tag_val != tag_val.lower():
                new_lines.append(f'  - {tag_val.lower()}')
                fixed.append(f'tag-lowercase={tag_val}')
            else:
                new_lines.append(tl)
        fm['tags'] = '\n'.join(new_lines)

    # 写回文件
    fm_lines = [f'{k}: {v}' for k, v in fm.items()]
    fm_str = '---\n' + '\n'.join(fm_lines) + '\n---\n'
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(fm_str + content[m.end():])

    # 检查剩余问题
    for fld in ['publish_date', 'author', 'source_url']:
        if not fm.get(fld, '').strip():
            remaining.append(f'{fld}空')
    if 'origin_title' not in fm or not fm.get('origin_title', '').strip():
        remaining.append('origin_title空')
    if 'description' not in fm or not fm.get('description', '').strip():
        remaining.append('description空')

    return fm, fixed, remaining


# ------------------------------------------------------------
# 5. record_issues: 写入 issues 字段
# ------------------------------------------------------------
def record_issues(url, issues_text, db_path=None):
    """将 issues 写入 SQLite"""
    if db_path is None:
        db_path = os.path.expanduser(
            '{{VAULT_PATH}}/url-index.db'
        )
    conn = sqlite3.connect(db_path)
    conn.execute('UPDATE url_index SET issues=? WHERE url=?',
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
        "(url, title, fetched_at, issues, category, origin_path, article_path) "
        "VALUES (?,?,?,?,?,?,?)",
        (url, os.path.basename(article_path), fetch_date, '', cat, origin_path, article_path)
    )
    conn.commit()


# ------------------------------------------------------------
# 8. validate_and_repair: 完整校验 + 自动修复流程
# ------------------------------------------------------------
def validate_and_repair(origin_path, article_path, url, defaults=None):
    """
    执行保存后校验，自动修复可修复的问题。
    返回 (是否通过, fixed列表, remaining列表)
    """
    defaults = defaults or {}
    defaults.setdefault('fetch_date', FETCH_DATE)

    fm_orig, fixed_orig, rem_orig = repair_frontmatter(origin_path, url, defaults)
    fm_art, fixed_art, rem_art = repair_frontmatter(article_path, url, defaults)

    all_fixed = fixed_orig + fixed_art
    all_remaining = [f'[Origin] {r}' for r in rem_orig] + [f'[Article] {r}' for r in rem_art]

    passed = len(all_remaining) == 0
    return passed, all_fixed, all_remaining


# ------------------------------------------------------------
# 9. sanitize_filename: 文件名清理
# ------------------------------------------------------------
def sanitize_filename(name):
    """移除文件名中的特殊字符"""
    for ch in ['\\', '/', '*', '?', '<', '>', '|', ':', '"']:
        name = name.replace(ch, '')
    return name.lstrip('.')
