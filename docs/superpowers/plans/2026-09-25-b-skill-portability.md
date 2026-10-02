# B 类 Skill 平台适配最小修复实施计划

**目标：** 修复七个已发布 skill 的共享宿主表述、安装路径和模式前提，不新增平台能力。

**架构：** 共享 `SKILL.md` 表达任务语义，现有 `platforms/` 保留宿主命令；引用文件与骨架资产跟随 `init-project` 修正。用小范围静态契约及安装产物检查验证，更新版本与索引哈希。

**技术栈：** Markdown/YAML、Node.js `node:test`、现有 hskill 索引。

**规格：** `docs/superpowers/specs/2026-09-25-b-skill-portability-design.md`

---

### Task 1: 三个 feed skill 的共享入口

**文件：** `skills/feed/sync-{xtimeline,ytchannel,website}/SKILL.md`，`tests/skill-portability.test.mjs`

- [ ] 先在 `tests/skill-portability.test.mjs` 添加三个用例：共享入口以单次运行与条件调度描述，不把 `/loop` 作为通用入口；现有脚本、提交点与失败边界仍在。运行 `node --test tests/skill-portability.test.mjs`，预期三个新增用例失败。
- [ ] 最小修改三个 description 与 run 标题，必要时在正文用一句话区分单次运行与调度；不改抓取步骤和既有 `platforms/`。运行同一测试，预期通过。

### Task 2: `question-me` 与 `rephrase` 的执行主体

**文件：** `skills/coding/question-me/SKILL.md`，`skills/coding/rephrase/SKILL.md`，`tests/skill-portability.test.mjs`

- [ ] 先添加两个定向测试，分别覆盖“自动提议须等确认、当前 agent 执行”和“仅手动调用、可靠性按猜错代价分支”；运行定向测试，预期失败。
- [ ] 最小替换 Claude 主体措辞，不动决策树与改写规则；运行定向测试，预期通过。

### Task 3: `init-project` 引用与骨架

**文件：** `skills/coding/init-project/references/template-schema.md`，`skills/coding/init-project/assets/skeleton/README.md`，`tests/templates.test.mjs`

- [ ] 先添加测试，验证 schema 以当前 skill 目录定位模板、骨架 README 所列文件存在于骨架资产；运行 `node --test tests/templates.test.mjs`，预期失败。
- [ ] 修正 schema 的固定 Claude 路径与过时文件名，修正 README 链接；运行同一测试，预期通过。

### Task 4: `runby-opencode` 模式前提

**文件：** `skills/mint/runby-opencode/SKILL.md`，`tests/skill-portability.test.mjs`

- [ ] 先添加用例覆盖 verify 的显式源路径优先、实际 opencode 配置核对、未经确认不改配置，以及 compare 缺端时不伪称比较结果；运行定向测试，预期失败。
- [ ] 以最小文字修改路径解析与两种模式的前提；运行定向测试，预期通过。

### Task 5: 版本、索引和集成验证

**文件：** 七个 `SKILL.md`，`skills-index.json`，`tests/skill-portability.test.mjs`

- [ ] 将七项 patch 版本各递增 1，并按 `sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' ... | shasum -a 256 | cut -c1-16` 计算哈希；使用 `apply_patch` 更新索引。
- [ ] 验证版本与哈希一致、npm 发布包包含七项及 `init-project` 骨架；运行 `node --test tests/skill-portability.test.mjs tests/templates.test.mjs`、相关 skill 测试、`npm test`。完整测试失败时逐项记录，不能称全绿。
- [ ] 审查 `git diff --check` 和基线到 HEAD 的变更，只提交本批内容；不合并、不推送、不部署。

## Review Focus

检查措辞修复是否改变了定时授权、feed 游标提交顺序、question-me 的确认门禁、rephrase 的手动边界，或将 runby-opencode 的有意 Claude 对比范围错误泛化。静态测试不能证明任一目标宿主端到端可用。
