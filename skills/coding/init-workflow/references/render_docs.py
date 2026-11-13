#!/usr/bin/env python3
"""
init-workflow Step 7 渲染器
从 workflow-config.yml 动态生成 docs/reference/git-workflow.md
"""
import sys, re, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from workflow_resolve import load_config, resolve  # noqa: E402

NOTES_BEGIN = '<!-- BEGIN PROJECT NOTES -->'
NOTES_END = '<!-- END PROJECT NOTES -->'

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


def render(config, resolved, template):
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

    # 拓扑：每个根分支写一次，来源逐级缩进展开；受保护分支的来源对齐在它名字下方
    def build_tree(name, indent, seen):
        lines = []
        for src in next(x for x in protected if x['name'] == name)['merge_from']:
            src_base = src.rstrip('/*')
            if src_base in all_names and src_base not in seen:
                lines.append(f'{indent}<- {src_base}')
                lines += build_tree(src_base, indent + ' ' * 5, seen | {src_base})
            else:
                lines.append(f'{indent}<- {src}')
        return lines

    roots = [b['name'] for b in protected if b['name'] not in merge_targets]
    ascii_lines = []
    for r in roots:
        ascii_lines += [r] + build_tree(r, '  ', {r})
    topology_ascii = '\n'.join(ascii_lines) if ascii_lines else ' <- '.join(b['name'] for b in protected)

    # ── BRANCH_TABLE ───────────────────────────────────────────────
    rows = ['| 分支 | 用途 | 合并目标 |', '|------|------|---------|']
    for b in protected:
        target = roots[0] if b['name'] != roots[0] else '—'
        rows.append(f'| `{b["name"]}` | {branch_purpose(b["name"])} | `{target}` |')
    for p in c['naming_patterns']:
        prefix = pattern_to_prefix(p)
        purpose, _ = pattern_purpose(prefix)
        # 与 resolved.env 一致：分支类型并入 base.<类型>；解释器没给出时不猜
        target_branch = resolved['base'].get(prefix.rstrip('/'), '—')
        rows.append(f'| `{prefix}<名称>` | {purpose} | `{target_branch}` |')
    branch_table = '\n'.join(rows)

    # ── PROTECTION_RULES ──────────────────────────────────────────
    rule_lines = []
    target = resolved['merge_target']
    for b in protected:
        sources = '、'.join(f'`{s}`' for s in b['merge_from'])
        if b['name'] == target:
            # 合并目标：pre-commit 只管直接提交；合并来源不再检查，只认合并脚本留下的标记
            direct = ('直接提交时发出警告（不阻断）' if b['allow_direct_commit']
                      else '禁止直接提交')
            rule_lines.append(
                f'- **`{target}`** — {direct}（`.githooks/pre-commit`）。'
                f'合并只经 `{resolved["merge_script"]}` 进行，任何非集成分支都用它合并进来；'
                f'合并提交须带 `{resolved["merge_trailer"]}` 行，缺少该行的合并提交由 '
                f'`.githooks/commit-msg` 拒绝，推送时由 `.githooks/pre-push` 拒绝'
                f'（远端同步合并 `Merge branch \'{target}\' of …` 除外）。')
        elif b['allow_direct_commit']:
            rule_lines.append(f'- **`{b["name"]}`** — 直接提交时发出警告（不阻断）。合并来源建议为 {sources}。')
        else:
            rule_lines.append(f'- **`{b["name"]}`** — 禁止直接提交。只接受来自 {sources} 的合并。')
    protection_rules = '\n'.join(rule_lines)

    # ── WORKFLOW EXAMPLES ─────────────────────────────────────────
    integration = next((b['name'] for b in protected if b['name'] not in roots), roots[0] if roots else 'staging')
    main_branch = roots[0] if roots else 'main'
    wt_dir = resolved['worktree_dir']

    # 开始新工作：manage-worktree「准备」+ 未安装时的兜底命令（按基线分支分组）
    by_base = {}
    for t, base_branch in resolved['base'].items():
        by_base.setdefault(base_branch, []).append(f'{t}/')
    if not by_base:
        by_base[integration] = []
    fallback_lines = []
    for base_branch, prefixes in by_base.items():
        line = f'git worktree add {wt_dir}/<分支名，/ 换成 +> -b <分支> {base_branch}'
        if prefixes:
            line += '   # ' + ' '.join(prefixes)
        fallback_lines.append(line)
    start_section = (
        '调用 `manage-worktree「准备」`建立并进入本任务的 worktree。'
        '不要在主工作树里切换分支。\n\n'
        '未安装 `manage-worktree` 时的兜底命令（基线分支按分支类型而定）：\n\n'
        '```bash\n' + '\n'.join(fallback_lines) + '\n```'
    )

    # 合并到集成分支：有合并目标 → 合并脚本；否则保留通用 git merge
    if target:
        if resolved['pre_checks']:
            checks = '\n'.join(f'{i}. `{cmd}`' for i, cmd in enumerate(resolved['pre_checks'], 1))
            checks_text = (f'合并前依次执行以下检查（在被合并分支的 worktree 根目录运行，'
                           f'`{{target}}` 即 `{target}`），任一失败即中止、不合并：\n\n{checks}')
        else:
            checks_text = '合并前检查：未配置（`merge.pre_checks` 为空）。'
        merge_section = (
            f'调用 `manage-worktree「合并」`，或在被合并分支的 worktree 里直接运行 '
            f'`{resolved["merge_script"]}`。\n\n'
            f'- 只更新本地 `{target}`，不会推送；`git push` 另行进行。\n'
            f'- 禁止手动切到 `{target}` 再 `git merge`：合并提交必须带 '
            f'`{resolved["merge_trailer"]}` 标记，缺少该标记的手动合并会被 hook 拒绝。\n\n'
            + checks_text
        )
    else:
        merge_section = (
            f'在 `{integration}` 所在的工作区里合并（不要在主工作树里切换分支）：\n\n'
            f'```bash\ngit merge <分支>\ngit push\n```'
        )

    # 发布到主分支：不切换主工作树，交给项目自己的发布流程
    if integration != main_branch:
        release_section = (f'把 `{integration}` 发布到 `{main_branch}` 由项目自己的发布流程负责'
                           f'（如 `release-project`），不要为此在主工作树里切换分支。')
    else:
        release_section = ('发布由项目自己的发布流程负责（如 `release-project`），'
                           '不要为此在主工作树里切换分支。')

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
    if release_p and target and target != main_branch:
        faq.append(f'**Q：需要紧急热修复直接上 {main_branch} 怎么办？**\n'
                   f'A：从 {main_branch} 切一个 `release/*` 分支，修复后按项目发布流程合并到 {main_branch}；'
                   f'再在这个 `release/*` 分支的 worktree 里调用 `manage-worktree「合并」`'
                   f'（或直接运行 `{resolved["merge_script"]}`）把修复带回 {target}，'
                   f'不要手动 `git merge` 进 {target}。')
    elif release_p and target:
        faq.append(f'**Q：需要紧急热修复直接上 {main_branch} 怎么办？**\n'
                   f'A：从 {main_branch} 切一个 `release/*` 分支，修复后在它的 worktree 里调用 '
                   f'`manage-worktree「合并」`（或直接运行 `{resolved["merge_script"]}`）合并到 {main_branch}。')
    elif release_p:
        faq.append(f'**Q：需要紧急热修复直接上 {main_branch} 怎么办？**\n'
                   f'A：从 {main_branch} 切一个 `release/*` 分支，修复后合并到 {main_branch}，再反向合并到 {integration}。')
    if target:
        faq.append(f'**Q：怎么把远端的 {target} 同步到本地？**\n'
                   f'A：用快进同步：`git pull --ff-only`（或 `git merge --ff-only origin/{target}`）。'
                   f'本仓库设置了 `merge.ff=false`，直接 `git merge origin/{target}` 会生成一个 '
                   f'"Merge remote-tracking branch …" 合并提交，它不带 `{resolved["merge_trailer"]}` 行，'
                   f'会被 commit-msg 拒绝（只放行 `Merge branch \'{target}\' of …` 形式的远端同步合并）。')
        faq.append(f'**Q：手动合并被拒后怎么办？**\n'
                   f'A：被 commit-msg 拒绝后合并仍处于进行中，先 `git merge --abort` 撤销，'
                   f'再到被合并分支的 worktree 里运行 `{resolved["merge_script"]}`。'
                   f'`git merge --ff-only <功能分支>` 这类快进不产生提交，本地不会被拦，'
                   f'要到推送 {target} 时才被 pre-push 拒绝；快进只用于同步远端 {target}。')
        faq.append(f'**Q：第一次推送 {target} 被拒怎么办？**\n'
                   f'A：远端还没有 {target} 时，pre-push 只检查它的尖端；尖端若不是合并脚本产生的合并'
                   f'（例如刚初始化、还没合并过任何分支），就会被拒。先用 `{resolved["merge_script"]}` '
                   f'合并一个分支再推送即可；确认要原样发布时，执行一次 `git push --no-verify -u origin {target}`。')
        faq.append(f'**Q：合并后 worktree 和分支怎么处理？**\n'
                   f'A：确认不再需要后，在主工作树执行 `git worktree remove <worktree 路径>` 收掉工作区，'
                   f'再 `git branch -d <分支>` 删除已合并的分支（`-d` 会拒绝删除尚未合并进当前分支的分支）。'
                   f'交接中的工作区要等验收、合并都完成后再收。')
    faq_section = '\n\n'.join(faq)

    # ── 替换占位符 ─────────────────────────────────────────────────
    result = template
    result = result.replace('{{BRANCH_TOPOLOGY_ASCII}}',    topology_ascii)
    result = result.replace('{{BRANCH_TABLE}}',             branch_table)
    result = result.replace('{{PROTECTION_RULES}}',         protection_rules)
    result = result.replace('{{WORKFLOW_START_SECTION}}',   start_section)
    result = result.replace('{{WORKFLOW_MERGE_SECTION}}',   merge_section)
    result = result.replace('{{WORKFLOW_RELEASE_SECTION}}', release_section)
    result = result.replace('{{NAMING_TABLE}}',             naming_table)
    result = result.replace('{{NAMING_EXEMPT}}',            naming_exempt)
    result = result.replace('{{COMMIT_FORMAT_SECTION}}',    commit_section)
    result = result.replace('{{FAQ_SECTION}}',              faq_section + '\n\n' if faq_section else '')
    return result


def _notes_span(text):
    """返回 (标记之间内容的起点, 终点)；缺任一标记或顺序颠倒返回 None。"""
    b = text.find(NOTES_BEGIN)
    if b == -1:
        return None
    start = b + len(NOTES_BEGIN)
    e = text.find(NOTES_END, start)
    return None if e == -1 else (start, e)


def carry_notes(existing, rendered):
    """把现有文档自填区标记之间的内容逐字节搬入新渲染结果。

    返回 (最终文本, 是否需要 WARN)。现有文件没有（完整的）标记且内容与新渲染不同
    → 照旧覆盖并要求 WARN。
    """
    if existing is None:
        return rendered, False
    old, new = _notes_span(existing), _notes_span(rendered)
    if old and new:
        return rendered[:new[0]] + existing[old[0]:old[1]] + rendered[new[1]:], False
    return rendered, existing != rendered


if __name__ == '__main__':
    config_path   = sys.argv[1]
    template_path = sys.argv[2]
    output_path   = sys.argv[3]

    config   = load_config(config_path)
    resolved = resolve(config, config_path)
    with open(template_path, encoding='utf-8') as f:
        template = f.read()
    rendered = render(config, resolved, template)

    # 差量写入（newline='' 保持字节原样，自填区内容不被换行转换）
    existing = None
    if os.path.exists(output_path):
        with open(output_path, encoding='utf-8', newline='') as f:
            existing = f.read()
    final, warn = carry_notes(existing, rendered)
    if warn:
        print(f'WARN {output_path} 没有项目自填区标记，现有内容已被覆盖；'
              f'找回手改内容：git diff HEAD -- {output_path}')
    if existing == final:
        print('UNCHANGED')
    else:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            f.write(final)
        print('UPDATED' if existing is not None else 'NEW')
