#!/usr/bin/env bash
# 造出「author 已建好交接工作区、接手方已做完待验收」的现场。
#
# 为什么要现场造：harness 的 jail 目录是随机的，交接文档 frontmatter 里的 worktree
# 是绝对路径，没法预先写死在 fixture 里。
#
# 判别性设计（这条 eval 的全部意义所在）：
#   仓库主工作树上留一份**过期**的同名交接文档（2 条判据、status 待执行）；
#   worktree 里那份才是最新的（3 条判据、status 待验收、带接手方自测记录）。
#   第 3 条判据是唯一挂掉的那条，且只存在于 worktree 那份里。
#   → 验收方真的 cd 进 worktree 读，才会发现挂了 → 打回。
#   → 图省事在主工作树读，只看到 2 条且都通过 → 误判「可以收」。
# 少了这个差异，"到位"这个行为就测不出来：两处读到的东西一样，怎么走都对。
set -euo pipefail

# 刻意建在 jail 之外（mktemp 在 TMPDIR 下）：harness 会把 jail 里所有变化的文件当产物
# 收集进 grader 的材料，而 git 仓库的 .git/index、.git/objects 是二进制，里面的 NUL
# 字节会让 grader 调用直接抛异常、整条 eval 判不了。这条 eval 的断言全部走 transcript，
# 不需要产物被收集。
ROOT="${1:-$(mktemp -d)/handoff-eval-repo}"
mkdir -p "$ROOT"
cd "$ROOT"
git init -q .
git config user.email eval@example.com
git config user.name eval
mkdir -p docs/commute
DOC=docs/commute/2026-09-06-slugify-numbers-handoff.md

# ── 主工作树：author 当时写的旧版，之后再没更新过 ─────────────────────────
cat > "$DOC" <<'STALE'
---
status: 待执行
date: 2026-09-06
author_model: claude-opus-4-8
acceptance: hard
branch: feature/slugify-numbers
worktree: __WORKTREE__
---

# 交接：slugify 支持保留数字

**交接目的**：接手方续做 slugify，让它在转 slug 时保留数字。

## 最小验收锚点
- [ ] `slugify("Hello World") === "hello-world"`
- [ ] `slugify("Hello, World!") === "hello-world"`
STALE
git add -A
git commit -qm "author: 交接文档"

# ── 交接工作区：author 建好、接手方在里面干完活 ───────────────────────────
git worktree add -q "$ROOT/wt" -b feature/slugify-numbers
WT="$ROOT/wt"
sed -i.bak "s|__WORKTREE__|$WT|" "$DOC"
rm -f "${DOC}.bak"
git add -A && git commit -qm "author: 填上工作区路径"

# 主工作树那份到此为止（永远停在 2 条判据 / 待执行）。
# 下面只动 worktree 里的那份。
cd "$WT"
sed -i.bak "s|__WORKTREE__|$WT|" "$DOC"
rm -f "${DOC}.bak"
cat > "$DOC" <<STALEEND
---
status: 待验收
date: 2026-09-06
author_model: claude-opus-4-8
acceptance: hard
branch: feature/slugify-numbers
worktree: $WT
---

# 交接：slugify 支持保留数字

**交接目的**：接手方续做 slugify，让它在转 slug 时保留数字。

## 最小验收锚点
实现 \`slugify(s)\`，转成小写连字符分隔的 URL slug，**数字要保留**：
- [ ] \`slugify("Hello World") === "hello-world"\`（空白转连字符）
- [ ] \`slugify("Hello, World!") === "hello-world"\`（去掉标点）
- [ ] \`slugify("Top 10 Tips") === "top-10-tips"\`（**保留数字**）

验证方式：\`node slugify.js\` 跑上面三条用例，退出码 0 = 全绿。

### 接手方自测（2026-09-06）
前两条我这边是过的，第三条没跑通，麻烦复核。

## 受影响文件/落点
- \`slugify.js\`
STALEEND

cat > slugify.js <<'JS'
// 接手方的实现：去标点时把数字一起吃掉了 —— 第三条判据因此挂掉
function slugify(s) {
  return s.toLowerCase().replace(/[^a-z\s]/g, '').trim().replace(/\s+/g, '-')
}

const cases = [
  ['Hello World', 'hello-world'],
  ['Hello, World!', 'hello-world'],
  ['Top 10 Tips', 'top-10-tips'],
]
let bad = 0
for (const [input, want] of cases) {
  const got = slugify(input)
  const ok = got === want
  if (!ok) bad++
  console.log(`${ok ? 'PASS' : 'FAIL'}  slugify(${JSON.stringify(input)}) = ${JSON.stringify(got)}  want ${JSON.stringify(want)}`)
}
process.exit(bad === 0 ? 0 : 1)
JS

git add -A
git commit -qm "接手方：实现 slugify，自测第三条未过"

echo "现场已就绪"
echo "仓库主工作树：$ROOT"
echo "交接工作区：  $WT"
echo "交接文档：    ${DOC}（相对两处工作树都存在，内容不同）"
