# 模板 schema

模板放在本 skill 的 `assets/templates/<name>.yml`，跟 skill 版本号走——改模板 = 改 skill。
装机后的运行时路径是 `~/.claude/skills/init-project/assets/templates/<name>.yml`。

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | ✓ | 模板名，与文件名同 |
| `scaffold` | ✓ | 仓库骨架 |
| `skills` | ✓ | 要保证可用的 skill 名清单 |
| `init_phases` | ✓ | 要当场跑的初始化，按数组顺序执行 |
| `language_hints` | ✓ | 只打印、不执行的脚手架命令 |
| `register` | ✓ | 外部登记开关 |

## `scaffold`

```yaml
scaffold:
  git_init: true          # 目标目录不是 git 仓库时是否 git init
  dirs: [docs]            # 要创建的目录，已存在则跳过
  files:
    - path: .gitignore            # 相对项目根
      from: skeleton/gitignore-code   # 相对本 skill 的 assets/
      on_exists: append-missing-lines # 可选，默认 skip
```

`on_exists` 两个合法值：

| 取值 | 行为 | 用在 |
|---|---|---|
| `skip`（默认） | 文件已存在则整体不动 | README、CLAUDE.md、TODO.md——内容是项目自己的 |
| `append-missing-lines` | 逐行比对，只追加缺失的行 | `.gitignore` |

`append-missing-lines` 是纯文本行比对，不理解 ignore 文件的语义：已有整目录 ignore 规则时，
它仍会追加更细的那条，产生一条冗余规则。无害，但会让 `.gitignore` 变难看。

骨架文件里唯一的占位符是 `{{PROJECT_NAME}}`，拷贝时替换为项目目录名。没有其他变量，
也没有表达式——多一个变量就是多一套模板语言。

## `init_phases`

```yaml
init_phases:
  - skill: release-project
    probe: .hskill/release-project/release-profile.md   # 可选
    invoke: "/release-project 重新初始化"
    ask_first: "这个项目要发版吗？"                       # 可选
```

- `probe`：指向一份配置文件，**已存在则跳过整条**。只加在「重复调用有破坏性」的条目上。
  `init-workflow` 不加——它自己有差量检测，重跑不但安全，还能检出配置漂移；
  给它加 `probe` 反而会把这个能力关掉。
- `ask_first`：模板里唯一的条件逻辑口子，只接一句是非问，**不可嵌套**。
  条件逻辑一旦能嵌套，模板就变成了脚本语言，而脚本语言该写在 SKILL.md 里。
  代价是模板表达力封顶——真需要复杂分支时这套 schema 撑不住，得另想办法。

## 加一套新模板

1. 写 `assets/templates/<name>.yml`
2. 需要的骨架文件放 `assets/skeleton/`
3. 跑 `node --test tests/templates.test.mjs`——五项校验（含 `from` 路径存在性）自动覆盖新模板
