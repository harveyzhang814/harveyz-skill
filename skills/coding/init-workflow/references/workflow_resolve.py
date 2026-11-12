#!/usr/bin/env python3
"""
init-workflow 单一解释器
读取 workflow-config.yml（手写 YAML 子集解析，仅标准库），推断集成分支、分支类型基线、
合并目标等，输出 resolved.env。render_docs.py 的配置解析也来自这里。
"""
import os
import re

INIT_WORKFLOW_VERSION = "5.0.0"
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


def load_config(path):
    """简单 YAML 解析（只处理此 skill 使用的字段，无需完整 YAML 库）"""
    content = open(path).read()

    def extract_list_under(key, text):
        """提取某个 key 下的列表项（- value 或 - "value"）"""
        pattern = rf'{re.escape(key)}:[ \t]*(?:#[^\n]*)?\n((?:[ \t]+- .+\n?)+)'
        m = re.search(pattern, text)
        if not m:
            # 尝试行内列表 [a, b, c]
            m2 = re.search(rf'{re.escape(key)}:\s*\[([^\]]+)\]', text)
            if m2:
                return [v.strip().strip('"') for v in m2.group(1).split(',')]
            return []
        return [re.sub(r'^[ \t]+- ', '', l).strip().strip('"')
                for l in m.group(1).splitlines() if l.strip().startswith('- ')]

    # 提取 branches.protected
    protected = []
    in_protected = False
    current = None
    for line in content.splitlines():
        if re.match(r'\s+protected:', line):
            in_protected = True
            continue
        if in_protected:
            m = re.match(r'\s{4}- name:\s+(\S+)', line)
            if m:
                if current:
                    protected.append(current)
                current = {'name': m.group(1), 'allow_direct_commit': False, 'merge_from': []}
            elif current and re.match(r'\s+allow_direct_commit:\s*(true|false)', line):
                current['allow_direct_commit'] = 'true' in line
            elif current and re.match(r'\s+merge_from:', line):
                pass  # next lines are the list
            elif current and re.match(r'\s{8}- ', line):
                val = line.strip().lstrip('- ').strip('"')
                current['merge_from'].append(val)
            elif line.strip() and not line.startswith(' '):
                in_protected = False
    if current:
        protected.append(current)

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
    """从 load_config 的结果推断 resolved.env 的全部取值。"""
    protected = config['protected']
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
