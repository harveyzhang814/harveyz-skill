# 探索：project-release 自我学习机制

> 这是一个开放性设计探索，不是实现方案。目的是想清楚「skill 跨项目积累经验」这件事的本质和可能路径。

---

## 核心问题

现在的 Init 阶段每次都从零开始扫描、问问题。如果 skill 已经在 10 个 npm 项目上跑过，它对第 11 个 npm 项目的初始猜测应该比第 1 次好得多。

**自我学习要解决的问题**：把跨项目的经验沉淀成「猜测」，让 Init 问更少的问题、猜中更多的细节。

---

## 知识库放在哪里

**项目级**：`.hskill/release-profile.md` — 已有，记录单个项目的确定结论。

**全局级**：`~/.hskill/release-knowledge.md`（或 `~/.hskill/release-knowledge/`）— 跨项目的经验汇总。

选择 `~/.hskill/` 的理由：
- 和项目级 `.hskill/` 同命名空间，语义一致
- 不污染任何单个项目的 repo
- 不依赖 Claude Code（`.claude/` 是 Claude 专属，`~/.hskill/` 是工具链的）

---

## 知识库里存什么

不存「项目 A 用了 npm」这种事实，而是存**归纳出来的模式**：

```markdown
## 模式库

### 生态系统识别
- 见到 package.json + 无 `"private": true` → 大概率 npm publish
- 见到 package.json + `"private": true` → 可能是 monorepo 子包或内部项目，需问发布方式
- 见到 pyproject.toml + [tool.poetry] → 大概率 poetry publish
- 见到 pyproject.toml + build-backend → python -m build + twine upload
- 见到 Cargo.toml → cargo publish，tag 通常不带 v 前缀

### 分支拓扑
- 有 staging 分支 → 几乎都是三层模型（feature → staging → main）
- 无 staging、有 develop → Git Flow
- 无 staging、无 develop → GitHub Flow
- 有 workflow-config.yml → 直接读它，比猜更准

### 版本文件组合
- package.json + package-lock.json → lock 文件由 npm version 自动更新，不要手动改
- pyproject.toml + Cargo.toml → PyO3 项目，两个都要更新
- 有 CHANGELOG.md → 大概率 Keep a Changelog 格式，但验证一下头部格式

### 常见特殊规则
- 有 scripts/generate-npmignore.js → 发版前执行它
- 有 .github/workflows/publish.yml → 可能是 CI 自动发布，问用户
- tag 有 annotated 要求 → 通常在 pre-push hook 里有检查逻辑
```

---

## 学习在什么时机发生

**方案 A：Execute 成功后主动写入**

每次 Execute 完成后，skill 把这个项目的 profile 提炼成「新模式」追加到知识库：

```
Execute 完成
  → 读取 .hskill/release-profile.md
  → 提取可泛化的部分（去掉项目特有内容，保留生态系统级规律）
  → 追加到 ~/.hskill/release-knowledge.md
  → 去重（相同模式不重复记录）
```

问题：如何判断什么是「可泛化的」？目前只能靠模型判断，没有固定规则。

**方案 B：Init 结束时由用户确认写入**

Init 生成 profile 后，问用户：「是否把这个项目的配置模式贡献到全局知识库？」

优点：用户有控制权，知识库内容是有意识选择的，不会混入奇怪的项目。

**方案 C：只在 Init 时读、不主动写**

知识库由用户手动维护（或由 skill 提示「你可以把这个加进去」），Init 时只读取做参考。

最保守，但知识库增长慢，需要用户操心。

---

## Init 如何利用知识库

现在的 Init 流程：扫描文件 → 问用户 → 写 profile。

引入知识库后的 Init 流程：

```
扫描文件
  → 读取 ~/.hskill/release-knowledge.md
  → 基于文件组合匹配已知模式
  → 生成「预填充草稿 profile」，标注哪些是推断、哪些需确认
  → 只就「不确定的部分」问用户
  → 写 profile
```

效果：第一次初始化一个 npm 项目，问 5 个问题；第 5 次，可能只问 1 个（「发布命令确认一下？」）。

---

## 最难的问题

### 1. 知识腐化

模式可能随生态系统版本变化而失效（比如 poetry 的配置格式改了）。知识库需要有时间戳，Init 时可以提示「该模式已有 6 个月未被验证，以下推断仅供参考」。

### 2. 冲突模式

不同项目对同一生态系统有不同做法（比如有的 npm 项目手动改 package.json 而不用 `npm version`）。知识库需要记录「置信度」或「见过几次」，而不是把第一次见到的当唯一真理。

### 3. 知识库格式

存成 markdown（人可读、可手动编辑，但模型解析不稳定）还是 JSON（结构化、易查询，但人工维护成本高）？

一个可能的中间方案：用 markdown 存，但每条模式有固定的行格式，方便用 grep 查询：

```
[npm] package.json+no-private → publish:npm publish | confidence:high | seen:7
[python] pyproject.toml+poetry → publish:poetry publish | confidence:medium | seen:3
```

### 4. 边界：什么不该进知识库

- 项目特有的路径（`scripts/generate-npmignore.js` 只在这个项目存在）→ 不该进
- 生态系统级通用规律（`npm version` 自动更新 lock 文件）→ 应该进
- 公司/团队级约定（tag 用 annotated）→ 模糊地带，取决于用户是否跨项目复用同一套约定

---

## 一个最小可行方案草图

不做完整的学习系统，只做「Init 猜测更聪明」这一件事：

1. Init 扫描到文件组合后，检查 `~/.hskill/release-knowledge.md` 是否有匹配条目
2. 有匹配 → 把推断结果展示给用户，问「这些信息是否正确？」，用户确认后直接生成 profile，省掉大部分问答
3. 无匹配 → 走现有流程，结束时问用户「是否把这个项目的配置加入知识库」
4. 知识库格式保持 markdown，人工可读、可编辑

这个方案的价值：初次初始化一个「熟悉生态系统」的项目，可以从 5 步问答压缩到 1 步确认。

---

## 尚未回答的问题

- 知识库要不要版本控制？（放进 dotfiles repo？）
- 团队场景：知识库能不能共享？（放进项目 `.hskill/team-knowledge.md`？）
- 和 profile 的边界：profile 是「这个项目确定的事」，knowledge 是「跨项目的经验」，两者不能混
- 知识库大了之后怎么检索？（目前靠模型全文读，几十条还好，几百条开始有压力）
