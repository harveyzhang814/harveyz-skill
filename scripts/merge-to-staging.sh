#!/usr/bin/env bash
# 把当前分支无锁合并进本地 staging：乐观 merge-tree + commit-tree + update-ref
# CAS，ref 被别的 worktree 抢先移动就自动重算重试；遇到真实内容冲突则在当前
# worktree 落下冲突标记交给调用方处理，不重试、不阻塞其他并发的合并请求。
#
# 只更新本地 refs/heads/staging，不 push 到 origin——push 仍是单独的人工/后续步骤。
#
# 用法：在 feature 分支的 worktree 里直接运行
#   scripts/merge-to-staging.sh
#
# 退出码：
#   0 = 合并成功（或已经在 staging 里，无需合并）
#   1 = 出错（非冲突类：merge-tree 内部错误、CAS 因非竞态原因失败、重试超限等）
#   2 = 检测到真实冲突，已在当前 worktree 落下冲突标记，等待手动解决后重新运行本脚本

set -euo pipefail

TARGET_BRANCH="staging"
TARGET_REF="refs/heads/${TARGET_BRANCH}"
MAX_RETRIES=20
BASE_DELAY_MS=300
MAX_DELAY_MS=5000
LOCK_STALE_SECONDS=60
LOCK_WAIT_TIMEOUT_MS=90000

feature_branch=$(git symbolic-ref --short HEAD 2>/dev/null) || {
    echo "❌ 当前处于 detached HEAD，无法确定要合并的分支。" >&2
    exit 1
}

if [ "$feature_branch" = "$TARGET_BRANCH" ] || [ "$feature_branch" = "main" ]; then
    echo "❌ 请在 feature/fix/chore/doc 分支的 worktree 里调用本脚本，当前在 ${feature_branch}。" >&2
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "❌ 当前 worktree 有未提交的改动，请先提交或清理后再合并。" >&2
    exit 1
fi

# 找到当前 checkout 着 staging 的 worktree（如果有）。干不干净的判断挪到
# sync_staging_worktree() 拿到互斥锁之后现读现算（见下），这里只需要知道
# 这个 worktree 在哪、存不存在。
staging_wt=$(git worktree list --porcelain | awk -v target="$TARGET_REF" '
    $1 == "worktree" { wt = $2 }
    $1 == "branch" && $2 == target { print wt }
')

# 互斥锁：整个 sync_staging_worktree() 期间独占，锁目录建在 hub 的私有 git-dir 下
# （git rev-parse --absolute-git-dir；linked worktree 各自独立，不会跟共享对象库混）。
# mkdir 是原子操作，天然满足互斥需要；不用 flock(1)，因为 macOS 默认不带它。
# 成功时把锁目录路径打到 stdout（调用方用它来释放锁），失败（等待超时）时返回 1。
acquire_hub_lock() {
    local git_dir lock_dir owner_file waited_ms=0 attempt=0
    if ! git_dir=$(git -C "$staging_wt" rev-parse --absolute-git-dir 2>/dev/null); then
        echo "⚠️ ${TARGET_BRANCH} 所在 worktree（${staging_wt}）无法定位 git-dir，放弃本次同步。" >&2
        return 1
    fi
    lock_dir="${git_dir}/merge-to-staging.lock"
    owner_file="${lock_dir}/owner"

    while true; do
        if mkdir "$lock_dir" 2>/dev/null; then
            printf 'pid=%s ts=%s\n' "$$" "$(date +%s)" > "$owner_file"
            printf '%s\n' "$lock_dir"
            return 0
        fi

        local lock_ts now age
        lock_ts=$(sed -n 's/.*ts=\([0-9]*\).*/\1/p' "$owner_file" 2>/dev/null || true)
        now=$(date +%s)
        if [ -n "$lock_ts" ]; then
            age=$((now - lock_ts))
            if [ "$age" -gt "$LOCK_STALE_SECONDS" ]; then
                # 原子改名后再删——mv 是唯一的争夺点，只有一个进程能抢到改名
                # 成功，避免两个进程都判定"残留"、都 rm -rf，后动手的那个把
                # 另一个刚抢到的新锁也删掉。mv 失败说明别的进程已经抢先回收
                # （或已经拿到新锁），不重复处理，直接往下走正常的退避重试，
                # 让下一轮 mkdir 自然决出胜者。
                local stale_dir="${lock_dir}.stale.$$"
                if mv "$lock_dir" "$stale_dir" 2>/dev/null; then
                    echo "⚠️ ${TARGET_BRANCH} 所在 worktree 的同步锁残留超过 ${LOCK_STALE_SECONDS}s（疑似持锁进程已退出），强制清除后重试。" >&2
                    rm -rf "$stale_dir"
                fi
            fi
        fi

        if [ "$waited_ms" -ge "$LOCK_WAIT_TIMEOUT_MS" ]; then
            echo "⚠️ 等待 ${TARGET_BRANCH} 所在 worktree 的同步锁超过 $((LOCK_WAIT_TIMEOUT_MS / 1000))s，放弃本次同步。" >&2
            return 1
        fi

        attempt=$((attempt + 1))
        if [ "$attempt" -eq 1 ]; then
            echo "⏳ ${TARGET_BRANCH} 所在 worktree 正在被其他进程同步，等待锁..." >&2
        fi
        local delay_ms jitter_ms sleep_arg
        delay_ms=$((BASE_DELAY_MS * (1 << (attempt - 1))))
        if [ "$delay_ms" -gt "$MAX_DELAY_MS" ]; then
            delay_ms=$MAX_DELAY_MS
        fi
        jitter_ms=$((delay_ms / 2 + (RANDOM % (delay_ms / 2 + 1))))
        waited_ms=$((waited_ms + jitter_ms))
        sleep_arg=$(printf '%d.%03d' $((jitter_ms / 1000)) $((jitter_ms % 1000)))
        sleep "$sleep_arg"
    done
}

release_hub_lock() {
    local lock_dir="$1" owner_file
    owner_file="${lock_dir}/owner"
    # 只释放确认还是自己持有的锁——残留回收的竞态里，自己的旧锁可能已经被
    # 别的进程强制清除、自己又抢到了一把新锁；这里比对 owner 文件里的 pid，
    # 不是自己的就不动，避免误删别人正持有的锁。
    if [ -f "$owner_file" ] && ! grep -q "^pid=$$ " "$owner_file" 2>/dev/null; then
        return 0
    fi
    rm -rf "$lock_dir"
}

# 原子写：先写临时文件，再 mv 到目标名字，避免读到写一半的内容。
write_synced_baseline() {
    local target_file="$1" value="$2" tmp_file
    tmp_file="${target_file}.tmp.$$"
    printf '%s\n' "$value" > "$tmp_file"
    mv "$tmp_file" "$target_file"
}

# $1 = 这次合并发起前调用方读到的 staging 提交，只在 hub 从未同步过（还没有持久化
# 基线标记）时用作 detach 的兜底基准；一旦标记文件存在，永远优先用标记里的值。
sync_staging_worktree() {
    [ -z "$staging_wt" ] && return 0

    local fallback_baseline="$1"
    local lock_dir
    if ! lock_dir=$(acquire_hub_lock); then
        return 0
    fi

    # 兜底：万一同步中途被信号打断（Ctrl-C/kill），退出前把 HEAD 接回分支、
    # 释放锁，不把 hub 晾在游离状态——detach 之后 hub 会从 `git worktree list
    # --porcelain` 的 branch 字段里"消失"，下一次合并会静默跳过同步且不报警。
    # HEAD 本来就已接回分支时，symbolic-ref 重复设置成同一个值是安全的空操作。
    #
    # INT/TERM 必须与 EXIT 分开、且**自己显式 exit**：bash 的信号 trap 跑完处理器
    # 之后会**回到被打断的地方接着执行**，不会终止脚本。三个信号共用一条不带 exit
    # 的 trap 会把"被打断"变成"清理完继续跑"——脏路径上尤其致命：current_target 是
    # stash push 之前就读好的，信号若落在 stash push 期间，处理器接回 HEAD、放掉锁，
    # 然后脚本继续往下 reset --hard "$current_target"，把 refs/heads/staging 硬拽回
    # 合并前的值，静默吞掉这期间别的进程 CAS 进来的提交——正是本分支要根除的那个
    # 回退 bug 换了个门重新出现。EXIT 那条不能带 exit（它本来就在退出路径上）。
    _hub_sync_cleanup() {
        git -C "$staging_wt" symbolic-ref HEAD "refs/heads/${TARGET_BRANCH}" 2>/dev/null
        release_hub_lock "$lock_dir"
    }
    trap '_hub_sync_cleanup' EXIT
    trap '_hub_sync_cleanup; trap - EXIT; exit 130' INT
    trap '_hub_sync_cleanup; trap - EXIT; exit 143' TERM

    local status
    if _sync_staging_worktree_locked "$fallback_baseline"; then
        status=0
    else
        status=$?
    fi

    trap - EXIT INT TERM
    release_hub_lock "$lock_dir"
    return $status
}

_sync_staging_worktree_locked() {
    local fallback_baseline="$1"
    local git_dir baseline_file detach_base
    git_dir=$(git -C "$staging_wt" rev-parse --absolute-git-dir)
    baseline_file="${git_dir}/merge-to-staging.synced-to"

    # 标记文件里的值先验证能不能解析成真实提交，再拿来用。写坏了、或者那个提交
    # 后来被剪掉/改写掉时，下面的 update-ref 会失败，而失败分支只警告不修标记——
    # 于是之后每一次同步都会走进同一条死路，且提示的补救手法（git reset --hard）
    # 根本不碰这个标记文件，照着做也好不了。解析不出来就退化到兜底值，跟"还没有
    # 标记文件"走同一条自愈路径，下一次同步就能自行接上。
    if [ -f "$baseline_file" ] && detach_base=$(git -C "$staging_wt" rev-parse -q --verify "$(cat "$baseline_file")^{commit}" 2>/dev/null); then
        :
    else
        detach_base="$fallback_baseline"
    fi

    # detach 到基准，让索引/工作树与 HEAD 对齐，这样接下来的 git status 才能读出
    # 真实脏净：update-ref 已经把 refs/heads/staging 挪到新提交，hub 的 HEAD 是
    # 分支的 symref，不先对齐的话，任何时候读 status 都会把"符号引用已经跟着分支
    # 挪走、但索引/工作树还没动"误判成一堆假象改动。纯指针操作，--no-deref 不碰
    # refs/heads/staging 也不碰索引/工作树。
    if ! git -C "$staging_wt" update-ref --no-deref HEAD "$detach_base" 2>/dev/null; then
        echo "⚠️ ${TARGET_BRANCH} 所在 worktree（${staging_wt}）无法固定同步基准，未自动同步；" >&2
        echo "   处理完手头的改动后，请在那个 worktree 里执行： git reset --hard" >&2
        return 0
    fi

    local hub_status
    if ! hub_status=$(git -C "$staging_wt" status --porcelain 2>/dev/null); then
        git -C "$staging_wt" symbolic-ref HEAD "refs/heads/${TARGET_BRANCH}"
        echo "⚠️ ${TARGET_BRANCH} 所在 worktree（${staging_wt}）无法读取状态，未自动同步；" >&2
        echo "   处理完手头的改动后，请在那个 worktree 里执行： git reset --hard" >&2
        return 0
    fi

    if [ -z "$hub_status" ]; then
        # 现读一次目标提交，先在 detach 状态下 reset 到这个显式值（此时还没有
        # 分支 symref 可移动，reset 只碰这个 worktree 自己的索引/工作树），
        # 再接回分支——顺序不能反：HEAD 一旦先接回分支，reset --hard 到显式
        # 提交号会直接把分支指针本身砸过去，绕过所有 CAS 保护。
        local current_target
        current_target=$(git rev-parse "$TARGET_REF")
        if ! git -C "$staging_wt" reset --hard -q "$current_target"; then
            git -C "$staging_wt" symbolic-ref HEAD "refs/heads/${TARGET_BRANCH}"
            echo "⚠️ ${TARGET_BRANCH} 所在 worktree（${staging_wt}）reset 失败，未自动同步；" >&2
            echo "   处理完手头的改动后，请在那个 worktree 里执行： git reset --hard" >&2
            return 0
        fi
        git -C "$staging_wt" symbolic-ref HEAD "refs/heads/${TARGET_BRANCH}"
        write_synced_baseline "$baseline_file" "$current_target"
        return 0
    fi

    # 它本来就有未提交改动，不能直接 reset --hard——那会抹掉别人的在制品。但也不该
    # 就此撒手：先把在制品（已暂存/未暂存/untracked 全部含）stash 起来，reset --hard
    # 到锁内现读的最新目标，再 stash pop 尝试重新应用。这是 git 原生的行级三方合并，
    # 只有真的**同一处内容**冲突（而不是同一个文件的任意改动）才会失败。pop 失败时
    # 冲突标记落在工作树里，同时 stash 里还留着一份原始改动兜底，不会丢东西。
    local current_target
    current_target=$(git rev-parse "$TARGET_REF")

    local stash_before stash_after
    stash_before=$(git -C "$staging_wt" rev-parse -q --verify refs/stash 2>/dev/null || true)

    if ! git -C "$staging_wt" stash push -u -q -m "merge-to-staging.sh auto-stash"; then
        git -C "$staging_wt" symbolic-ref HEAD "refs/heads/${TARGET_BRANCH}"
        echo "⚠️ ${TARGET_BRANCH} 所在 worktree（${staging_wt}）的未提交改动无法自动 stash，未自动同步；" >&2
        echo "   它的 git status 现在会显示误导性的改动，此时在那里直接 commit 会把本次合并反转掉。" >&2
        echo "   处理完手头的改动后，请在那个 worktree 里执行： git reset --hard" >&2
        return 0
    fi

    stash_after=$(git -C "$staging_wt" rev-parse -q --verify refs/stash 2>/dev/null || true)

    if ! git -C "$staging_wt" reset --hard -q "$current_target"; then
        git -C "$staging_wt" symbolic-ref HEAD "refs/heads/${TARGET_BRANCH}"
        echo "⚠️ ${TARGET_BRANCH} 所在 worktree（${staging_wt}）reset 失败，未自动同步；原始改动仍保留在 stash 里兜底。" >&2
        echo "   处理完手头的改动后，请在那个 worktree 里执行： git reset --hard" >&2
        return 0
    fi
    git -C "$staging_wt" symbolic-ref HEAD "refs/heads/${TARGET_BRANCH}"
    write_synced_baseline "$baseline_file" "$current_target"

    if [ "$stash_before" = "$stash_after" ]; then
        # stash push 没有新建 stash 条目（没有可存的改动），reset 已经足够。
        echo "⚠️ hub 当前有未清理的在制品，本次同步走了退化路径，建议尽快处理。" >&2
        return 0
    fi

    if git -C "$staging_wt" stash pop -q 2>/dev/null; then
        echo "⚠️ hub 当前有未清理的在制品，本次同步走了退化路径，建议尽快处理。" >&2
        return 0
    fi

    echo "⚠️ ${TARGET_BRANCH} 所在 worktree（${staging_wt}）的未提交改动与本次合并出现同一处内容冲突，未自动同步；" >&2
    echo "   工作树里已落下 git 冲突标记（<<<<<<< / ======= / >>>>>>>），原始改动同时还保留在" >&2
    echo "   git stash list 里兜底。请在那个 worktree 里手动解决冲突后 git add，或改用" >&2
    echo "   git checkout --ours/--theirs 处理，不需要重新 stash pop。" >&2
    return 0
}

attempt=0
while [ "$attempt" -lt "$MAX_RETRIES" ]; do
    attempt=$((attempt + 1))

    staging_head=$(git rev-parse "$TARGET_REF")
    feature_head=$(git rev-parse HEAD)

    if git merge-base --is-ancestor "$feature_head" "$staging_head"; then
        echo "✅ ${feature_branch} 已经包含在 ${TARGET_BRANCH} 里，无需合并。"
        exit 0
    fi

    set +e
    merge_tree_output=$(git merge-tree --write-tree "$staging_head" "$feature_head" 2>&1)
    merge_tree_status=$?
    set -e

    if [ "$merge_tree_status" -eq 0 ]; then
        new_tree=$(printf '%s\n' "$merge_tree_output" | head -n1)
        commit_message="merge: $feature_branch into $TARGET_BRANCH

Merge-Via: merge-to-staging.sh"
        new_commit=$(git commit-tree "$new_tree" -p "$staging_head" -p "$feature_head" -m "$commit_message")

        if [ "$attempt" -eq 1 ] && [ -n "${MERGE_TO_STAGING_TEST_DELAY_MS:-}" ]; then
            # 仅供 E2E 测试注入：在第一次尝试更新 ref 前制造一个可控窗口，
            # 用来确定性地复现"ref 已被别的 worktree 抢先移动"的重试路径。
            delay_s=$(printf '%d.%03d' $((MERGE_TO_STAGING_TEST_DELAY_MS / 1000)) $((MERGE_TO_STAGING_TEST_DELAY_MS % 1000)))
            sleep "$delay_s"
        fi

        if git update-ref "$TARGET_REF" "$new_commit" "$staging_head" 2>/dev/null; then
            echo "✅ 已将 ${feature_branch} 合并进本地 ${TARGET_BRANCH}（${new_commit}）"
            sync_staging_worktree "$staging_head" || true
            exit 0
        fi

        if [ "$attempt" -ge "$MAX_RETRIES" ]; then
            echo "❌ 本地 ${TARGET_BRANCH} 连续被抢先移动 ${attempt} 次仍未成功，已达重试上限，放弃。" >&2
            exit 1
        fi

        delay_ms=$((BASE_DELAY_MS * (1 << (attempt - 1))))
        if [ "$delay_ms" -gt "$MAX_DELAY_MS" ]; then
            delay_ms=$MAX_DELAY_MS
        fi
        jitter_ms=$((delay_ms / 2 + (RANDOM % (delay_ms / 2 + 1))))
        sleep_arg=$(printf '%d.%03d' $((jitter_ms / 1000)) $((jitter_ms % 1000)))
        echo "⚠️ ${TARGET_BRANCH} 已被其他 worktree 抢先移动，第 ${attempt} 次重试，等待 ${sleep_arg}s..." >&2
        sleep "$sleep_arg"
        continue
    fi

    if [ "$merge_tree_status" -eq 1 ]; then
        echo "❌ 检测到与 ${TARGET_BRANCH} 的真实内容冲突，正在当前 worktree 里合并出冲突标记..." >&2
        set +e
        git merge "$TARGET_BRANCH" >/dev/null 2>&1
        set -e
        echo "冲突文件：" >&2
        git diff --name-only --diff-filter=U >&2
        echo "" >&2
        echo "请解决冲突、git add、git commit 后重新运行 scripts/merge-to-staging.sh。" >&2
        exit 2
    fi

    echo "❌ git merge-tree 执行出错（退出码 ${merge_tree_status}）：" >&2
    echo "$merge_tree_output" >&2
    exit 1
done

echo "❌ 重试 ${MAX_RETRIES} 次仍未成功。" >&2
exit 1
