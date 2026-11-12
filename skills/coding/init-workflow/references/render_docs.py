#!/usr/bin/env python3
"""
init-workflow Step 7 渲染器
从 workflow-config.yml 动态生成 docs/reference/git-workflow.md
"""
import sys, re, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from workflow_resolve import load_config  # noqa: E402

def branch_purpose(name):
    mapping = {
        'main': '生产就绪代码', 'master': '生产就绪代码',
        'staging': '集成 / 预发布', 'develop': '开发集成',
    }
    if name in mapping:
        return mapping[name]
    if name.startswith('release'):
        return '发版准备'
    return '—'


def pattern_to_prefix(p):
    """^feature/.+ → feature/"""
    m = re.match(r'^\^?([a-z]+)/', p)
    return m.group(1) + '/' if m else p


def pattern_purpose(prefix):
    mapping = {
        'feature/': ('新功能', 'feature/user-auth、feature/dark-mode'),
        'fix/':     ('Bug 修复', 'fix/login-crash、fix/null-pointer'),
        'chore/':   ('维护、依赖升级等', 'chore/upgrade-deps、chore/ci-timeout'),
        'doc/':     ('文档更新', 'doc/api-reference、doc/onboarding'),
        'docs/':    ('文档更新', 'docs/api-reference、docs/onboarding'),
        'release/': ('发版切点', 'release/1.2.0'),
        'hotfix/':  ('紧急热修复', 'hotfix/login-crash'),
    }
    return mapping.get(prefix, ('—', f'{prefix}example'))


def render(config, template):
    c = config
    protected = c['protected']

    # ── BRANCH_TOPOLOGY_ASCII ──────────────────────────────────────
    # 找主分支（没有其他受保护分支 merge_from 到它的最顶层）
    all_names = {b['name'] for b in protected}
    merge_targets = set()
    for b in protected:
        for mf in b['merge_from']:
            # mf 可能是 glob，提取固定前缀
            base = mf.rstrip('/*')
            if base in all_names:
                merge_targets.add(base)

    # 拓扑：逐级展开
    def build_tree(root, depth=0):
        b = next((x for x in protected if x['name'] == root), None)
        if not b:
            return ''
        indent = '  ' * depth
        lines = [indent + root]
        for src in b['merge_from']:
            src_base = src.rstrip('/*')
            if src_base in all_names:
                lines.append(build_tree(src_base, depth + 1))
            else:
                lines.append('  ' * (depth + 1) + f'<- {src}')
        return '\n'.join(l for l in lines if l)

    roots = [b['name'] for b in protected if b['name'] not in merge_targets]
    ascii_lines = []
    for r in roots:
        for src in next(x for x in protected if x['name'] == r)['merge_from']:
            src_base = src.rstrip('/*')
            if src_base in all_names:
                sub = next((x for x in protected if x['name'] == src_base), None)
                ascii_lines.append(f'{r}')
                ascii_lines.append(f'  <- {src_base}')
                for subsrc in (sub['merge_from'] if sub else []):
                    ascii_lines.append(f'        <- {subsrc}')
            else:
                ascii_lines.append(f'{r}')
                ascii_lines.append(f'  <- {src}')
    topology_ascii = '\n'.join(ascii_lines) if ascii_lines else ' <- '.join(b['name'] for b in protected)

    # ── BRANCH_TABLE ───────────────────────────────────────────────
    rows = ['| 分支 | 用途 | 合并目标 |', '|------|------|---------|']
    for b in protected:
        target = roots[0] if b['name'] != roots[0] else '—'
        rows.append(f'| `{b["name"]}` | {branch_purpose(b["name"])} | `{target}` |')
    for p in c['naming_patterns']:
        prefix = pattern_to_prefix(p)
        purpose, _ = pattern_purpose(prefix)
        target_branch = next((b['name'] for b in protected if b['name'] not in roots), roots[0] if roots else '—')
        rows.append(f'| `{prefix}<名称>` | {purpose} | `{target_branch}` |')
    branch_table = '\n'.join(rows)

    # ── PROTECTION_RULES ──────────────────────────────────────────
    rule_lines = []
    for b in protected:
        sources = '、'.join(f'`{s}`' for s in b['merge_from'])
        if b['allow_direct_commit']:
            rule_lines.append(f'- **`{b["name"]}`** — 直接提交时发出警告（不阻断）。合并来源建议为 {sources}。')
        else:
            rule_lines.append(f'- **`{b["name"]}`** — 禁止直接提交。只接受来自 {sources} 的合并。')
    protection_rules = '\n'.join(rule_lines)

    # ── WORKFLOW EXAMPLES ─────────────────────────────────────────
    integration = next((b['name'] for b in protected if b['name'] not in roots), roots[0] if roots else 'staging')
    main_branch = roots[0] if roots else 'main'
    checkout_ex = f'git checkout {integration}'
    merge_ex     = f'git checkout {integration}\ngit merge feature/my-feature'
    release_ex   = f'git checkout {main_branch}\ngit merge {integration}       # 或：git merge release/x.y.z\ngit push'

    # ── NAMING_TABLE ──────────────────────────────────────────────
    naming_rows = ['| 前缀 | 适用场景 | 示例 |', '|------|---------|------|']
    for p in c['naming_patterns']:
        prefix = pattern_to_prefix(p)
        purpose, example = pattern_purpose(prefix)
        naming_rows.append(f'| `{prefix}` | {purpose} | `{example}` |')
    naming_table = '\n'.join(naming_rows)

    # ── NAMING_EXEMPT ─────────────────────────────────────────────
    naming_exempt = '、'.join(f'`{e}`' for e in c['naming_exempt']) or '无'

    # ── COMMIT_FORMAT_SECTION ─────────────────────────────────────
    if c['commit_format'] == 'conventional':
        types_line = ' | '.join(f'`{t}`' for t in c['commit_types'])
        commit_section = f"""遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<类型>(<范围>): <简短描述>

[可选正文]

[可选 footer]
```

**类型：** {types_line}

**首行长度限制：** {c['max_subject_length']} 个字符"""
    elif c['commit_format'] == 'regex':
        commit_section = f"""提交信息首行必须匹配正则：

```
{c['commit_regex']}
```

**首行长度限制：** {c['max_subject_length']} 个字符"""
    else:
        commit_section = '本项目无提交信息格式要求。'

    # ── FAQ_SECTION ───────────────────────────────────────────────
    faq = []
    if integration != main_branch:
        faq.append(f'**Q：在 {integration} 上提交被拒绝怎么办？**\n'
                   f'A：你正在直接向 {integration} 提交。请新建分支，在新分支提交后再合并回 {integration}。')
    release_p = [p for p in c['naming_patterns'] if 'release' in p]
    if release_p:
        faq.append(f'**Q：需要紧急热修复直接上 {main_branch} 怎么办？**\n'
                   f'A：从 {main_branch} 切一个 `release/*` 分支，修复后合并到 {main_branch}，再反向合并到 {integration}。')
    faq_section = '\n\n'.join(faq)

    # ── 替换占位符 ─────────────────────────────────────────────────
    result = template
    result = result.replace('{{BRANCH_TOPOLOGY_ASCII}}',    topology_ascii)
    result = result.replace('{{BRANCH_TABLE}}',             branch_table)
    result = result.replace('{{PROTECTION_RULES}}',         protection_rules)
    result = result.replace('{{WORKFLOW_CHECKOUT_EXAMPLE}}', checkout_ex)
    result = result.replace('{{WORKFLOW_MERGE_EXAMPLE}}',   merge_ex)
    result = result.replace('{{WORKFLOW_RELEASE_EXAMPLE}}', release_ex)
    result = result.replace('{{NAMING_TABLE}}',             naming_table)
    result = result.replace('{{NAMING_EXEMPT}}',            naming_exempt)
    result = result.replace('{{COMMIT_FORMAT_SECTION}}',    commit_section)
    result = result.replace('{{FAQ_SECTION}}',              faq_section + '\n\n' if faq_section else '')
    return result


if __name__ == '__main__':
    config_path   = sys.argv[1]
    template_path = sys.argv[2]
    output_path   = sys.argv[3]

    config   = load_config(config_path)
    template = open(template_path).read()
    rendered = render(config, template)

    # 差量写入
    existing = open(output_path).read() if os.path.exists(output_path) else None
    if existing == rendered:
        print('UNCHANGED')
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        open(output_path, 'w').write(rendered)
        print('UPDATED' if existing else 'NEW')
