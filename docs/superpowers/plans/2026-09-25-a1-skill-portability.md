# A1 Skill 执行断点修复实施计划

**目标：** 让 `learn-video`、`extract-vision`、`close-node` 在缺少 Claude 专有工具或个人固定目录时，仍按共享语义执行或安全停止。

**架构：** 三个共享 `SKILL.md` 各自定义能力入口与回退；只对确有差异的宿主保留简短适配说明。通过静态回归、隔离路径/流程场景与受限真实宿主记录逐层验证，不把安装成功等同于运行成功。

**技术栈：** Markdown skill、Node `node:test`、现有 hskill/Bats 测试与 `skills-index.json` 发布元数据。设计依据见 [A1 规格](../specs/2026-09-25-a1-skill-portability-design.md)、[适配标准](../../reference/skill-platform-adaptation.md)和[静态审计](../../reports/2026-09-24-published-skill-platform-audit.md)。

---

## 执行前门禁

- 在明确的本地 `staging` 基线创建 `fix/a1-skill-portability` 分支及独立 worktree；设置 `core.hooksPath=.githooks`、`merge.ff=false`。现有文档分支未合并，实施者须读取本规格/计划，但不能把文档分支暗中当作 staging 基线或直接在其上改 skill。
- 记录三个 skill 的 `SKILL.md` 版本及 index 元数据。先读 `docs/reference/testing-guide.md`，再添加回归测试。
- 不修改宿主装机副本、vdl 项目、用户配置或真实 Canvas 节点；真实宿主验证使用受控测试数据与明确授权。未能执行的场景标记为未验证。

### Task 1: learn-video 模式与路径

**文件：** 修改 `skills/research/learn-video/SKILL.md`；测试 `tests/skill-portability.test.mjs`。若仅靠文字无法可靠定位当前 skill，使用 `skills/research/learn-video/scripts/` 中已有脚本的显式绝对路径参数，不新增通用安装器逻辑。

- [ ] 在静态测试加入如下用例，先运行 `node --test tests/skill-portability.test.mjs`，确认它在旧正文上失败：

  ```js
  test('learn-video: mode and script paths are host-neutral', async () => {
    const body = await readFile(resolve(root, 'skills/research/learn-video/SKILL.md'), 'utf8')
    assert.match(body, /当前宿主可用的提问方式/)
    assert.match(body, /\$SKILL_DIR\/scripts\/store_config\.py/)
    assert.match(body, /\$SKILL_DIR\/scripts\/archive\.py/)
    assert.match(body, /\$SKILL_DIR\/scripts\/build_creator_index\.py/)
    assert.doesNotMatch(body, /\$HOME\/Projects\/(harveyz-skill|Video-Learner)/)
  })
  ```
- [ ] 将模式段落改为：`运行前必须得到用户的模式选择。若消息已明确要文字、音频、视频或全部，直接映射到 transcript、audio、media 或 full；否则用当前宿主可用的提问方式列出四项并等待回答。不得因结构化提问工具不可用而默选。` 在注明 Claude 的短适配说明中保留 `AskUserQuestion` 作为示例。
- [ ] 在脚本示例前定义：`SKILL_DIR` 是当前安装或源码 skill 目录的实际绝对路径，必须先定位、绑定并引用；命令使用 `python3 "$SKILL_DIR/scripts/store_config.py" check`、`python3 "$SKILL_DIR/scripts/store_config.py" check-downstream`、`TASK_ID="<task_id>" python3 "$SKILL_DIR/scripts/archive.py"`、`python3 "$SKILL_DIR/scripts/build_creator_index.py" build`。不要留下依赖当前 shell 工作目录的 `python3 scripts/...`。
- [ ] 对 `vdl` 主命令、`rerun`、`result` 去除固定 `cd`；对 `npm link` 和 `npm run agent:serve` 写明：仅在已显式确认 Video-Learner 根目录且目标 `package.json`/脚本存在时执行，否则询问或停止。保留日志终态、后台追踪与 `DRIFT:` 用户确认门禁。
- [ ] 在临时非默认安装目录校验三个脚本文件可定位；运行目标 Node 静态测试。若要做视频实测，先确认宿主可追踪长任务；不得因测试而启动无法收尾的真实视频任务。

### Task 2: extract-vision 无委派回退

**文件：** 修改 `skills/research/extract-vision/SKILL.md`；测试 `tests/skill-portability.test.mjs`。

- [ ] 新增静态测试，运行 `node --test tests/skill-portability.test.mjs`，确认旧正文使新增断言失败：

  ```js
  test('extract-vision: delegation and vision have safe fallbacks', async () => {
    const body = await readFile(resolve(root, 'skills/research/extract-vision/SKILL.md'), 'utf8')
    assert.match(body, /当前 agent 顺序处理 OCR 文本/)
    assert.match(body, /无原图视觉能力则停止/)
  })
  ```
- [ ] 将第二步改为能力优先的顺序：有可用委派能力则把 OCR 文字交给子智能体；否则当前 agent 使用现有 goal 模板的同一字段/列表规则过滤。结果不能因执行者不同而改变形状或遗漏用户要求。
- [ ] 将 OCR 空、小字模糊分支改为：检查当前 agent 或可用委派目标是否能查看原图；能看则视觉提取；不能看则报告“当前会话无法可靠读取原图，不能判断图片是否含目标文字”并停止。保留 OCR 脚本的原退出码与依赖提示。
- [ ] 用小型人工 OCR 文本检查“金额/日期”过滤结果；用无视觉能力的模拟场景检查停止说明。只在可访问测试图像且具备授权时做真实视觉实测。

### Task 3: close-node 接手方安全退出

**文件：** 修改 `skills/agent-canvas/close-node/SKILL.md`；测试 `tests/skill-portability.test.mjs`。

- [ ] 新增静态测试，运行 `node --test tests/skill-portability.test.mjs`，确认旧正文失败：

  ```js
  test('close-node: receiver has a safe no-detach stop', async () => {
    const body = await readFile(resolve(root, 'skills/agent-canvas/close-node/SKILL.md'), 'utf8')
    assert.match(body, /Claude.*ExitWorktree\(action: "keep"\)/)
    assert.match(body, /无安全解除绑定能力.*停在第 4 步/)
    assert.match(body, /不得继续.*(?:hide|stop-node)/)
  })
  ```
- [ ] 接手方分支先检查可靠的宿主“保留 worktree 并离开/解除会话绑定”能力。Claude 的 `ExitWorktree(action: "keep")` 放在明确适配说明；其他宿主仅使用实际提供且已核对语义的能力，不杜撰 Codex/Canvas API。
- [ ] 无该能力时报告 `nodeId`、分支、worktree 绝对路径与人工解除绑定需求，立即停在 handoff 收口步骤；明确单次 `cd` 不能解除绑定，不能进入第 6/7 步。保留“接手方不合并、不删 worktree”以及交出方验收门禁。
- [ ] 仅用隔离 Canvas 测试节点（若可用）验证接手方成功离开和能力缺失两条路径；未具备安全测试环境时只做静态检查，并在报告中标未验证，不对活跃工作节点执行 `hide`/`stop-node`。

### Task 4: 发布元数据与验收记录

**文件：** 修改 `skills-index.json`、`tests/skill-portability.test.mjs`；创建 `docs/reports/2026-09-25-a1-skill-portability-verification.md` 记录本次证据。原始审计仍保留静态基线，不改写为运行结果。

- [ ] 将三个 `SKILL.md` patch 版本分别从 `1.9.0`、`1.2.0`、`1.0.3` 升至 `1.9.1`、`1.2.1`、`1.0.4`；若实施前 baseline 已变化，以实际版本的下一 patch 为准。用 `publish-skill` F8 规则计算去除 version 差异后的 SHA-256 前 16 位，并同步 index 的 `contentVersion`/`contentHash`。
- [ ] 运行 `node --test tests/skill-portability.test.mjs` 与涉及实际脚本的定向测试，记录通过数/失败数。检查目标 skill 文件与脚本被发布包包含；若 package 验证失败，修复打包范围后重测。
- [ ] 运行 `npm test`；如重现既有公网 browser-fetch 失败，记录精确用例和错误，不能把之前的豁免扩展成本次通过。运行 `git diff --check`；暂存后再运行 `git diff --cached --check`，审查三项验收表的每一条以及未覆盖宿主。
- [ ] 验证完成后提交到修复分支；只在用户明确要求合并时从该 worktree 运行 `scripts/merge-to-staging.sh`，不推送、不部署。需要装机验证时，从已集成的 `staging` 归档部署，并核对装机 `SKILL.md` 版本。

## 验收输出

交付时逐项列出：源文件与 index 版本/hash、静态与定向测试结果、真实宿主/隔离环境的通过或未验证格子、保留的风险。只有实际运行过的格子可标“通过”；三项均满足 A1 规格且没有未解释的失败，才可称源修复已完成。
