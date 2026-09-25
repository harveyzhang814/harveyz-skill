# A1 Skill 执行断点修复设计

## 目标与范围

按 [平台适配标准](../../reference/skill-platform-adaptation.md) 修复静态审计 A1 的三个发布条目：`research/learn-video`、`research/extract-vision`、`agent-canvas/close-node`。保留用户可见的任务语义和安全边界，只解除宿主专有工具、个人固定目录作为必经条件的问题。本轮不改安装器、不生成七份平台变体、不部署装机副本，也不处理 A2/B 批次。

## 共同接口

共享 `SKILL.md` 描述“需要什么能力、输入输出、何时停止”；宿主专有调用仅作为标明平台的示例。运行前判断当前会话是否具备所需能力，缺失时使用共享流程列出的回退；回退不能降低用户确认、数据准确性或 worktree 所有权要求。安装目录从当前 skill 实际所在位置取得，不使用维护者仓库目录作为默认值。一次性操作不能冒称已经安排自动持续执行。

## learn-video

1. 模式选择的语义是“运行前得到用户明确的模式选择”。用户消息已明确“只要文字/音频/视频/全部”时直接映射；否则通过当前宿主的结构化提问工具或普通对话展示四个模式，并等待回答。Claude 的 `AskUserQuestion` 只能在注明 Claude 的适配说明中出现。不得因提问工具不可用而默选 `transcript`。
2. `store_config.py`、`archive.py`、`build_creator_index.py` 均从当前 skill 的实际目录运行；示例先绑定并引用绝对 `SKILL_DIR`。不得将 `$HOME/Projects/harveyz-skill` 作为运行前提。`check-downstream` 输出 `DRIFT:` 时仍只报告修复命令，由用户决定是否修改 vdl/scholia 配置。
3. `vdl` 主命令、`rerun`、`result` 使用已发现的 CLI；只有 `npm link`、`npm run agent:serve` 等源码仓库命令需要 Video-Learner 项目根目录。先采用用户显式给出的根目录并验证目标脚本存在；未提供时询问或停止，不猜 `$HOME/Projects/Video-Learner`。不在本批修改 vdl 本身的命令行为。
4. 后台执行、日志终态、失败重跑及配置写入失败的停止条件保持原样。若宿主不能可靠启动并追踪长期任务，启动前说明限制并停止，不启动一个无法收尾的孤儿任务。

## extract-vision

1. OCR 文本过滤是共享任务，不把子智能体隔离当作必需能力。可委派时使用有界委派；不可委派时由当前 agent 按同一字段/列表输出约束顺序处理 OCR 文本。
2. OCR 返回空或原图小字模糊时，先检查当前 agent 或可用委派目标能否读取原图；可用则直接视觉提取，不要求一定是“视觉子智能体”。若无原图视觉能力，明确报告无法可靠提取并停止，不能把 OCR 空结果当作“图片没有内容”。
3. `scripts/ocr_extract.py` 的退出码和依赖提示保持不变；不在本批修改 OCR 脚本、下载模型或代替用户安装依赖。

## close-node

1. 接手方必须保留共享 worktree；`ExitWorktree(action: "keep")` 只是提供该语义的一个宿主调用。先检查是否存在可靠的宿主“保留并离开/解除当前会话绑定”能力，并明确该操作不会移除 worktree。
2. 有能力时走该宿主的适配步骤；没有时报告节点、分支、worktree 路径与需要人工解除绑定的事实，停在第 4 步。不得用单次 shell `cd` 假装解除会话绑定，也不得继续到隐藏或 `stop-node`。绝不合并、删除接手方 worktree，或代替交出方验收。
3. 独立节点与交出方的既有合并、验收和关闭门禁不因本改动放宽；Canvas 环境检测仍是入口条件。

## 验收与证据

| 条目 | 必须可观察到的行为 | 不可接受的行为 |
|---|---|---|
| learn-video | 无 `AskUserQuestion` 的宿主仍能获得用户模式；skill 从非维护者路径找到脚本；缺 vdl 源码根目录时停下 | 猜选模式、猜固定项目目录、擅改下游配置、启动无法追踪的任务 |
| extract-vision | 无委派能力时可从 OCR 文本提取字段；OCR 空且无视觉能力时明确停止 | 把子智能体作为必经工具，或将 OCR 空当作无内容 |
| close-node | 无 `ExitWorktree` 时安全保留 worktree 并报告待人工解除绑定 | 用 `cd` 冒充离开、删除接手方 worktree、在仍绑定时隐藏/停止节点 |

先运行静态规则和本地可重复的路径/流程场景，再在至少一个可用的非 Claude 宿主做受限实测。真实宿主未覆盖的格子标“未验证”；文本通过和发布包可安装均不等于七平台端到端通过。修改 `SKILL.md` 时分别升 patch 版本、同步 `skills-index.json` 的 `contentVersion`/`contentHash`，检查安装包是否含所需脚本或适配文件；部署只能在明确要求集成后从 `staging` 进行。
