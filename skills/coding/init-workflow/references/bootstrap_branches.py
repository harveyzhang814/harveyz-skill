#!/usr/bin/env python3
"""
init-workflow 起步引导（Step 9，写完 lock 文件之后）
让仓库具备开始工作的分支：全新仓库（还没有提交）在根集成分支上做根提交（收入所有未被忽略的文件），
再把主工作树切到合并目标常驻；本地缺少的集成分支从远端同名分支或其上游建出；
最后提醒合并目标分支上推送会被 pre-push 拒绝的提交。
先算出完整计划再动手：任何一步推不出来就在改动之前停下。

用法：python3 bootstrap_branches.py <repo_root> [--dry-run]
stdout 逐行：ROOT-COMMIT <分支>（随后每个将提交的文件一行 FILE <路径>）/ CREATE <分支> <来源> /
             EXISTS <分支> / SWITCH <分支> / WARN ahead <来源> <数量> <新分支> /
             WARN unpushed <分支> <数量> / WARN first-publish <分支>；--dry-run 时末行 DRY-RUN
退出码：0 正常；2 找不到规则文件；3 配置推不出分支顺序；4 已有提交的仓库缺根集成分支
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    """合并目标推送时 pre-push/merge-via 会拒绝的情况；无需提醒时返回 None。
    还没有远端也照样判断：加上远端后第一次推送面对的是同一个尖端。"""
    remote = _remote_of(repo, target)
    if remote is None:
        tip_msg = _git(repo, 'log', '-1', '--format=%B', tip).stdout if tip else ''
        return None if tip and _marked(tip_msg.strip(), target, trailer) else ('WARN', 'first-publish', target)
    log = _git(repo, 'log', '--first-parent', '--format=%B%x1e', f'{remote}..{tip}').stdout
    n = sum(1 for m in log.split('\x1e') if m.strip() and not _marked(m.strip(), target, trailer))
    return ('WARN', 'unpushed', target, str(n)) if n else None


def _remote_of(repo, branch):
    """分支对应的远端引用：先取 upstream，再取 origin/<分支>；都没有返回 None。"""
    up = _git(repo, 'rev-parse', '-q', '--verify', '--symbolic-full-name', f'{branch}@{{upstream}}',
              check=False)
    if up.returncode == 0 and up.stdout.strip():
        return up.stdout.strip()
    return f'refs/remotes/origin/{branch}' if _has_ref(repo, f'refs/remotes/origin/{branch}') else None


def _ahead_warnings(repo, plan):
    """从本地分支新建集成分支时，来源若领先它的远端，这些提交会随新分支一起发布。"""
    out = []
    for step in plan:
        if step[0] != 'CREATE' or step[2].startswith('origin/'):
            continue
        remote = _remote_of(repo, step[2])
        if remote is None:
            continue
        n = _git(repo, 'rev-list', '--count', f'{remote}..refs/heads/{step[2]}').stdout.strip()
        if n != '0':
            out.append(('WARN', 'ahead', step[2], n, step[1]))
    return out


def _root_files(repo_root):
    """根提交将收入的文件：已暂存的加上未跟踪且未被忽略的，与 git add -A 一致。"""
    staged = _git(repo_root, 'ls-files', '-z').stdout.split('\0')
    others = _git(repo_root, 'ls-files', '-z', '--others', '--exclude-standard').stdout.split('\0')
    return sorted({f for f in staged + others if f})


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
            plan.extend(('FILE', f) for f in _root_files(repo_root))
            tips[name] = None
        else:
            raise BootstrapError(
                f'仓库已有提交，但根集成分支 {name} 在本地和 origin 都不存在；'
                f'不猜测从哪建，请先确定 {name} 的来源（例如 git branch -m <现有默认分支> {name}）后重跑')

    target = resolved['merge_target']
    if plan[0][0] == 'ROOT-COMMIT' and target and target != order[0][0]:
        plan.append(('SWITCH', target))  # 与根分支同一提交，只改 HEAD 指向
    warnings = _ahead_warnings(repo_root, plan)
    warning = _push_warning(repo_root, target, resolved['merge_trailer'], tips.get(target)) \
        if target and target in tips else None
    warnings += [warning] if warning else []

    if dry_run:
        return plan + warnings

    # 2. 按计划执行；根提交绕过已生效的 hooks（它们禁止在集成分支上直接提交）
    for step in plan:
        if step[0] == 'ROOT-COMMIT':
            _git(repo_root, 'symbolic-ref', 'HEAD', f'refs/heads/{step[1]}')
            _git(repo_root, 'add', '-A')
            _git(repo_root, '-c', 'core.hooksPath=/dev/null', 'commit', '-q', '--no-verify',
                 '-m', ROOT_COMMIT_MSG)
        elif step[0] == 'CREATE':
            _git(repo_root, 'branch', step[1], step[2])
        elif step[0] == 'SWITCH':
            _git(repo_root, 'symbolic-ref', 'HEAD', f'refs/heads/{step[1]}')
    return plan + warnings


WARN_HELP = {
    'unpushed': '{0} 有 {1} 个未推送、不带合并标记行的提交，推送时会被 pre-push/merge-via 拒绝；'
                '确认它们应发布后执行一次 git push --no-verify origin {0}',
    'first-publish': '{0} 还没发布到远端，且尖端不是合并脚本产生的合并，第一次推送会被 pre-push/merge-via 拒绝'
                     '（还没加远端也一样）；先用合并脚本合并一次（如部署产物所在的 chore 分支或第一个功能分支）'
                     '再推送即可，或确认后执行一次 git push --no-verify -u origin {0}',
    'ahead': '{0} 有 {1} 个提交还没推送到远端；从它建出的 {2} 带着这些提交，推送 {2} 时会一并发布。'
             '确认它们应发布，或先处理（推送 {0}、或改为从远端的 {0} 建出 {2}）再继续',
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
        print(' '.join(r), flush=True)  # 先出 stdout 行，stderr 的说明紧随其后
        if r[0] == 'WARN':
            print('WARN ' + WARN_HELP[r[1]].format(*r[2:]), file=sys.stderr)
    if dry:
        print('DRY-RUN')
