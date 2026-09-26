# Skill 平台适配标准单源分发验证记录

基线：本地 `staging` 的 `4960dea`；实施分支：`fix/skill-platform-standard-sync`。本报告只评价本次标准同步与三个 mint 入口，不声称七宿主端到端兼容。

## 交付与判定

- 唯一手工编辑的标准：`docs/reference/skill-platform-adaptation.md`。同步器确定性生成 `mint/init-skill`、`mint/contribute-skill` 各自的完整离线副本和 `SKILL.md` 摘要标识。`--check` 只读报漂移；`--write` 后复查通过，重复写入无变化；注入第三次替换失败时四个目标都恢复原字节。
- `init-skill` 创建时读取两份本地标准，按目标宿主、能力、路径、回退和验证状态检查；预览确认后先建立明确 `staging` 基线的独立 worktree，再写文件。`contribute-skill` 在复制确认前分类来源风险，回源另需确认。`publish-skill` 只检查同步、包内容与元数据，不给语义兼容结论。
- `npm pack --dry-run --ignore-scripts --json` 的文件清单包含两份 `references/platform-adaptation.md` 和 `init-skill`、`contribute-skill`、`publish-skill` 三个 `SKILL.md`；安装后的两个消费者不需要访问仓库 `docs/`。

| Skill | 版本 | `contentHash`（F8） |
|---|---:|---|
| `mint/init-skill` | 1.3.0 | `260c22e1e1a6b0a5` |
| `mint/contribute-skill` | 1.1.0 | `f48338e6d5267a28` |
| `mint/publish-skill` | 1.6.0 | `6ce6b83f99b11d82` |

## 受控案例与宿主证据

使用 Codex 子 Agent 的 Terra 模型，对改动前后同一段 skill 指令做无写入 dry-run；这是当前宿主的受控代理行为探针，不是 Claude、Codex 或其他宿主的完整真实任务执行。

| 案例 | 改动前 | 改动后 |
|---|---|---|
| `init-skill`：同时面向 Claude/Codex，当前 `staging` 有无关脏文件 | 先在 `staging` 写新 skill，再检查脏状态并停下；不检查适配 | 识别 Claude 提问接口与 Codex 对话回退，标注未实跑；在创建 worktree 或写文件前因脏状态停止 |
| 导入：共享流程强制 `AskUserQuestion`，无回退 | 无平台分类 | 确认断点，影响 Codex；只展示候选 diff，不擅改源文件 |
| 导入：明确 Claude-only | 无平台分类 | 有意限定，不机械泛化七宿主 |
| 导入：共享提问能力含顺序对话回退，但无实跑 | 无平台分类 | 待验证风险，不冒称端到端兼容 |

另在一次性 Git 仓库中执行 `init-skill` 的显式路径 fallback：正常路径从 `staging` 提交 `64d9ade…` 创建 `feature/init-sync-calendar`，新 skill 仅出现在该分支的提交 `32ae5eb…`，原 `staging` 工作区保持干净且无新文件；目标已存在时在创建分支/worktree 前停止；没有可靠原生入口且 Git fallback 不可用时停止、不写当前 checkout。演练发现对常见 `.gitignore` 规则 `.worktrees/`，`git check-ignore -q .worktrees` 会误判未忽略；已改为检查 `.worktrees/` 并加回归断言。以上是隔离夹具验证，不是实际用户仓库的创建任务。

未覆盖真实 Claude、Hermes、Pi、OpenCode、Cursor、OpenClaw 任务执行，也未实跑这三个 skill 的完整创建／导入／发布操作。文本规则、同步脚本和包内容有定向验证；宿主 API 与权限仍需目标宿主受限实测。

## 测试结果与红项

- `node --test tests/platform-standard-sync.test.mjs tests/skill-platform-authoring.test.mjs`：12/12 通过；包括故障注入验证备份准备失败时无临时文件残留。
- 默认 Node 命令 `node --test tests/*.test.mjs tests/harness/*.test.mjs`：363 个用例，356 通过、7 跳过、0 失败；新增测试已接入 `npm test`。
- 首次完整 `npm test`（接入新测试前）退出 0：顶层 Bats 168/168、14 组自带测试通过，Node 351 个用例中 344 通过、7 跳过。该次不覆盖新增两个 Node 文件。
- 接入新测试后的完整 `npm test` 第二次运行停在外部 LLM hook 的第 38 个 Bats 用例，约两分钟无新输出后主动中断；该用例显示状态 130，最终命令退出 1，实际只执行 38/168 个顶层 Bats 用例。**第二次完整测试未通过，不能视为绿色或豁免通过。** 随后单独运行默认 Node 命令，结果如上。此次中断不构成本次 skill 改动失败的证据，但完整默认门禁仍需一次不受外部 hook 阻塞的成功运行。
- 第三次完整 `npm test` 通过了外部 hook，但 `tools/browser-fetch` 的 220 个用例有 5 个失败、215 个通过，命令退出 1；失败均为访问 `https://example.com/` 时 `Page.goto` 超过 30 秒，分别发生在 `test_cli_fetch.py::test_article_json_format_returns_blocks_and_writes_nothing`、`test_evaluate_js.py::test_evaluate_js_returns_page_evaluate_result`，以及 `test_fetch_article.py` 的三个 thin-content/default-cookie 场景。首次完整运行同组 220/220 通过；故障与本次改动文件无重叠，但第三次完整门禁仍是红色。未提高生产超时或放宽浏览边界以掩盖环境波动。
- 复审修复后第四次完整 `npm test` 在外部 LLM hook 第 37 个用例约两分钟无输出，主动中断；该用例状态 130，顶层 Bats 仅执行 37/168，最终退出 1。最终版本随后单独运行默认 Node 命令，363 个用例 356 通过、7 跳过、0 失败；标准同步 `--check` 通过。**最终完整默认门禁仍未得到绿色结果。**

本次未合并、推送或部署。是否接受外部 hook 阻塞下的分项证据，以及是否合并到本地 `staging`，由用户另行决定。
