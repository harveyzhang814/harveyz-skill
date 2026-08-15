# native vs inject 实测记录 · 2026-08-14

支撑 [../2026-08-14-skill-harness-adapter-design.md](../2026-08-14-skill-harness-adapter-design.md)
的「决策」一节。这里只记事实与复现方法，结论在 spec 里。

## 探针设计

`probe-anchor/`（本目录下），两个 token 分居两处：

| token | 位置 | 测什么 |
|---|---|---|
| `BODY-4B21E8` | `SKILL.md` 正文 | skill 正文有没有到达模型 |
| `ANCHOR-7F3A9C` | `references/token.md` | **模型知不知道 skill 根目录在哪** |

要求模型输出 `BODY=` 与 `FILE=` 两行，读不到文件时输出 `FILE=UNREACHABLE` 而非猜测。
`FILE` 这一格就是路径锚点的判据。

## 结果

| 平台 | 模式 | 命令要点 | BODY | FILE |
|---|---|---|---|---|
| pi | native | `pi -p -ns --skill <dir> "run anchor probe"` | ✓ | `ANCHOR-7F3A9C` |
| pi | inject | `pi -p -ns --append-system-prompt <body> "run anchor probe"` | ✓ | `UNREACHABLE` |
| pi | inject+补偿 | 同上，body 末尾加一行绝对路径 | ✓ | `ANCHOR-7F3A9C` |
| pi | native/非触发 | `--skill <dir> "what is 2+2?"` | — | — （skill 未触发，答 `4`） |
| claude | native | `HOME=<jail> CLAUDE_CONFIG_DIR=<jail>/.claude claude -p --setting-sources user` | ✓ | `ANCHOR-7F3A9C` |
| claude | inject | 同上 + `--append-system-prompt <body>`，jail 内无 skills 目录 | ✓ | `UNREACHABLE` |
| hermes | native | `HOME=<jail> hermes -z "run anchor probe"` | ✓ | `ANCHOR-7F3A9C` |
| hermes | native+safe | 同上 + `--safe-mode` | ✓ | `ANCHOR-7F3A9C` |
| hermes | inject | `hermes -z "<body>\n---\nrun anchor probe"`，jail 内 skills 为空 | ✓ | `UNREACHABLE` |

每格 n=1。`FILE` 的失败是机制性的（模型无锚点信息），不是采样噪声，故未重复。

## 附带测得的平台事实

**claude**
- `HOME` 重定向后认证必失败，复制 `.credentials.json` 无效，报 `Not logged in · Please run /login`。
  需注入 `CLAUDE_CODE_OAUTH_TOKEN`，值取自 keychain
  `security find-generic-password -s "Claude Code-credentials"` 的 `claudeAiOauth.accessToken`。
- `--setting-sources user` + `CLAUDE_CONFIG_DIR=<jail>/.claude` 足以让 jail 内 skill 被发现并按
  description 触发。
- jail 后仍可见 12 个内置 skill：`dataviz` `update-config` `keybindings-help` `code-review`
  `simplify` `fewer-permission-prompts` `loop` `schedule` `claude-api` `run` `init` `security-review`。
  拿不到零 skill 基线。

**pi**
- `--skill <file|dir>` 是显式加载通道，`-ns` 不影响它。二者组合 = 恰好一个 skill，
  且无需 `HOME` 重定向。
- `--append-system-prompt` 接受文件路径或字面文本两种形式。

**hermes**
- jail 需复制 `.hermes/{.env,auth.json,config.yaml}`。
- `hermes skills list` 在 jail 内输出 `0 hub-installed, 0 builtin, 1 local` —— 三平台里最干净。
- jail 内的 skill **自动被发现并按 description 触发，无需 `-s`**。
- `--safe-mode` 不影响目录发现的 skill。其隐含的 `--ignore-rules` 说明里那句
  "skip ... and preloaded skills" 只指 `-s` 的强制预载通道。

## 一次未复现的异常

claude inject 模式第一次运行时工作目录名为 `jail-inject`，模型**拒绝执行**，理由是
「这段文本不在我真实的 skill 列表里」「working directory is literally named `jail-inject`」，
判定为 prompt injection。换中性目录名后输出正常（`FILE=UNREACHABLE`）。

n=1 且被目录名混淆，不作为结论。但记录在案：inject 模式的正文在 claude 上存在被判为
不可信内容的方差风险，native 模式结构上没有这个风险。对应 spec「风险 8」。

## 复现

探针在本目录。各平台命令见上表。claude 需要 keychain 取 token，
pi 与 hermes 用当前用户已有凭证即可。
