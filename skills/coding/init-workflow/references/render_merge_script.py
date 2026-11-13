#!/usr/bin/env python3
"""
init-workflow 标准合并脚本渲染器
把 merge-script-template.sh 的占位符替换为解释器（workflow_resolve.resolve）给出的取值。
"""
import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from block_hash import block_hash as _block_hash  # noqa: E402,F401  与 hooks 同一实现


def render_merge_script(resolved, template, version):
    """渲染合并脚本；resolved 必须有合并目标（merge_target 非空）。"""
    target = resolved['merge_target']
    if not target:
        raise ValueError('resolved 没有 merge_target，不应渲染合并脚本')

    # 每条 pre_check 一行 run_pre_check '<命令>'；{target} 替换为合并目标，{script_dir} 替换为
    # 带引号的 "$MERGE_SCRIPT_DIR"（eval 时展开，路径含空格也安全）；shlex.quote 保证原样传给 eval
    block = '\n'.join(
        "run_pre_check " + shlex.quote(
            cmd.replace('{target}', target).replace('{script_dir}', '"$MERGE_SCRIPT_DIR"'))
        for cmd in resolved['pre_checks']
    )

    result = template
    # 空块时连同占位符所在的行一起去掉，BEGIN/END 两行紧挨
    result = result.replace('{{PRE_CHECKS}}\n', block + '\n' if block else '')
    result = result.replace('{{PRE_CHECKS_HASH}}', _block_hash(block))
    result = result.replace('{{TARGET_BRANCH}}', target)
    result = result.replace('{{INTEGRATION_BRANCHES}}', ' '.join(resolved['integration_branches']))
    result = result.replace('{{MERGE_TRAILER}}', resolved['merge_trailer'])
    result = result.replace('{{VERSION}}', version)
    return result
