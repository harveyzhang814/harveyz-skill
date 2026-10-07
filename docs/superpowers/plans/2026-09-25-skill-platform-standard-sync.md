# Skill 平台适配标准单源分发实施计划

**目标：** 让 `init-skill` 与 `contribute-skill` 使用同一份平台适配标准，安装后仍可离线读取，并消除 `init-skill` 自身的宿主和 worktree 假设。

**架构：** `docs/reference/skill-platform-adaptation.md` 是唯一手工编辑的权威文本；同步器确定性生成两个 skill 内的完整副本及 `SKILL.md` 源摘要标识。两个入口执行语义检查，`publish-skill` 仅检查分发和元数据，不代替宿主实测。

**技术栈：** Node.js ESM、`node:test`、Markdown/YAML、Git worktree、npm pack。

**规格：** `docs/superpowers/specs/2026-09-25-skill-platform-standard-sync-design.md`

---

## 前置门禁

当前 `staging` 尚无 `docs/reference/skill-platform-adaptation.md`；它在 `doc/skill-platform-adaptation-standard` 分支。执行实现任务前，先确认用户指定的集成方式，使权威文件成为从明确 `staging` 基线创建的实施分支中的受跟踪文件。不得为绕过门禁而读取某个未合并 worktree 的实体路径，也不得在未获明确指令时合并 `staging`。

检查命令：

```bash
git cat-file -e staging:docs/reference/skill-platform-adaptation.md
git status --short --branch
```

第一条在目前状态预期失败；此时只完成计划，不进入 Task 1。门禁解除后创建 `fix/skill-platform-standard-sync` 独立 worktree，明确以当时的 `staging` 为基线，配置 `core.hooksPath=.githooks` 与 `merge.ff=false`。保留本计划与规格在该实施分支中的可追踪副本。

## 任务接口

| 任务 | 产出 | 后续消费 |
|---|---|---|
| 1 | 同步器、两个生成副本、两个摘要标识 | 任务 2、3 读取副本；任务 4 验证包内文件与哈希 |
| 2 | `init-skill` 创建时的适配检查与安全 worktree 流程 | 任务 4 运行受控案例及隔离工作区验证 |
| 3 | `contribute-skill` 导入检查、`publish-skill` 分发核对 | 任务 4 做包与元数据验收 |
| 4 | 版本、索引、验证报告 | 独立审查；用户决定是否合并 |

### Task 1：确定性同步与漂移检测

**文件：**
- 新建 `scripts/sync-skill-platform-standard.mjs`
- 新建 `tests/platform-standard-sync.test.mjs`
- 生成 `skills/mint/init-skill/references/platform-adaptation.md`
- 生成 `skills/mint/contribute-skill/references/platform-adaptation.md`
- 修改两个消费者的 `SKILL.md`，各插入一行 `<!-- platform-standard-sha256: <64 位十六进制摘要> -->`

- [ ] **Step 1（RED）：** 用 `mkdtemp` 建隔离夹具，写入权威文本、两个含旧摘要标识的 `SKILL.md` 和两个旧副本；测试 `--check` 返回非零且不改任何字节，`--write` 使两份副本内容相同且摘要标识等于 `createHash('sha256').update(source).digest('hex')`，第二次 `--write` 无 diff。另以注入的 rename 失败验证已替换目标回滚。测试只在临时目录运行，不碰真实 skill。
- [ ] **Step 2：** 运行 `node --test tests/platform-standard-sync.test.mjs`，预期因同步器不存在而失败，不接受测试语法错误作为 RED。
- [ ] **Step 3（GREEN）：** 同步器导出 `syncPlatformStandard({ root, mode, fsApi })`，CLI 只接受 `--check` 或 `--write`；路径使用固定白名单，拒绝未知参数。生成副本格式固定为 `<!-- Generated from docs/reference/skill-platform-adaptation.md; sha256: <digest>. Do not edit. -->\n\n<源文件全文>`；标识仅替换两个 `SKILL.md` 中唯一匹配的整行，缺失或重复就报错。先读齐四个目标并在内存生成期望内容；`--check` 只比较并报出漂移文件。`--write` 先把变更写到同目录临时文件，保留原字节备份，再逐一替换；失败则按逆序恢复，恢复失败时列出准确路径并退出非零。`fsApi` 只为故障注入测试使用，CLI 采用真实 `node:fs/promises`。
- [ ] **Step 4：** 重跑定向测试；对真实仓库先执行 `node scripts/sync-skill-platform-standard.mjs --check`（预期漂移），再执行 `--write` 与 `--check`（预期通过），再执行一次 `--write` 并确认 `git diff` 无新增变化。
- [ ] **Step 5：** 提交同步器、测试与生成文件。提交前只暂存本任务明确文件，不处理索引或合并分支。

### Task 2：`init-skill` 创建门禁与自身 worktree 流程

**文件：**
- 修改 `skills/mint/init-skill/SKILL.md`
- 修改 `skills/mint/init-skill/references/skill-standard.md`
- 新建或扩展 `tests/skill-platform-authoring.test.mjs`

- [ ] **Step 1（RED）：** 加入测试：Step 2 同时要求读取本地 `skill-standard.md` 与 `platform-adaptation.md`、记录目标宿主/限定范围/能力/路径/回退/验证状态；Step 3 只为真实差异生成适配文件；正文不以 `Read`／`Write` 工具或“由 Claude 推断”为通用必经入口。另检查写入步骤发生在显式 `staging` 基线创建 worktree 之后，目标冲突与脏工作区会停止。运行 `node --test tests/skill-platform-authoring.test.mjs`，预期这些新增断言失败。
- [ ] **Step 2（GREEN）：** 将 Step 0 的主体改为当前 agent；Step 2 加载随包安装的 `references/platform-adaptation.md`，用“通过／缺口／不适用＋理由”报告。Step 3 预览共享流程、必要的短适配章节或 `platforms/SKILL.<host>.md`，无差异则不建空适配器。把原 Step 4/5 调整为“先用户确认，再从明确 `staging` 基线创建独立分支和 worktree、配置 hooks、确认目标目录不存在、再写入全部预览文件并提交”；宿主原生 worktree 必须能绑定明确基线，否则用显式路径 Git fallback。`skill-standard.md` 区分领域/技术栈 `references/<dim>/` 与宿主接口 `platforms/`。
- [ ] **Step 3：** 重跑定向测试；在临时 Git fixture 中受限演练目标目录已存在、脏工作区和正常创建三种分支，核对未向 `staging` 工作区写入。模型执行验证只在当前可用宿主做受控案例，不把静态断言写成七平台实测。
- [ ] **Step 4：** 提交本任务文件；若同步器因此更新摘要标识，先重跑 `--check` 并按其结果决定是否需要 `--write`，不得手改生成副本。

### Task 3：导入门禁与发布边界

**文件：**
- 修改 `skills/mint/contribute-skill/SKILL.md`
- 修改 `skills/mint/publish-skill/SKILL.md`
- 扩展 `tests/skill-platform-authoring.test.mjs`

- [ ] **Step 1（RED）：** 加入测试，要求 `contribute-skill` 在复制摘要和用户确认前读取自己的本地副本，报告“确认断点／有意限定／待验证风险”，不改原有回源确认；要求 `publish-skill` 只验证生成副本被打包及版本/索引状态，不输出语义兼容通过。运行定向测试，预期新增用例失败。
- [ ] **Step 2（GREEN）：** 将适配评估加在 `contribute-skill` 的源目录确认之后、复制目标摘要之前；仅对已确认的必要内容修改生成 diff 并等用户确认，不静默泛化单宿主 skill。`publish-skill` 增加两副本的打包检查与“未实测不宣称兼容”的报告字段，保持原 F1–F9/R1–R3 职责边界。
- [ ] **Step 3：** 重跑定向测试；以宿主专有命令无回退、明确单宿主限定、已有顺序回退三份受控输入核对分类与报告。提交本任务文件。

### Task 4：版本、分发和最终验证

**文件：**
- 修改 `skills/mint/{init-skill,contribute-skill,publish-skill}/SKILL.md` 的版本字段
- 修改 `skills-index.json` 的三个 `contentVersion`/`contentHash`
- 新建 `docs/reports/2026-09-25-skill-platform-standard-sync-verification.md`

- [ ] **Step 1（RED）：** 加入测试按现有 F8 算法计算三个 `SKILL.md` 去版本后的 SHA-256 前 16 位，核对索引值与版本；先运行，预期因尚未同步索引而失败。把两个生成副本与三个 `SKILL.md` 纳入 npm dry-run 包清单断言。
- [ ] **Step 2（GREEN）：** `init-skill` 与 `contribute-skill` 按行为扩展递增 minor；`publish-skill` 依实际检查项变更递增相应版本。用 `apply_patch` 更新索引，不让同步器直接改版本/索引。运行 `node scripts/sync-skill-platform-standard.mjs --check`、相关 Node 测试与 `npm pack --dry-run --ignore-scripts --json`，预期通过。
- [ ] **Step 3：** 运行 `npm test` 并记录完整退出状态；如果外部 `claude -p` hook 或公共网页测试停滞/失败，记录具体用例、耗时和中断事实，再独立运行本次相关的测试组，不称全绿。运行 `git diff --check` 与 `git status --short --branch`，检查仅有本计划文件范围内的改动。
- [ ] **Step 4：** 在报告中列出已覆盖宿主、未验证宿主、三个受控案例、包内容、哈希和所有红项；提交报告与索引。独立只读审查整个基线到 HEAD 的差异。仅在用户明确要求时用 `scripts/merge-to-staging.sh` 合并本地 `staging`，不自动推送或部署。

## 自检与执行移交

规格的单源/离线副本/分类边界对应任务 1–3；漂移、打包、工作区安全、受控场景与版本哈希对应任务 1–4。实施者若发现当前 installer 对额外 `references/` 文件有排除规则，先以 npm dry-run 证据定位，再在本计划范围内修正打包；不得仅靠文件存在断言。实施前置门禁未解除时，应报告并等待用户决定权威标准分支的集成方式，不擅自合并。
