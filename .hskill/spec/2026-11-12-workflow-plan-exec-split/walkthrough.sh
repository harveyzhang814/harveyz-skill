#!/usr/bin/env bash
# 合并前实走（Spec 7(8)，plan Task 10）：在 /tmp 的两份克隆副本上部署并执行本分支的工具。
#
# 用法：bash walkthrough.sh <stage>
#   clone      克隆两份副本、切 staging、设 hooksPath / merge.ff、删 origin
#   deploy-hs  harveyz-skill 副本：用副本 staging 上的旧合并脚本把本功能分支并入副本 staging
#   deploy-ac  agent-canvas 副本：chore 分支里迁自填区、加 pre_checks、deploy_artifacts.py、
#              改 hooks 与 lock，提交后用副本 staging 上的旧合并脚本并入副本 staging
#   exec-hs    harveyz-skill 副本执行 (i)~(iv)
#   exec-ac    agent-canvas 副本执行 (i)~(iv)
#   budget-ac  agent-canvas 副本执行 (v)：超出 token 预算的改动「合并」→ 退出 1、staging 不动
#   verify     真实仓库未被改动的核对
#
# 安全：只写 /tmp/wt-hs 与 /tmp/wt-ac；对真实仓库只做 git clone（读）与 rev-parse/status（读）；
# 克隆后立即删 origin，任何东西都推不回真实仓库；不碰 ~/.claude/skills。
# 本分支的工具一律用字面绝对路径引用。

set -u

REAL_HS=/Users/harveyzhang96/Projects/harveyz-skill
REAL_AC=/Users/harveyzhang96/Projects/agent-canvas
HS=/tmp/wt-hs
AC=/tmp/wt-ac
FEATURE_SHA=80604bf90c206ad2a442a449b2e1ce23cefb08d3

run() {
  echo "\$ $*"
  "$@"
  local rc=$?
  echo "[exit $rc]"
  return $rc
}

runin() {
  local d="$1"; shift
  echo "\$ (cd $d) $*"
  ( cd "$d" && "$@" )
  local rc=$?
  echo "[exit $rc]"
  return $rc
}

section() { echo; echo "===== $* ====="; }

# 自填区（含两行标记）的 sha256
notes_sum() {
  awk '/^<!-- BEGIN PROJECT NOTES -->$/{p=1} p{print} /^<!-- END PROJECT NOTES -->$/{p=0}' "$1/docs/reference/git-workflow.md" \
    | shasum -a 256 | cut -c1-64
}

stage_clone() {
  section "clone: 基线（真实仓库只读）"
  echo "real harveyz-skill staging = $(git -C "$REAL_HS" rev-parse staging)"
  echo "real agent-canvas  staging = $(git -C "$REAL_AC" rev-parse staging)"
  echo "real agent-canvas  status --short: [$(git -C "$REAL_AC" status --short | tr '\n' ';')]"

  rm -rf /tmp/wt-hs /tmp/wt-ac

  section "clone: harveyz-skill -> /tmp/wt-hs"
  run git clone -q /Users/harveyzhang96/Projects/harveyz-skill /tmp/wt-hs
  echo "clone origin/staging = $(git -C "$HS" rev-parse origin/staging)"
  run git -C "$HS" checkout -q staging
  run git -C "$HS" config core.hooksPath .githooks
  run git -C "$HS" config merge.ff false
  run git -C "$HS" branch feature/workflow-plan-exec-split origin/feature/workflow-plan-exec-split
  local fsha; fsha=$(git -C "$HS" rev-parse feature/workflow-plan-exec-split)
  echo "feature/workflow-plan-exec-split = $fsha (expect $FEATURE_SHA) -> $([ "$fsha" = "$FEATURE_SHA" ] && echo MATCH || echo MISMATCH)"
  run git -C "$HS" remote remove origin
  echo "remotes after removal: [$(git -C "$HS" remote -v | tr '\n' ';')]"

  section "clone: agent-canvas -> /tmp/wt-ac"
  run git clone -q /Users/harveyzhang96/Projects/agent-canvas /tmp/wt-ac
  echo "clone origin/staging = $(git -C "$AC" rev-parse origin/staging)"
  run git -C "$AC" checkout -q staging
  run git -C "$AC" config core.hooksPath .githooks
  run git -C "$AC" config merge.ff false
  run git -C "$AC" remote remove origin
  echo "remotes after removal: [$(git -C "$AC" remote -v | tr '\n' ';')]"

  section "clone: 副本 staging 起点（动手前）"
  for r in "$HS" "$AC"; do
    echo "$r: HEAD=$(git -C "$r" symbolic-ref --short HEAD) staging=$(git -C "$r" rev-parse staging)" \
      "hooksPath=$(git -C "$r" config core.hooksPath) merge.ff=$(git -C "$r" config merge.ff)" \
      "status=[$(git -C "$r" status --short | tr '\n' ';')]"
  done
}

stage_deploy_hs() {
  section "deploy-hs: 功能分支并入副本 staging（用副本 staging 上的旧脚本）"
  echo "old script header (line 2): $(sed -n 2p /tmp/wt-hs/scripts/merge-to-staging.sh)"
  echo "副本 staging before = $(git -C "$HS" rev-parse staging)"
  echo "副本 staging 上 resolved.env: $(git -C "$HS" cat-file -e staging:.hskill/init-workflow/resolved.env 2>/dev/null && echo present || echo absent)"
  run git -C "$HS" worktree add -q /tmp/wt-hs/.worktrees/feature+workflow-plan-exec-split feature/workflow-plan-exec-split
  runin /tmp/wt-hs/.worktrees/feature+workflow-plan-exec-split bash /tmp/wt-hs/scripts/merge-to-staging.sh
  echo "副本 staging after = $(git -C "$HS" rev-parse staging)"
  echo "--- newest staging commit:"
  git -C "$HS" log -1 --format='%H%nparents: %P%n%B' staging
  echo "--- main worktree (hub) after sync: HEAD=$(git -C "$HS" rev-parse HEAD) branch=$(git -C "$HS" symbolic-ref --short HEAD) status=[$(git -C "$HS" status --short | tr '\n' ';')]"
  echo "--- deployment now on 副本 staging:"
  git -C "$HS" show staging:.hskill/init-workflow/resolved.env | sed -n '1p;/^merge_/p;/^worktree_dir/p'
  echo "merge script header (line 2): $(git -C "$HS" show staging:scripts/merge-to-staging.sh | sed -n 2p)"
  echo "hooks MANAGED merge-via blocks: $(git -C "$HS" show staging:.githooks/commit-msg | grep -c 'BEGIN MANAGED: commit-msg/merge-via') commit-msg, $(git -C "$HS" show staging:.githooks/pre-push | grep -c 'BEGIN MANAGED: pre-push/merge-via') pre-push"
}

stage_deploy_ac() {
  local W=/tmp/wt-ac/.worktrees/chore+deploy-init-workflow-5
  section "deploy-ac: 建 chore 分支 worktree"
  echo "副本 staging before = $(git -C "$AC" rev-parse staging)"
  run git -C "$AC" worktree add -q /tmp/wt-ac/.worktrees/chore+deploy-init-workflow-5 -b chore/deploy-init-workflow-5 staging

  section "deploy-ac: 1. 现有文档先加自填区标记并迁入手写内容"
  python3 - "$W/docs/reference/git-workflow.md" <<'PYEOF'
import sys
p = sys.argv[1]
doc = open(p, encoding='utf-8').read()
assert '<!-- BEGIN PROJECT NOTES -->' not in doc
notes = r'''
<!-- BEGIN PROJECT NOTES -->
### agent-canvas 补充：合并脚本

合并脚本的原理、并发处理方式、已知局限详见
[explanation/concurrent-staging-merge.md](../explanation/concurrent-staging-merge.md)。

**如果看到「未自动同步」警告**：说明停着 `staging` 的那个 worktree（通常是主目录）里有未提交
的改动，且改到了和本次合并同一批文件。脚本会保留那些改动、不覆盖，代价是那个 worktree 停在
合并前。**此时在那里直接 `git commit`，会造出一个把整批合并反转掉的提交**——看到大批
`D`/`M` 先用 `git diff --cached HEAD` 确认方向，别当成垃圾清理。处理完手头的改动后，在那个
worktree 里执行 `git reset --hard` 即可。机制见
[explanation/concurrent-staging-merge.md](../explanation/concurrent-staging-merge.md) §3.4。

**合并前的单文件 token 预算检查**（即上文 `merge.pre_checks` 里的
`node scripts/check-file-token-budget.js --changed-since staging`）：本分支相对 staging 改动了
`src/`、`tests/` 下的代码文件（或改了 `tests/structural/fileTokenBudget.json`）时才真正检查，
与 `npm test` 里的 `fileTokenBudget` 测试同一套规则。不通过就不合并、退出码 1，报错里列出违规文件和
处理办法：超限文件首选按职责拆开（规则见
[large-file-split spec §3](../superpowers/specs/2026-10-21-large-file-split-design.md)），确实切不开再在
`fileTokenBudget.json` 的 `exceptions` 里登记理由、送用户评审。没有绕过开关。检查要用开发依赖
`gpt-tokenizer`，提示缺它时在本 worktree 运行 `npm install` 后重试；只改文档的分支不做这项检查。

**退出码 2（真实内容冲突）**：脚本会在你当前 worktree 里落下真实的冲突标记文件，
按平时解决 git 冲突的方式处理：

```bash
# 解决冲突文件后
git add <冲突文件>
git commit
# 重新运行合并脚本
scripts/merge-to-staging.sh
```

### agent-canvas 补充：常见问题

**Q：主工作树为什么常驻 staging，不能换成别的分支吗？**
A：这是有意保留的现状，不要再提议改。代价是：一旦有人往主工作树写了未提交的文件，`merge-to-staging.sh` 同步宿主工作区时就会退化成 stash/pop 路径。对策是不在主工作树留在制品（AGENTS.md Step 3），而不是改脚本或挪走 staging。曾被否掉的方案还有「spec 写完就提交进 staging」：pre-commit 拦着做不到，实际只能变成每份文档一条短命分支，而且它只缩短主工作树变脏的时间、消除不了，并发合并照样会撞。所以改成了在写 spec 之前就建分支和 worktree。
<!-- END PROJECT NOTES -->
'''
doc = doc.rstrip('\n') + '\n' + notes
open(p, 'w', encoding='utf-8').write(doc)
print('notes block appended to old doc')
PYEOF
  echo "notes sha256 (in old doc, before deploy) = $(notes_sum "$W")"

  section "deploy-ac: 2. workflow-config.yml 加 merge.pre_checks（块列表写法）"
  cat >> "$W/.hskill/init-workflow/workflow-config.yml" <<'YMLEOF'

# ── 合并前检查（渲染进 scripts/merge-to-staging.sh 的 merge/pre-checks 块）──────
#
# 按顺序在被合并分支的工作树根执行，{target} 替换为合并目标分支；任一非 0 → 不合并、退出码 1
merge:
  pre_checks:
    - "node scripts/check-file-token-budget.js --changed-since {target}"
YMLEOF
  tail -4 "$W/.hskill/init-workflow/workflow-config.yml"

  section "deploy-ac: 3. Step 6.0 deploy_artifacts.py（stdout 与 stderr 分开记录）"
  echo "\$ python3 /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/coding/init-workflow/references/deploy_artifacts.py $W"
  python3 /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/coding/init-workflow/references/deploy_artifacts.py "$W" \
    >/tmp/wt-ac/.git/deploy.stdout 2>/tmp/wt-ac/.git/deploy.stderr
  echo "[exit $?]"
  echo "--- stdout:"; cat /tmp/wt-ac/.git/deploy.stdout
  echo "--- stderr:"; cat /tmp/wt-ac/.git/deploy.stderr
  echo "notes sha256 (new doc, after deploy) = $(notes_sum "$W")"
  echo "--- rendered resolved.env:"; cat "$W/.hskill/init-workflow/resolved.env"
  echo "--- rendered merge/pre-checks block:"
  sed -n '/BEGIN MANAGED: merge\/pre-checks/,/END MANAGED: merge\/pre-checks/p' "$W/scripts/merge-to-staging.sh"

  section "deploy-ac: 4. Step 6 hooks（merge-via 块、staging 变体、删 MANAGED 块外的手写合并拦截）"
  python3 - "$W/.githooks" <<'PYEOF'
import hashlib, re, sys
d = sys.argv[1]
TARGET = 'staging'
SCRIPT = 'scripts/merge-to-staging.sh'
TRAILER = 'Merge-Via: merge-to-staging.sh'

def h(content):
    data = content.strip().encode('utf-8')
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()[:8]

def rehash(text, block_id):
    pat = re.compile(r'# --- BEGIN MANAGED: ' + re.escape(block_id) + r' \(hash:(\w+)\) ---\n(.*?)\n# --- END MANAGED: ' + re.escape(block_id) + r' ---', re.S)
    m = pat.search(text)
    assert m, block_id
    new = h(m.group(2))
    print(f'  {block_id}: hash {m.group(1)} -> {new}')
    return text[:m.start(1)] + new + text[m.end(1):]

def rd(n): return open(f'{d}/{n}', encoding='utf-8').read()
def wr(n, t): open(f'{d}/{n}', 'w', encoding='utf-8').write(t)

# pre-commit：staging 块换成合并目标变体
t = rd('pre-commit')
variant = f'''# --- BEGIN MANAGED: branches.protected/{TARGET} (hash:PLACEHOLDER) ---
if [ "$BRANCH" = "{TARGET}" ]; then
    if [ "$IS_MERGE" -eq 0 ]; then
        echo "❌ 禁止直接在 {TARGET} 上提交。请在 feature/*、fix/*、chore/* 或 doc/* 分支开发，合并请用 {SCRIPT}。"
        exit 1
    fi
fi
# --- END MANAGED: branches.protected/{TARGET} ---'''
t, n = re.subn(r'# --- BEGIN MANAGED: branches\.protected/staging \(hash:\w+\) ---\n.*?# --- END MANAGED: branches\.protected/staging ---', lambda m: variant, t, flags=re.S)
assert n == 1
print('pre-commit:'); t = rehash(t, 'branches.protected/staging'); wr('pre-commit', t)

# commit-msg：删 MANAGED 块外的手写合并拦截，插 merge-via 块（在 format 之前），format 块首行豁免合并提交
t = rd('commit-msg')
i = t.index('# Skip merge commits')
j = t.index('# --- BEGIN MANAGED: commit-msg/format')
removed = t[i:j]
assert TRAILER in removed and 'exit 0' in removed
print('commit-msg: removed hand-written block outside MANAGED:\n' + ''.join('    | ' + l + '\n' for l in removed.rstrip('\n').split('\n')))
merge_via = f'''# --- BEGIN MANAGED: commit-msg/merge-via (hash:PLACEHOLDER) ---
if [ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] \\
    && [ "$(git symbolic-ref --short HEAD 2>/dev/null)" = "{TARGET}" ]; then
    if ! grep -qxF -- "{TRAILER}" "$1"; then
        case "$SUBJECT" in
            "Merge branch '{TARGET}' of "*) ;;
            *)
                echo "❌ 禁止手动合并进 {TARGET}。请改用 {SCRIPT}。"
                exit 1
                ;;
        esac
    fi
fi
# --- END MANAGED: commit-msg/merge-via ---

'''
t = t[:i] + merge_via + t[j:]
t, n = re.subn(r'(# --- BEGIN MANAGED: commit-msg/format \(hash:\w+\) ---\n)',
               lambda m: m.group(1) + '[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] && exit 0\n', t)
assert n == 1
print('commit-msg:'); t = rehash(t, 'commit-msg/merge-via'); t = rehash(t, 'commit-msg/format'); wr('commit-msg', t)

# pre-push：merge-via 块放在 while 与 case 之间；删 esac 之后的手写 staging 检查
t = rd('pre-push')
m = re.search(r'    esac\n(.*?)done\n', t, re.S)
removed = m.group(1)
assert TRAILER in removed
print('pre-push: removed hand-written block outside MANAGED:\n' + ''.join('    | ' + l + '\n' for l in removed.rstrip('\n').split('\n')))
t = t[:m.start(1)] + t[m.end(1):]
pp = f'''# --- BEGIN MANAGED: pre-push/merge-via (hash:PLACEHOLDER) ---
    if [ "$remote_ref" = "refs/heads/{TARGET}" ] \\
        && [ "$local_sha" != "0000000000000000000000000000000000000000" ]; then
        if [ "$remote_sha" = "0000000000000000000000000000000000000000" ]; then
            CHECK_SHAS="$local_sha"
        else
            CHECK_SHAS=$(git rev-list --first-parent "$remote_sha..$local_sha" 2>/dev/null)
        fi
        for SHA in $CHECK_SHAS; do
            if git log -1 --format=%B "$SHA" | grep -qxF -- "{TRAILER}"; then
                continue
            fi
            case "$(git log -1 --format=%s "$SHA")" in
                "Merge branch '{TARGET}' of "*) continue ;;
            esac
            echo "❌ 推送被拒：$SHA 不是经 {SCRIPT} 产生的合并（缺少 '{TRAILER}' 行）。"
            exit 1
        done
    fi
# --- END MANAGED: pre-push/merge-via ---
'''
k = t.index('    case "$remote_ref" in\n')
t = t[:k] + pp + t[k:]
print('pre-push:'); t = rehash(t, 'pre-push/merge-via'); wr('pre-push', t)
print('pre-push/force-push: 既有 hash 与内容不符（部署前即如此，Step 4b 类型 C），按“保留用户修改”原样保留')
print('post-checkout: naming 取值与 resolved.env 一致，UNCHANGED')
PYEOF
  echo "--- hooks diff stat:"; git -C "$W" diff --stat -- .githooks

  section "deploy-ac: 5. Step 9 lock 文件"
  python3 - "$W/.githooks/.workflow-config.lock.yml" <<'PYEOF'
import sys, datetime
p = sys.argv[1]
t = open(p, encoding='utf-8').read()
body = t[t.index('branches_protected:'):]
now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
out = ('# Generated by init-workflow, do not edit manually\n'
       f'generated_at: "{now}"\n'
       'skill_version: "5.0.0"\n' + body.rstrip('\n') + '\n'
       'git_config:\n'
       '  core_hooks_path: ".githooks"   # 上次运行时设置的值\n'
       '  merge_ff: "false"              # 上次运行时设置的值\n')
open(p, 'w', encoding='utf-8').write(out)
print('lock updated')
PYEOF
  chmod +x "$W"/.githooks/*

  section "deploy-ac: 6. 提交到 chore 分支"
  run git -C "$W" status --short
  run git -C "$W" add -A
  run git -C "$W" commit -q -m "chore: deploy init-workflow 5.0.0 (walkthrough copy)"
  echo "chore tip = $(git -C "$W" rev-parse HEAD)"

  section "deploy-ac: 7. 用副本 staging 上的旧合并脚本并入副本 staging"
  echo "old script header (line 2): $(sed -n 2p /tmp/wt-ac/scripts/merge-to-staging.sh)"
  echo "副本 staging before = $(git -C "$AC" rev-parse staging)"
  runin /tmp/wt-ac/.worktrees/chore+deploy-init-workflow-5 bash /tmp/wt-ac/scripts/merge-to-staging.sh
  echo "副本 staging after = $(git -C "$AC" rev-parse staging)"
  git -C "$AC" log -1 --format='%H%nparents: %P%n%B' staging
  echo "--- hub after sync: HEAD=$(git -C "$AC" rev-parse HEAD) branch=$(git -C "$AC" symbolic-ref --short HEAD) status=[$(git -C "$AC" status --short | tr '\n' ';')]"
  echo "merge script header (line 2) on staging: $(git -C "$AC" show staging:scripts/merge-to-staging.sh | sed -n 2p)"
}

# 共用 (i)~(iv)；$1 副本根，$2 = doc | src（feature/walk 改动的种类）
exec_common() {
  local R="$1" kind="$2"
  local out dp

  section "(i) $R: inspect-worktree.sh --branch feature/walk（在主工作树运行）"
  echo "\$ (cd $R) bash /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/devflow/manage-worktree/scripts/inspect-worktree.sh --branch feature/walk"
  out=$(cd "$R" && bash /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/devflow/manage-worktree/scripts/inspect-worktree.sh --branch feature/walk)
  echo "[exit $?]"; echo "$out"
  dp=$(printf '%s\n' "$out" | sed -n 's/^default_path=//p')
  echo "default_path = $dp"
  run git -C "$R" worktree add -q "$dp" -b feature/walk staging
  if [ "$kind" = src ]; then
    # token 预算检查要 gpt-tokenizer：链接真实仓库的 node_modules（只读使用；node_modules 被 .gitignore 忽略）
    run ln -s /Users/harveyzhang96/Projects/agent-canvas/node_modules "$dp/node_modules"
    printf 'export const walkProbe = 1\n' > "$dp/src/walk-probe.ts"
    run git -C "$dp" add src/walk-probe.ts
  else
    printf '\nwalkthrough probe\n' >> "$dp/README.md"
    run git -C "$dp" add README.md
  fi
  run git -C "$dp" commit -q -m "test: walkthrough probe commit"
  local before after
  before=$(git -C "$R" rev-parse staging)
  echo "副本 staging before = $before"
  runin "$dp" bash /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/devflow/manage-worktree/scripts/merge-worktree.sh
  after=$(git -C "$R" rev-parse staging)
  echo "副本 staging after  = $after ($([ "$before" != "$after" ] && echo ADVANCED || echo UNCHANGED))"
  echo "--- newest staging commit:"; git -C "$R" log -1 --format='%H%nparents: %P%n%B' staging
  echo "trailer line present: $(git -C "$R" log -1 --format=%B staging | grep -cxF 'Merge-Via: merge-to-staging.sh')"
  echo "feature/walk tip is ancestor of staging: $(git -C "$R" merge-base --is-ancestor feature/walk staging && echo yes || echo no)"
  echo "hub: branch=$(git -C "$R" symbolic-ref --short HEAD) HEAD=$(git -C "$R" rev-parse HEAD) status=[$(git -C "$R" status --short | tr '\n' ';')]"

  section "(ii) $R: 手动 git merge --no-ff feature/walk2 进 staging（主工作树）"
  local W2="$R/.worktrees/feature+walk2"
  run git -C "$R" worktree add -q "$W2" -b feature/walk2 staging
  printf '\nwalk2 probe\n' >> "$W2/README.md"
  run git -C "$W2" add README.md
  run git -C "$W2" commit -q -m "docs: walk2 probe"
  before=$(git -C "$R" rev-parse staging)
  run git -C "$R" merge --no-ff --no-edit feature/walk2
  echo "MERGE_HEAD present: $([ -f "$R/.git/MERGE_HEAD" ] && echo yes || echo no)"
  run git -C "$R" commit --no-edit
  run git -C "$R" merge --abort
  after=$(git -C "$R" rev-parse staging)
  echo "staging before=$before after=$after ($([ "$before" = "$after" ] && echo UNCHANGED || echo MOVED))"
  echo "hub status after abort: [$(git -C "$R" status --short | tr '\n' ';')]"

  section "(iii) $R: 在干净的 staging 上重跑 deploy_artifacts.py，自填区逐字节不变"
  echo "hub status before: [$(git -C "$R" status --short | tr '\n' ';')]"
  local s1 s2
  s1=$(notes_sum "$R")
  echo "notes block lines: $(awk '/^<!-- BEGIN PROJECT NOTES -->$/{p=1} p{n++} /^<!-- END PROJECT NOTES -->$/{p=0} END{print n}' "$R/docs/reference/git-workflow.md")"
  echo "notes sha256 before = $s1"
  run python3 /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/coding/init-workflow/references/deploy_artifacts.py "$R"
  s2=$(notes_sum "$R")
  echo "notes sha256 after  = $s2 ($([ "$s1" = "$s2" ] && echo IDENTICAL || echo DIFFERENT))"
  echo "hub status after: [$(git -C "$R" status --short | tr '\n' ';')]"
}

# (iii) 补充：自填区为空时，再放一行内容（不提交）重跑，确认被原样搬运，然后还原
notes_extra_probe() {
  local R="$1" s1 s2
  section "(iii-extra) $R: 自填区写入一行（未提交）后重跑"
  python3 - "$R/docs/reference/git-workflow.md" <<'PYEOF'
import sys
p = sys.argv[1]
t = open(p, encoding='utf-8').read()
t = t.replace('<!-- BEGIN PROJECT NOTES -->\n', '<!-- BEGIN PROJECT NOTES -->\n项目自填探针：这一行应在重新渲染后原样保留。\n', 1)
open(p, 'w', encoding='utf-8').write(t)
PYEOF
  s1=$(notes_sum "$R"); echo "notes sha256 before = $s1"
  run python3 /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/coding/init-workflow/references/deploy_artifacts.py "$R"
  s2=$(notes_sum "$R"); echo "notes sha256 after  = $s2 ($([ "$s1" = "$s2" ] && echo IDENTICAL || echo DIFFERENT))"
  run git -C "$R" diff --stat
  run git -C "$R" checkout -- docs/reference/git-workflow.md
  echo "hub status after restore: [$(git -C "$R" status --short | tr '\n' ';')]"
}

consistency() {
  local R="$1"
  section "(iv) $R: 合并目标与 worktree 目录四处取值（读副本 staging 上已提交的版本）"
  echo "--- resolved.env:"
  git -C "$R" show staging:.hskill/init-workflow/resolved.env | grep -E '^(integration_branches|merge_target|merge_script|merge_trailer|worktree_dir)='
  echo "--- docs/reference/git-workflow.md:"
  git -C "$R" show staging:docs/reference/git-workflow.md | grep -nE 'git worktree add|scripts/merge-to-|Merge-Via|只更新本地' | grep -v '^.*PROJECT NOTES' | head -8
  echo "--- hooks:"
  for f in pre-commit commit-msg pre-push; do
    git -C "$R" show "staging:.githooks/$f" | grep -nE '= "staging"|refs/heads/staging"|Merge-Via|merge-to-staging|Merge branch .staging' | sed "s|^|$f:|"
  done
  echo "--- scripts/merge-to-staging.sh:"
  git -C "$R" show staging:scripts/merge-to-staging.sh | grep -nE '^TARGET_BRANCH=|^INTEGRATION_BRANCHES=|^Merge-Via|^run_pre_check '
  echo "--- worktree dir actually used / ignored:"
  echo "git worktree list:"; git -C "$R" worktree list
  echo "check-ignore .worktrees/: $(cd "$R" && git check-ignore -v .worktrees/ || echo NOT-IGNORED)"
}

stage_budget_ac() {
  local out dp before after
  section "(v) $AC: 超出 token 预算的改动「合并」→ 退出 1、staging 不动"
  out=$(cd "$AC" && bash /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/devflow/manage-worktree/scripts/inspect-worktree.sh --branch feature/walk-budget)
  dp=$(printf '%s\n' "$out" | sed -n 's/^default_path=//p')
  echo "default_path = $dp"
  run git -C "$AC" worktree add -q "$dp" -b feature/walk-budget staging
  run ln -s /Users/harveyzhang96/Projects/agent-canvas/node_modules "$dp/node_modules"
  python3 - "$dp/src/walk-over-budget.ts" <<'PYEOF'
import sys
lines = [f'export const walkOverBudget{i} = {i * 7919 % 100003}' for i in range(1500)]
open(sys.argv[1], 'w').write('\n'.join(lines) + '\n')
PYEOF
  echo "src/walk-over-budget.ts: $(wc -l < "$dp/src/walk-over-budget.ts") lines, $(wc -c < "$dp/src/walk-over-budget.ts") bytes (limit 5000 o200k tokens)"
  run git -C "$dp" add src/walk-over-budget.ts
  run git -C "$dp" commit -q -m "test: add over-budget probe file"
  before=$(git -C "$AC" rev-parse staging)
  echo "副本 staging before = $before"
  runin "$dp" bash /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split/skills/devflow/manage-worktree/scripts/merge-worktree.sh
  after=$(git -C "$AC" rev-parse staging)
  echo "副本 staging after  = $after ($([ "$before" = "$after" ] && echo UNCHANGED || echo MOVED))"
  echo "feature/walk-budget in staging: $(git -C "$AC" merge-base --is-ancestor feature/walk-budget staging && echo yes || echo no)"
}

stage_verify() {
  section "verify: 真实仓库未被改动"
  echo "real harveyz-skill staging = $(git -C "$REAL_HS" rev-parse staging) (expect 22a1c02a49ee2e2a0c9af5030e930e3133ad8c19)"
  echo "real agent-canvas  staging = $(git -C "$REAL_AC" rev-parse staging) (expect 9d10e908db56cc747400469edd5a4d65e9f80789)"
  echo "real agent-canvas  status --short: [$(git -C "$REAL_AC" status --short | tr '\n' ';')]"
  echo "real agent-canvas  has branch feature/walk: $(git -C "$REAL_AC" rev-parse -q --verify refs/heads/feature/walk >/dev/null && echo yes || echo no)"
  echo "real harveyz-skill has branch feature/walk: $(git -C "$REAL_HS" rev-parse -q --verify refs/heads/feature/walk >/dev/null && echo yes || echo no)"
  echo "clones' remotes: hs=[$(git -C "$HS" remote | tr '\n' ' ')] ac=[$(git -C "$AC" remote | tr '\n' ' ')]"
}

case "${1:-}" in
  clone) stage_clone ;;
  deploy-hs) stage_deploy_hs ;;
  deploy-ac) stage_deploy_ac ;;
  exec-hs) exec_common /tmp/wt-hs doc; notes_extra_probe /tmp/wt-hs; consistency /tmp/wt-hs ;;
  exec-ac) exec_common /tmp/wt-ac src; consistency /tmp/wt-ac ;;
  budget-ac) stage_budget_ac ;;
  verify) stage_verify ;;
  *) echo "用法：bash walkthrough.sh clone|deploy-hs|deploy-ac|exec-hs|exec-ac|budget-ac|verify" >&2; exit 2 ;;
esac
