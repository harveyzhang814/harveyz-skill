---
name: release-project
description: "Universal project release skill. Triggers on: release, bump version, publish, new version, cut release. Two phases: Init (first run — scans project and generates .hskill/release-project/release-profile.md); Execute (daily use — reads profile and runs full release flow). Works with npm, Python, Rust, Java, or any versioned project."
user_invocable: true
version: "1.2.0"
---

# release-project

## 入口判断

`.hskill/release-project/release-profile.md` 不存在，或用户说「重新初始化」→ 读 `references/init.md` 执行 Init（覆盖旧 profile）。存在 → 执行下方 Execute。

---

## Execute 阶段

**读取 `.hskill/release-project/release-profile.md`，完全按照它执行。** profile 是唯一依据，不在 profile 里的事不要自己发明；profile 有误时，请用户直接编辑后重新触发。

### Step E-0 — 读取 profile + 前置检查

先完整读取 profile，理解：发版起点分支是什么、版本文件清单是什么、合并流向是什么、发布命令是什么。

然后按 profile 做前置检查，通常包括：当前分支是发版起点分支；`git status --porcelain` 为空；`git fetch origin` 后 `git rev-list --count HEAD..origin/<当前分支>` 为 0。另执行 profile「特殊规则」中的发版前检查（如测试）。任一项失败 → 停下告知用户；修复后从 E-0 重新开始。

### Step E-1 — 确定新版本号

从版本文件清单里第一个带版本号字段的文件（如 `package.json` 的 `version`）读取当前版本。

如果项目有 CHANGELOG，展示其中 Unreleased 部分的内容；没有则询问用户本次改动摘要，或经用户确认跳过 CHANGELOG 更新。

按 semver 建议升级类型（只有 fix/docs/chore → patch；兼容的新功能 → minor；breaking change → major），等用户确认后定下 NEW_VERSION。

### Step E-2 — 更新 CHANGELOG（如适用）

如果 profile 中记录了 CHANGELOG 文件，按该文件的**现有格式和风格**更新——把本次版本从 Unreleased 区域移动到有版本号的区段，保留一个空的 Unreleased 区域供下次使用。

### Step E-3 — 更新版本文件

按 profile 中版本文件清单的顺序，用 profile 里说明的方式逐一更新每个文件。

更新完后用 `git diff` 确认所有文件已正确改动，没有遗漏或多余修改。

### Step E-4 — 执行 profile 中的发版前脚本（如有）

profile「特殊规则」里列出的、需要在提交前执行的脚本或命令，在这里执行。

### Step E-5 — 创建 release 分支并提交

按 profile 中的分支命名规范创建 release 分支，提交所有版本文件改动：

```bash
git checkout -b <profile 中的 release 分支格式，如 release/NEW_VERSION>
git add <profile 中列出的所有版本文件>
git commit -m "<profile 中的 commit message 格式>"
```

### Step E-6 — 按合并流向执行本地合并 + 打 tag

读取 profile 中的合并流向，逐步执行本地合并。在最终目标分支（通常是 main/master）上按 profile 的 tag 格式（如 `vNEW_VERSION` 或 `NEW_VERSION`）打 tag：profile 要求 annotated tag 用 `git tag -a <tag> -m "<tag message>"`，否则用 `git tag <tag>`。

所有操作只在本地做，不推送。

### Step E-7 — 输出待执行清单

本地操作完成后，整理出推送和发布指令供用户手动执行：

```
== 本地已完成，待执行 ==

# 推送（按 profile 中的合并流向列出所有需要推送的分支）
git push origin <branch1>
git push origin <branch2>
git push origin <tag>

# 发布
<profile 中的发布命令>
```

### Step E-8 — 收尾

用户确认成功后输出摘要，列出：版本变更（旧 → 新）、CHANGELOG 更新情况、tag、已推送分支、发布目标。

询问是否清理 release 分支（本地 + 远端），用户同意才删。
