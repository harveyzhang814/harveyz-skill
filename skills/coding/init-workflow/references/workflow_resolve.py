#!/usr/bin/env python3
"""
init-workflow 单一解释器
读取 workflow-config.yml（手写 YAML 子集解析，仅标准库），推断集成分支、分支类型基线、
合并目标等，输出 resolved.env。render_docs.py 的配置解析也来自这里。
"""
import os
import re

INIT_WORKFLOW_VERSION = "5.0.2"
RULE_FILE_CANDIDATES = (
    ".hskill/init-workflow/workflow-config.yml",
    "workflow-config.yml",
    ".claude/workflow-config.yml",
)


def find_rule_file(repo_root):
    """按三级查找返回第一个存在的规则文件（相对 repo_root 的路径），都没有返回 None。"""
    for rel in RULE_FILE_CANDIDATES:
        if os.path.isfile(os.path.join(repo_root, rel)):
            return rel
    return None


class ConfigError(ValueError):
    """配置解释不出必需的取值（如受保护分支为空）；部署须停下，不得静默省略。"""


def _scalar(text):
    """取一个 YAML 标量：引号内原样（不反转义），无引号时去掉 ` #` 起的行内注释。"""
    s = text.strip()
    if s[:1] in ('"', "'"):
        end = s.find(s[0], 1)
        return s[1:end] if end != -1 else s[1:]
    return re.split(r'\s#', s, maxsplit=1)[0].strip()


def _inline_list(text):
    """解析以 `[` 开头的行内列表，引号内的 `,` 与 `]` 不算分隔；返回 (项列表, 是否闭合)。"""
    items, buf, quote = [], '', None
    for ch in text[1:]:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
            buf += ch
        elif ch in (',', ']'):
            if buf.strip():
                items.append(_scalar(buf))
            buf = ''
            if ch == ']':
                return items, True
        else:
            buf += ch
    return items, False


def _indent(line):
    return len(line) - len(line.lstrip(' \t'))


def _parse_protected(content):
    """解析 branches.protected：块列表或行内 merge_from 均可，缩进任意但须一致。

    每项为 {'name', 'allow_direct_commit', 'merge_from'}。写了块写法的 `merge_from:`
    却没解析出任何条目 → ConfigError（行内 `merge_from: []` 是明确的空列表，不算）。
    """
    lines = content.splitlines()
    start = next((i for i, l in enumerate(lines)
                  if re.match(r'^[ \t]+protected:[ \t]*(#.*)?$', l)
                  or re.match(r'^[ \t]+protected:[ \t]*\[', l)), None)
    if start is None:
        return []
    head = lines[start]
    head_indent = _indent(head)
    rest = head.split(':', 1)[1].strip()
    if rest.startswith('['):
        return []  # 行内写法只可能是空列表 []；非空时无法表达各分支的字段

    protected, current, mf_indent, block_declared = [], None, None, set()
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        ind = _indent(line)
        # 缩进回到 protected: 及以外、且不是同级的列表项 → 本节结束
        if ind < head_indent or (ind == head_indent and not stripped.startswith('-')):
            break
        m = re.match(r'^-[ \t]+name:[ \t]*(.*)$', stripped)
        if m:
            current = {'name': _scalar(m.group(1)), 'allow_direct_commit': False,
                       'merge_from': []}
            protected.append(current)
            mf_indent = None
            continue
        if current is None:
            continue
        if mf_indent is not None and stripped.startswith('- ') and ind >= mf_indent:
            current['merge_from'].append(_scalar(stripped[2:]))
            continue
        mf_indent = None
        m = re.match(r'^allow_direct_commit:[ \t]*(true|false)\b', stripped)
        if m:
            current['allow_direct_commit'] = m.group(1) == 'true'
            continue
        m = re.match(r'^merge_from:[ \t]*(.*)$', stripped)
        if m:
            value = m.group(1).strip()
            if value.startswith('['):
                current['merge_from'], _ = _inline_list(value)
            else:
                block_declared.add(id(current))
                mf_indent = ind
    for b in protected:
        if id(b) in block_declared and not b['merge_from']:
            raise ConfigError(
                f"branches.protected 中 {b['name']} 写了 merge_from 却没有解析出任何条目；"
                "请写成 `- <来源>` 逐行列表或行内 [a, \"b/*\"]，明确为空写 merge_from: []")
    return protected


def load_config(path):
    """简单 YAML 解析（只处理此 skill 使用的字段，无需完整 YAML 库）"""
    content = open(path).read()

    def extract_list_under(key, text):
        """取第一个 `key:` 下的列表：块列表（- value）或行内列表 [a, "b"]。"""
        m = re.search(rf'^[ \t]*{re.escape(key)}:[ \t]*(.*)$', text, re.M)
        if not m:
            return []
        value = m.group(1).strip()
        if value.startswith('['):
            return _inline_list(value)[0]
        items = []
        for l in text[m.end():].split('\n')[1:]:
            if not re.match(r'^[ \t]*- ', l):
                break
            items.append(re.sub(r'^[ \t]*- ', '', l).strip().strip('"'))
        return items

    # 提取 branches.protected
    protected = _parse_protected(content)

    # branch_naming
    naming_patterns = extract_list_under('allowed_patterns', content)
    naming_exempt   = extract_list_under('exempt', content)

    # commit_message
    fmt_m = re.search(r'format:\s*(\S+)', content)
    fmt = fmt_m.group(1) if fmt_m else 'none'
    types = extract_list_under('types', content)
    pattern_m = re.search(r'pattern:\s*"([^"]+)"', content)
    regex_pattern = pattern_m.group(1) if pattern_m else ''
    max_len_m = re.search(r'max_subject_length:\s*(\d+)', content)
    max_len = int(max_len_m.group(1)) if max_len_m else 72

    # worktree.dir / merge.pre_checks（旧配置没有这两节时取默认值）
    wt_m = re.search(r'^worktree:[ \t]*(?:#[^\n]*)?\n((?:[ \t]+.*\n?|[ \t]*\n)*)', content, re.M)
    dir_m = re.search(r'^[ \t]+dir:[ \t]*["\']?([^\s"\'#]+)', wt_m.group(1), re.M) if wt_m else None
    worktree_dir = dir_m.group(1) if dir_m else '.worktrees'
    merge_m = re.search(r'^merge:[ \t]*(?:#[^\n]*)?\n((?:[ \t]+.*\n?|[ \t]*\n)*)', content, re.M)
    pre_checks = extract_list_under('pre_checks', merge_m.group(1)) if merge_m else []

    return {
        'protected': protected,
        'naming_patterns': naming_patterns,
        'naming_exempt': naming_exempt,
        'commit_format': fmt,
        'commit_types': types,
        'commit_regex': regex_pattern,
        'max_subject_length': max_len,
        'worktree_dir': worktree_dir,
        'pre_checks': pre_checks,
    }

def _branch_types(patterns):
    """从形如 ^<type>/ 的 allowed_patterns 取分支类型，保持配置顺序、去重。"""
    types = []
    for p in patterns:
        m = re.match(r'^\^([A-Za-z0-9_-]+)/', p)
        if m and m.group(1) not in types:
            types.append(m.group(1))
    return types


def resolve(config, rule_file):
    """从 load_config 的结果推断 resolved.env 的全部取值。

    受保护分支解析为空 → ConfigError：没有集成分支就推不出基线与合并目标，
    不得静默写出一份缺键的 resolved.env。
    """
    protected = config['protected']
    if not protected:
        raise ConfigError(
            f'{rule_file} 的 branches.protected 没有解析出任何分支（缺这一节、写成空列表，'
            '或写法无法识别）；集成分支、基线与合并目标都推不出，不部署')
    base = {}
    for t in _branch_types(config['naming_patterns']):
        for b in protected:
            if f'{t}/*' in b['merge_from']:
                base[t] = b['name']
                break

    merge_target = base.get('feature')
    resolved = {
        'rule_file': rule_file,
        'integration_branches': [b['name'] for b in protected],
        'base': base,
        'merge_target': merge_target,
        'merge_script': f'scripts/merge-to-{merge_target}.sh' if merge_target else None,
        'merge_trailer': f'Merge-Via: merge-to-{merge_target}.sh' if merge_target else None,
        'worktree_dir': config.get('worktree_dir', '.worktrees'),
        # YAML 双引号里的 \\ 是一个反斜杠；消费方拿到的是最终的 ERE
        'naming': [p.replace('\\\\', '\\') for p in config['naming_patterns']],
        'naming_exempt': list(config['naming_exempt']),
        'pre_checks': list(config.get('pre_checks', [])),
    }
    return resolved


def format_env(resolved, version):
    """渲染 resolved.env 文本；消费方逐行读取，不得 source。"""
    lines = [
        f"# Generated by init-workflow {version} from {resolved['rule_file']}; "
        "do not edit, rerun init-workflow",
        'schema=1',
        f"rule_file={resolved['rule_file']}",
        f"integration_branches={' '.join(resolved['integration_branches'])}",
    ]
    for t, b in resolved['base'].items():
        lines.append(f'base.{t}={b}')
    if resolved['merge_target']:
        lines.append(f"merge_target={resolved['merge_target']}")
        lines.append(f"merge_script={resolved['merge_script']}")
        lines.append(f"merge_trailer={resolved['merge_trailer']}")
    lines.append(f"worktree_dir={resolved['worktree_dir']}")
    for i, p in enumerate(resolved['naming'], 1):
        lines.append(f'naming.{i}={p}')
    lines.append(f"naming_exempt={' '.join(resolved['naming_exempt'])}")
    return '\n'.join(lines) + '\n'


def parse_env(text):
    """逐行解析 key=value，跳过 # 注释与空行。"""
    env = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        key, _, value = line.partition('=')
        env[key] = value
    return env
