#!/usr/bin/env python3
"""
init-workflow 起步引导（Step 9，写完 lock 文件之后）
让仓库具备开始工作的分支：全新仓库（还没有提交）在根集成分支上做一个只含部署产物的根提交；
本地缺少的集成分支从远端同名分支或其上游建出；最后提醒合并目标分支上推送会被 pre-push 拒绝的提交。
先算出完整计划再动手：任何一步推不出来就在改动之前停下。

用法：python3 bootstrap_branches.py <repo_root> [--dry-run]
stdout 逐行：ROOT-COMMIT <分支> / CREATE <分支> <来源> / EXISTS <分支> /
             WARN unpushed <分支> <数量> / WARN first-publish <分支>；--dry-run 时末行 DRY-RUN
退出码：0 正常；2 找不到规则文件；3 配置推不出分支顺序；4 已有提交的仓库缺根集成分支
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deploy_artifacts import DOC_PATH, ENV_PATH  # noqa: E402
from workflow_resolve import ConfigError, find_rule_file, load_config, resolve  # noqa: E402

ROOT_COMMIT_MSG = 'chore: initialize git workflow'


class BootstrapError(RuntimeError):
    """仓库状态推不出安全的做法（如已有提交却没有根集成分支）；须由用户决定。"""


def branch_order(protected):
    """返回 [(分支, 上游或 None)]，根在前。上游 = merge_from 里列出该分支的那个受保护分支。"""
    names = [b['name'] for b in protected]
    upstream = {}
    for b in protected:
        for src in b['merge_from']:
            if src in names and src not in upstream:
                upstream[src] = b['name']
    roots = [n for n in names if n not in upstream]
    if len(roots) != 1:
        raise ConfigError(
            f'branches.protected 应恰有一个根分支（不出现在其他受保护分支的 merge_from 里），'
            f'实际为 {roots or "无（存在循环）"}')
    order = [(roots[0], None)]
    while len(order) < len(names):
        placed = {n for n, _ in order}
        nxt = [(n, upstream[n]) for n in names if n not in placed and upstream[n] in placed]
        if not nxt:
            raise ConfigError(f'branches.protected 的 merge_from 存在循环：{sorted(set(names) - placed)}')
        order.extend(nxt)
    return order


def _git(repo, *args, check=True):
    r = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise BootstrapError(f'git {" ".join(args)} 失败：{r.stderr.strip()}')
    return r


def _has_ref(repo, ref):
    return _git(repo, 'show-ref', '--verify', '-q', ref, check=False).returncode == 0


def _marked(message, target, trailer):
    lines = message.split('\n')
    return trailer in lines or lines[0].startswith(f"Merge branch '{target}' of ")


def _push_warning(repo, target, trailer, tip):
    """合并目标推送时 pre-push/merge-via 会拒绝的情况；没有远端或无需提醒时返回 None。"""
    if not _git(repo, 'remote', check=False).stdout.strip():
        return None
    up = _git(repo, 'rev-parse', '-q', '--verify', f'{target}@{{upstream}}', check=False)
    remote = up.stdout.strip() if up.returncode == 0 else None
    if remote is None and _has_ref(repo, f'refs/remotes/origin/{target}'):
        remote = f'refs/remotes/origin/{target}'
    if remote is None:
        tip_msg = _git(repo, 'log', '-1', '--format=%B', tip).stdout if tip else ''
        return None if tip and _marked(tip_msg.strip(), target, trailer) else ('WARN', 'first-publish', target)
    log = _git(repo, 'log', '--first-parent', '--format=%B%x1e', f'{remote}..{tip}').stdout
    n = sum(1 for m in log.split('\x1e') if m.strip() and not _marked(m.strip(), target, trailer))
    return ('WARN', 'unpushed', target, str(n)) if n else None


def bootstrap(repo_root, dry_run=False):
    rule_file = find_rule_file(repo_root)
    if rule_file is None:
        raise FileNotFoundError('找不到 workflow-config.yml（三级查找均不存在）')
    config = load_config(os.path.join(repo_root, rule_file))
    resolved = resolve(config, rule_file)
    order = branch_order(config['protected'])

    # 1. 先算计划：每个受保护分支是已存在、从哪建、还是做根提交
    unborn = _git(repo_root, 'rev-parse', '-q', '--verify', 'HEAD', check=False).returncode != 0
    plan, tips = [], {}
    for name, up in order:
        if _has_ref(repo_root, f'refs/heads/{name}'):
            plan.append(('EXISTS', name))
            tips[name] = name
        elif _has_ref(repo_root, f'refs/remotes/origin/{name}'):
            plan.append(('CREATE', name, f'origin/{name}'))
            tips[name] = f'origin/{name}'
        elif up is not None:
            plan.append(('CREATE', name, up))
            tips[name] = tips[up]
        elif unborn:
            plan.append(('ROOT-COMMIT', name))
            tips[name] = None
        else:
            raise BootstrapError(
                f'仓库已有提交，但根集成分支 {name} 在本地和 origin 都不存在；'
                f'不猜测从哪建，请先确定 {name} 的来源（例如 git branch -m <现有默认分支> {name}）后重跑')

    target = resolved['merge_target']
    warning = _push_warning(repo_root, target, resolved['merge_trailer'], tips.get(target)) \
        if target and target in tips else None

    if dry_run:
        return plan + ([warning] if warning else [])

    # 2. 按计划执行；根提交只收部署产物，绕过已生效的 hooks（它们禁止在集成分支上直接提交）
    for step in plan:
        if step[0] == 'ROOT-COMMIT':
            _git(repo_root, 'symbolic-ref', 'HEAD', f'refs/heads/{step[1]}')
            paths = [p for p in (rule_file, ENV_PATH, DOC_PATH, '.githooks',
                                 resolved['merge_script'], '.gitignore')
                     if p and os.path.exists(os.path.join(repo_root, p))]
            _git(repo_root, 'add', '--', *paths)
            _git(repo_root, '-c', 'core.hooksPath=/dev/null', 'commit', '-q', '--no-verify',
                 '-m', ROOT_COMMIT_MSG)
        elif step[0] == 'CREATE':
            _git(repo_root, 'branch', step[1], step[2])
    return plan + ([warning] if warning else [])


WARN_HELP = {
    'unpushed': '{0} 有 {1} 个未推送、不带合并标记行的提交，推送时会被 pre-push/merge-via 拒绝；'
                '确认它们应发布后执行一次 git push --no-verify origin {0}',
    'first-publish': '{0} 还没发布到远端，且尖端不是合并脚本产生的合并；'
                     '首次推送会被 pre-push/merge-via 拒绝，需要一次 git push --no-verify -u origin {0}',
}

if __name__ == '__main__':
    args = sys.argv[1:]
    dry = '--dry-run' in args
    args = [a for a in args if a != '--dry-run']
    if len(args) != 1:
        print('用法：bootstrap_branches.py <repo_root> [--dry-run]', file=sys.stderr)
        sys.exit(2)
    try:
        results = bootstrap(args[0], dry_run=dry)
    except FileNotFoundError as e:
        print(f'ERROR {e}', file=sys.stderr)
        sys.exit(2)
    except ConfigError as e:
        print(f'ERROR {e}', file=sys.stderr)
        sys.exit(3)
    except BootstrapError as e:
        print(f'ERROR {e}', file=sys.stderr)
        sys.exit(4)
    for r in results:
        print(' '.join(r))
        if r[0] == 'WARN':
            print('WARN ' + WARN_HELP[r[1]].format(*r[2:]), file=sys.stderr)
    if dry:
        print('DRY-RUN')
