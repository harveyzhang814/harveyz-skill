"""
共享工具函数：格式化 block、构建文章、修复 frontmatter
"""
import re, os, json, yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path

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
    if tag == 'code':
        return f'`{content}`'
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
def repair_frontmatter(fp, url, defaults=None, skip_remaining_fields=None):
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
    raw_fm_lines = m.group(1).split('\n')
    i = 0
    while i < len(raw_fm_lines):
        line = raw_fm_lines[i]
        if ':' in line and not line.startswith(' ') and not line.startswith('-'):
            k, v = line.split(':', 1)
            k, v = k.strip(), v.strip()
            # collect indented continuation lines (multi-line YAML values e.g. tags list)
            j = i + 1
            sub_lines = []
            while j < len(raw_fm_lines) and (raw_fm_lines[j].startswith('  ') or raw_fm_lines[j].startswith('\t')):
                sub_lines.append(raw_fm_lines[j])
                j += 1
            if sub_lines:
                fm[k] = (v + '\n' + '\n'.join(sub_lines)) if v else '\n' + '\n'.join(sub_lines)
                i = j
            else:
                fm[k] = v
                i += 1
        else:
            i += 1

    fixed, remaining = [], []

    # 自动补全 defaults
    for field, value in defaults.items():
        if not fm.get(field, '').strip():
            fm[field] = value
            fixed.append(f'{field}={value}')

    def _norm_tag(t):
        t = t.strip().strip('[]').strip()
        if re.search(r'[\u4e00-\u9fff]', t):
            return t.lower()
        return t.lower().replace(' ', '-')

    # tags 格式修复：逗号分隔 → YAML 列表
    tags_raw = fm.get('tags', '')
    if tags_raw and ',' in tags_raw and not tags_raw.strip().startswith('-') and '[' not in tags_raw:
        raw_list = [t.strip() for t in tags_raw.split(',') if t.strip()]
        fm['tags'] = '\n  - ' + '\n  - '.join(_norm_tag(t) for t in raw_list)
        fixed.append('tags=YAML列表')

    # tags 方括号格式修复：- [item1  /  - item2] → 正常 YAML 列表
    tags_raw = fm.get('tags', '')
    if tags_raw and ('[' in tags_raw or ']' in tags_raw):
        tag_lines = [l for l in tags_raw.split('\n') if l.strip().startswith('-')]
        clean = [_norm_tag(l.lstrip('- ').strip()) for l in tag_lines]
        clean = [t for t in clean if t]
        if clean:
            fm['tags'] = '\n  - ' + '\n  - '.join(clean)
            fixed.append('tags=去方括号')

    # tags 大写修复
    tags_raw = fm.get('tags', '')
    if tags_raw.strip().startswith('-') or '\n  -' in tags_raw:
        tag_lines = [l for l in tags_raw.strip().split('\n') if l.strip().startswith('-')]
        new_lines = []
        for tl in tag_lines:
            tag_val = tl.lstrip('- ').strip()
            if tag_val and tag_val != tag_val.lower():
                new_lines.append(f'  - {tag_val.lower()}')
                fixed.append(f'tag-lowercase={tag_val}')
            else:
                new_lines.append(f'  - {tag_val}' if not tl.startswith('  ') else tl)
        fm['tags'] = '\n' + '\n'.join(new_lines)

    # 日期格式修复：YYYY-MM-DD（含 ISO 8601 时间戳）
    _date_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    for date_fld in ['publish_date', 'fetch_date']:
        val = fm.get(date_fld, '').strip().strip("'\"")
        if val and not _date_re.match(val):
            _extracted = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', val)
            if _extracted:
                y, mo, d = _extracted.groups()
                fm[date_fld] = f'{y}-{int(mo):02d}-{int(d):02d}'
                fixed.append(f'{date_fld}=日期格式修复')
            else:
                remaining.append(f'{date_fld}格式错误: {val!r}')

    # 单引号包裹修复：去掉不必要的单引号
    for k in list(fm.keys()):
        v = fm[k]
        if isinstance(v, str) and v.startswith("'") and v.endswith("'") and len(v) > 1:
            fm[k] = v[1:-1]
            fixed.append(f'{k}=去单引号')

    # 含冒号的文本字段加双引号（排除 URL、已引号、多行值）
    _text_fields = {'origin_title', 'description', 'author'}
    for k in _text_fields:
        v = fm.get(k, '')
        if not v or v.startswith('\n'):
            continue
        v = v.strip()
        if ':' in v and not v.startswith('"'):
            fm[k] = '"' + v.replace('"', '\\"') + '"'
            fixed.append(f'{k}=加引号')

    # 写回文件
    fm_lines = []
    for k, v in fm.items():
        if v.startswith('\n'):
            fm_lines.append(f'{k}:{v}')
        else:
            fm_lines.append(f'{k}: {v}')
    fm_str = '---\n' + '\n'.join(fm_lines) + '\n---\n'
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(fm_str + content[m.end():])

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


# ------------------------------------------------------------
# 10. load_fixed_tags: 读取固定词表文件
# ------------------------------------------------------------
def load_fixed_tags(path):
    """从分组注释文本文件中读取固定词表，跳过 # 注释行和空行。"""
    try:
        with open(path, encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip() and not line.startswith('#')}
    except FileNotFoundError:
        return set()


# ------------------------------------------------------------
# 11. move_fixed_from_candidate: 将候选集中命中固定词表的条目移入确定集
# ------------------------------------------------------------
def move_fixed_from_candidate(tags, candidate_tags, fixed_tags):
    """
    遍历 candidate_tags，命中 fixed_tags 的条目移入 tags（去重）。
    返回 (new_tags, new_candidate_tags)。
    """
    new_tags = list(tags)
    new_candidate = []
    for t in candidate_tags:
        if t in fixed_tags and t not in new_tags:
            new_tags.append(t)
        elif t not in fixed_tags:
            new_candidate.append(t)
    return new_tags, new_candidate


# ------------------------------------------------------------
# 12. enforce_tag_separation: 兜底移位（candidate → tags）
# ------------------------------------------------------------
def _replace_yaml_list_field(fm_raw, field, values):
    """在原始 frontmatter 文本中替换指定 YAML 列表字段，不触碰其余字段。"""
    if values:
        new_block = f'{field}:\n' + ''.join(f'  - {v}\n' for v in values)
    else:
        new_block = f'{field}: []\n'
    # 匹配 "field:" 行 + 后续缩进列表行
    pattern = re.compile(
        rf'^{re.escape(field)}:[ \t]*(?:\[\])?[ \t]*\n(?:  -[^\n]*\n)*',
        re.MULTILINE
    )
    if pattern.search(fm_raw):
        return pattern.sub(new_block, fm_raw)
    # 字段不存在：追加到末尾
    return fm_raw.rstrip('\n') + '\n' + new_block


def enforce_tag_separation(fp, fixed_tags_path):
    """
    读取 fixed_tags_path 词表，将 fp 文章中 candidate_tags 里命中词表的条目移入 tags。
    若 fixed_tags_path 不存在或 candidate_tags 无改动，则不写文件。
    """
    fixed = load_fixed_tags(fixed_tags_path)
    if not fixed:
        return

    with open(fp, encoding='utf-8') as f:
        content = f.read()

    if not content.startswith('---'):
        return

    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return

    fm_raw = m.group(1)
    rest = content[m.end():]

    fm_parsed = yaml.safe_load(fm_raw) or {}
    tags = [t for t in (fm_parsed.get('tags') or []) if t]
    candidate_tags = [t for t in (fm_parsed.get('candidate_tags') or []) if t]

    if not candidate_tags:
        return

    new_tags, new_candidate = move_fixed_from_candidate(tags, candidate_tags, fixed)
    if new_tags == tags and new_candidate == candidate_tags:
        return

    fm_raw = _replace_yaml_list_field(fm_raw, 'tags', new_tags)
    fm_raw = _replace_yaml_list_field(fm_raw, 'candidate_tags', new_candidate)

    with open(fp, 'w', encoding='utf-8') as f:
        f.write('---\n' + fm_raw.rstrip('\n') + '\n---' + rest)
