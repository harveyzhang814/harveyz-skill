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


# 仅在配置了 merge.post_steps 时插入模板的函数定义（模板里的 {{POST_STEPS_DEF}} 位置）
POST_STEPS_DEF = r"""# 合并后步骤：按 workflow-config.yml 的 merge.post_steps 顺序，在本次合并的 worktree 根目录
# 用 nohup sh -c 脱离启动，不等待它结束；启动失败只在 stderr 打一行警告，退出码与 stdout 不受影响。
# 占位符 {script_dir} {merge_commit} {base_commit} {feature_branch} 在这里按 printf %q 转义后替换，
# 命令里不要再给它们加引号；同时导出 MERGE_COMMIT MERGE_BASE_COMMIT MERGE_FEATURE_BRANCH MERGE_TARGET。
run_post_step() {
    local cmd="$1" root
    if ! root=$(git rev-parse --show-toplevel 2>/dev/null) || ! command -v nohup >/dev/null 2>&1; then
        echo "⚠️ 合并后步骤未能启动：$1" >&2
        return 0
    fi
    cmd=${cmd//\{script_dir\}/"$(printf '%q' "$MERGE_SCRIPT_DIR")"}
    cmd=${cmd//\{merge_commit\}/"$(printf '%q' "$POST_MERGE_COMMIT")"}
    cmd=${cmd//\{base_commit\}/"$(printf '%q' "$POST_BASE_COMMIT")"}
    cmd=${cmd//\{feature_branch\}/"$(printf '%q' "$feature_branch")"}
    # 只把 nohup 那一条放进后台：连 cd 一起 `&&` 后台化，子 shell 会一直握着调用方的 stdout 管道
    if ! (
        cd "$root" || exit 1
        MERGE_COMMIT="$POST_MERGE_COMMIT" MERGE_BASE_COMMIT="$POST_BASE_COMMIT" \
        MERGE_FEATURE_BRANCH="$feature_branch" MERGE_TARGET="$TARGET_BRANCH" \
        nohup sh -c "$cmd" >/dev/null 2>&1 &
    ) 2>/dev/null; then
        echo "⚠️ 合并后步骤未能启动：$1" >&2
    fi
    return 0
}

# $1 = 新的合并提交，$2 = 合并前 ${TARGET_BRANCH} 指向的提交
run_post_steps() {
    POST_MERGE_COMMIT="$1"
    POST_BASE_COMMIT="$2"
    # --- BEGIN MANAGED: merge/post-steps (hash:{{POST_STEPS_HASH}}) ---
{{POST_STEPS}}
    # --- END MANAGED: merge/post-steps ---
}

"""


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

    # 合并后步骤：post_steps 为空时，两处占位符整行去掉，生成的脚本与没有这个功能时逐字节一致。
    # 每条一行 run_post_step '<命令>'；{target} 此处替换，{script_dir}/{merge_commit}/{base_commit}/
    # {feature_branch} 由脚本在运行时替换（见模板里的 run_post_step）
    post_steps = resolved['post_steps']
    if post_steps:
        post_block = '\n'.join(
            "    run_post_step " + shlex.quote(cmd.replace('{target}', target))
            for cmd in post_steps
        )
        post_def = POST_STEPS_DEF.replace('{{POST_STEPS}}', post_block) \
                                 .replace('{{POST_STEPS_HASH}}', _block_hash(post_block))
    else:
        post_def = ''

    result = template
    # 空块时连同占位符所在的行一起去掉，BEGIN/END 两行紧挨
    result = result.replace('{{PRE_CHECKS}}\n', block + '\n' if block else '')
    result = result.replace('{{PRE_CHECKS_HASH}}', _block_hash(block))
    result = result.replace('{{POST_STEPS_DEF}}\n', post_def)
    result = result.replace('{{POST_STEPS_CALL}}\n',
                            '            run_post_steps "$new_commit" "$staging_head"\n' if post_steps else '')
    result = result.replace('{{TARGET_BRANCH}}', target)
    result = result.replace('{{INTEGRATION_BRANCHES}}', ' '.join(resolved['integration_branches']))
    result = result.replace('{{MERGE_TRAILER}}', resolved['merge_trailer'])
    result = result.replace('{{VERSION}}', version)
    return result
