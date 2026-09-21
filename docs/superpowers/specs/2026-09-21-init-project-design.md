# init-project 新项目初始化 skill 设计

- 日期：2026-09-21
- 状态：设计已确认，待实施
- 新增 skill：`skills/coding/init-project`（`0.1.0`）
- 影响文件：`skills-index.json`、`tests/`（新增模板校验）
- 不影响任何现有 skill 的内容

## 主线

**新项目初始化是一个编排问题，不是一个生成问题。** 各 skill 已经各自内建了
「配置不存在就问用户并写下来」的分支，缺的只是一个知道「这类项目该有哪些 skill、
按什么顺序把它们叫起来」的编排器。所以 init-project 不写任何一份 skill 配置，
它只做四件事：建仓库骨架、解析并补齐 skill、按序触发能独立触发的初始化、
把触发不了的登记成待办。

这句话可证伪：如果实施过程中发现必须由 init-project 亲自写某个 `.hskill/<skill>/` 配置
文件才能让流程跑通，主线就是错的。

---

## 1. 定位与现状

### 1.1 这个 skill 在系统里的位置

harveyz-skill 目前有 50 个 skill，其中 24 个标记 `installScope: project`——它们只在
需要的项目里安装，并且多数依赖一份项目级配置才能工作。新开一个项目时，这些配置
一个都不存在。

没有 init-project 会发生什么：新项目开工后的头几天，会被零散的配置提问反复打断——
第一次用 `/handoff` 时问一次交接约定，第一次发版时问一遍 release profile，
第一次清分支时问一遍清理规则。每一次都发生在你正想干别的事的时候。

触发场景有两个，**第二个很可能才是主要用法**：

1. 从空目录（或刚 clone 的空仓库）起建一个新项目
2. 在一个已经管理了一段时间的仓库上**补缺**——它缺哪几个 skill、缺哪几份骨架文件、
   哪几个 init 相位还没跑过

整套流程为此按幂等设计（§4.2），并提供一个只读的诊断模式（见 §3 末尾的 `check` 模式）。

### 1.2 「需要初始化的东西」实际有几类

扫 `skills-index.json` 和各 SKILL.md 里出现的 `.hskill/` 路径，分四类：

| 类别 | 内容 | 现状 |
|---|---|---|
| git 规范 | `.hskill/init-workflow/workflow-config.yml` + 4 个 hooks | 已有 `init-workflow` 承担 |
| 各 skill 的项目级配置 | `handoff/config.md`、`release-project/release-profile.md`、`capture-vocab/vocab.md`、`clean-git/branch-cleanup.md`、`sync-design/manifest.json` 等 | 各 skill 首次运行时懒创建 |
| skill 安装 | 24 个 `installScope: project` 的 skill | `hskill` 能装，但「该装哪些」无人判断 |
| 项目登记与骨架 | `hub projects add`、README、CLAUDE.md、TODO.md、`docs/` | 无人负责 |

### 1.3 关键约束：只有两个 skill 有可独立触发的初始化相位

这八个 skill——handoff、capture-vocab、setup-debug、release-project、clean-git、
sync-design、capture-insight、manage-dir——全都内建了「配置不存在 → 问用户 → 写配置」
的分支。但其中只有两个能被单独叫起来跑初始化：

- `init-workflow`：整个 skill 就是初始化，本身就是入口
- `release-project`：显式 Init / Execute 两相位，说「重新初始化」即可单独跑 Init

其余六个的初始化是**干活时的副作用**。要让 handoff 生成 `config.md`，只能假装去写一份
交接文档——那是误用，不是调用。

**因此本设计把初始化分成两档**：能独立触发的当场跑完；不能的只安装，并在收尾清单里
登记成「首次使用时会问你 X」。代价是初始化不完整，部分配置仍要等到开工后才落地；
换来的是零修改——不动任何现有 skill。

「给这六个 skill 补一个统一 init 入口」是更彻底的解法，但那是给所有 skill 加新约束、
要改 6 个 skill 并全部发版的另一件事，不在本设计范围内。

---

## 2. 模板：schema 与 code 模板

模板是本设计的核心数据结构。**模板存放在 skill 仓库内**
（`assets/templates/*.yml`），跟 skill 版本号走，改模板 = 改 skill。
代价是每次调模板要走一遍分支/发版流程、重装才生效；好处是单一事实来源，
不会出现「装机副本的模板和仓库里的模板不一样」这种排查起来极费劲的分叉。

### 2.1 schema

五段，SKILL.md 只认这五段，不含任何 code 项目的具体知识：

```yaml
name: code
scaffold:                      # 1. 仓库骨架
  git_init: true
  dirs: [docs]
  files:                       # on_exists 默认 skip
    - {path: README.md,  from: skeleton/README.md}
    - {path: .gitignore, from: skeleton/gitignore-code, on_exists: append-missing-lines}
    - {path: CLAUDE.md,  from: skeleton/CLAUDE.md}
    - {path: TODO.md,    from: skeleton/TODO.md}
skills:                        # 2. 要保证可用的 skill（不预设装哪一级）
  [init-workflow, clean-git, release-project, capture-todo,
   capture-insight, capture-vocab, handoff, question-me, rephrase]
init_phases:                   # 3. 当场跑的初始化，按序
  - skill: init-workflow          # 无 probe：重复调用安全，它自己有差量检测
    invoke: "/init-workflow"
  - skill: release-project
    probe: .hskill/release-project/release-profile.md
    invoke: "/release-project 重新初始化"
    ask_first: "这个项目要发版吗？"
language_hints:                # 4. 只打印，不执行
  node: "npm init -y"
  python: "uv init"
  rust: "cargo init"
register:                      # 5. 登记
  hub: true
```

### 2.2 三个字段的取舍

**`ask_first` 是模板里唯一的条件逻辑口子**，只接一句是非问，不可嵌套。这是有意识的收窄：
条件逻辑一旦能嵌套，模板就变成了脚本语言，而脚本语言应该写在 SKILL.md 里而不是 YAML 里。
代价是模板表达力封顶——将来真需要复杂分支时，那套模板撑不住，得另想办法。

**`probe` 解决重跑安全**（见 §4.2），指向一份配置文件；文件已存在则整条 init_phase 跳过。
**它是可选字段，只加在「重复调用有破坏性」的条目上。** `init-workflow` 不加——它自己有
差量检测，重跑不但安全，还能检出配置漂移；给它加 probe 反而会把这个能力关掉。

**`on_exists` 解决老仓库上的幂等粒度**，两个取值：

| 取值 | 行为 | 用在 |
|---|---|---|
| `skip`（默认） | 文件已存在则整体不动 | README、CLAUDE.md、TODO.md——内容是项目自己的，不能被模板插手 |
| `append-missing-lines` | 文件已存在则逐行比对，只追加缺失的行 | `.gitignore` |

不加这个字段的话，老仓库上 `.gitignore` 一定已存在、于是整体跳过，
`.hskill/*/state.json` 那条永远补不上——而那恰好是这个 skill 该带来的东西。
代价：`append-missing-lines` 是纯文本行比对，不理解 ignore 文件的语义，
已有整目录 ignore 规则时它仍会追加更细的那条，产生一条冗余规则（无害，但难看）。

### 2.3 两个骨架层面的判断

**不预建 `docs/commute/`。** handoff 的交接文档落点由它自己在 `.hskill/handoff/config.md` 里
定，init-project 预先建目录等于替它选了路径，与「配置归各 skill 自己写」直接冲突。
代价：新项目第一次跑 `/handoff` 时会多一轮问答。

**`.gitignore` 不整体排除 `.hskill/`，只排除运行时状态文件。** `.hskill/` 下混了两类东西：
配置（`workflow-config.yml`、`config.md`、`vocab.md`——该进版本库，团队共享）和运行时状态
（如 `sync-agent/state.json`——不该进）。一刀切 ignore 会让 `init-workflow` 生成的配置
进不了库，下一个 clone 的人拿不到。

---

## 3. 执行流程

**全程 cwd 锁在新项目根。** 这是硬约束不是洁癖：`hskill` 的 project 档是从
`process.cwd()` 推出来的，cwd 错了它会静默去查/写别的目录，不报错。
所以每条 hskill 调用都写成 `cd <PROJECT> && hskill ...`。

### Step 0 — 落点与模板

确认目标目录绝对路径（不存在则创建），选模板。本期只有 `code`，仍然要显式确认，
为将来多模板留出问法。

### Step 1 — 骨架落盘

按 `scaffold` 建目录、拷文件。**已存在的文件按 `on_exists` 处理，默认整体不覆盖，
只记「已跳过」**——这条让整个 skill 可以在半成品仓库、乃至成熟仓库上重跑。
`append-missing-lines` 的条目改为逐行补齐，并记录实际追加了哪几行。

**能力上限，收尾清单里要明说**：这一步只认同名文件。老仓库里若已有一套自己的
钩子目录，或 `CONTRIBUTING.md` 已经承担了 CLAUDE.md 的部分职责，
init-project 照样会新建一个 CLAUDE.md——它看不出「同一件事换了个名字」。

### Step 2 — 解析已装，差量安装

```bash
cd <PROJECT> && hskill status --json
```

对模板 `skills:` 里每个名字查 `user.claude.status`：

| 全局状态 | 动作 |
|---|---|
| `up-to-date` | 跳过，不装到项目 |
| `update`（全局装了旧版） | 也跳过，**也不升级** |
| `none`，且 `project.claude.status` 也是 `none` | 记入待装清单 |

待装的一次性装完：

```bash
cd <PROJECT> && hskill install --skill a --skill b --scope project --target claude
```

**「全局是旧版也不升级」是明确取舍**：升级全局 skill 会波及所有项目，不该由
「初始化某个新项目」这个动作顺手触发。代价是新项目可能跑在旧版 skill 上，
所以收尾清单里补一句 `hskill outdated` 提示，把决定权留给用户。

### Step 3 — init 相位编排

按 `init_phases` 顺序走。每条依次判断：

1. `probe` 指向的文件已存在 → 跳过整条
2. 有 `ask_first` → 先问，答否则跳过
3. 调用 `invoke`

**这里有个实际会出的故障，SKILL.md 必须写死防住**：init 相位是在当前会话里调用
另一个 skill，`/init-workflow` 会接管对话跑完它自己的多步流程。控制权交出去之后，
很容易就地结束，Step 4、5 再没人执行。防护：每条 init_phase 后面写一句显式的
「回到 init-project 的 Step N」，并且整个流程用 todo 逐条钉住。

单条 init 失败（例如用户拒绝 `git init`，init-workflow 优雅停止）**不中断主流程**，
记为「跳过」进收尾清单。

### Step 4 — 登记

```bash
hub projects add <name> --path <abs> --desc <一句话>
```

`hub` 不在 PATH → 跳过，把命令打进收尾清单。

### Step 5 — 收尾清单

五段：

1. 已建的文件 / 已跳过的（因已存在）
2. 已装到项目级的 skill / 已跳过的（因全局已有）
3. 已跑完的 init 相位 / 跳过的及原因
4. **待办**：`language_hints` 里的语言脚手架命令、那六个「首次使用时会问你配置」的
   skill、需要时的 `hskill outdated`、以及建远程仓库的命令
5. **请自行核对**：本次新建的文件清单，提示用户确认有没有和仓库既有约定重复
   （只在确实新建了文件时输出）

### 模式分支 — `check`：只诊断不动手

`/init-project check` 走同一套模板，但**不写任何文件、不装任何 skill、不调任何 init 相位**。
它跑三件只读的事，然后输出一张「缺什么」的表：

| 检查项 | 数据来源 |
|---|---|
| 骨架缺哪些文件、`.gitignore` 缺哪几行 | 文件系统 |
| 模板声明的 skill 里哪些两级都没装 | `hskill status --json` |
| 哪些 init 相位还没跑过 | 各条的 `probe` 路径是否存在 |

**这是为老仓库加的。** 在一个跑了半年的仓库上，你多半想先看见差距再决定动不动，
而上面三项本来就全是只读操作——执行模式里它们各自是 Step 1/2/3 的前半段，
`check` 只是跑到那里停住。

代价：SKILL.md 多一条路由分支，而且两条路径的判断逻辑必须共用同一段描述，
否则 `check` 报「缺 X」而执行模式没装 X，这种分叉比没有 check 更糟。
实现上的约束：把三项检查写成 SKILL.md 里一节独立的「探测」，两条路径都引用它，
不各写一遍。

`check` 不问任何问题，包括 `ask_first`——它只报告「这条相位有 `ask_first`，
执行时会先问你」。

---

## 4. 边界与失败态

### 4.1 明确不做的五件事

写进 SKILL.md，因为「不做什么」是这个 skill 最容易被越界的地方：

1. **不生成语言脚手架**，只打印命令。委托给 `npm init` / `uv init` / `cargo init` 也不行——
   那要求本机装了对应工具链，而这个 skill 的价值不该押在那上面。代价：不是真正的
   「一条命令建好项目」。
2. **不写任何 `.hskill/<skill>/` 配置**——归各 skill 自己。
3. **不升级已装的 skill**。
4. **不碰远程仓库**（`git remote add` / `gh repo create`）。建远程是对外动作，
   和本地初始化的耦合只有一条命令，绑进来会让一个幂等的本地流程变得不可重跑。
5. **不装 shell tool**（hub、browser-fetch 等）。`hskill install --tool` 是全局动作，
   装一次全机器生效，不属于「初始化某个项目」。

### 4.2 幂等

Step 1 的文件不覆盖、Step 2 的已装跳过，两处天然可重跑。

**Step 3 原本不可重跑，是本设计发现的一个真 bug 源**：`init-workflow` 自己有差量检测，
重跑安全；但 `release-project` 那条 `invoke` 写的是 `/release-project 重新初始化`，
而「重新初始化」在它的 SKILL.md 里是**显式覆盖旧 profile** 的指令。第二次跑
init-project 会把已调好的 release-profile 冲掉。`probe` 字段（§2.2）就是为此而加。

### 4.3 失败态

| 情况 | 处理 |
|---|---|
| 目标目录已是 git 仓库 | `git_init` 跳过，其余照常 |
| `hskill` 不在 PATH | Step 2、3 整体降级为「打印待办」（skill 装不上，init 相位也调不起来），Step 1/4/5 照常走完 |
| 模板 YAML 解析失败或字段缺失 | 硬停，指出缺哪个字段 |

---

## 5. 落盘与元数据

```
skills/coding/init-project/
  SKILL.md                       name: init-project
                                 bundle: coding
                                 installScope: global
                                 user_invocable: true
                                 version: "0.1.0"
  assets/templates/code.yml
  assets/skeleton/README.md
  assets/skeleton/gitignore-code
  assets/skeleton/CLAUDE.md
  assets/skeleton/TODO.md
  references/template-schema.md  # schema 详解，渐进式披露
```

**`installScope: global` 是硬的**：这个 skill 要在一个还不存在的项目里被调起来，
不可能事先装在那个项目里。对比 `mint/init-skill` 是 `project`——那是因为它只在
harveyz-skill 仓库内使用，情况正相反。

命名符合仓库的 verb-noun 规范，且与 `init-skill` / `init-workflow` / `init-goal` 同族。

`skills-index.json` 需新增一条，`bundle: coding`。

---

## 6. 测试

接 `npm test` 现有的 SKILL.md 格式校验，新增四条模板校验：

1. `assets/templates/*.yml` 五段齐全
2. `init_phases[].skill` 必须出现在同模板的 `skills` 清单里
3. **`skills` 清单里每个名字必须能在 `skills-index.json` 里查到**
4. `scaffold.files[].on_exists` 若出现，取值必须是 `skip` 或 `append-missing-lines`

第三条最值钱：skill 被归档或改名时它会立刻失败，否则模板会静默引用一个不存在的 skill，
而这种失败要到某人初始化新项目时才暴露。

---

## 7. 把握度

| 档 | 内容 |
|---|---|
| **读到的** | 八个 skill 的懒初始化分支；`init-workflow` / `release-project` 的初始化入口；`hskill status --json` 的字段结构与 cwd 依赖；`hskill install --bundle/--skill --scope project` 的存在；`hub projects add` 签名；`release-project` 的「重新初始化」= 覆盖 profile |
| **推出来的** | 「init 相位调用其他 skill 后控制权不返回、Step 4/5 被跳过」——从 skill 互调机制推的，未实测。防护成本只有几行 SKILL.md，先加上 |
| **没查的** | 其余 23 个 `installScope: project` 的 skill（setup-debug、migrate-spec、scout-brand 等）各自的项目级配置需求——本期 code 模板只收录了 capture-vocab 一个 project 档 skill。不影响本设计，但将来扩模板时要逐个核 |

---

## 源码锚点

- `lib/bundles.js:136-163` — `checkInstalled`，project 档由 `process.cwd()` 推出
- `bin/cli.js:455-530` — `hskill status --json` 的输出构造
- `bin/cli.js:44-49` — install 的 `--bundle` / `--skill` / `--scope` 接口
- `skills/coding/init-workflow/SKILL.md:1-40` — 初始化入口与配置查找顺序
- `skills/meta/release-project/SKILL.md:12-39` — Init / Execute 两相位，及「重新初始化」的覆盖语义
- `skills/coding/handoff/SKILL.md:26-28` — 懒初始化分支的典型形态
- `docs/reference/hub-reference.md:38-55` — `hub projects add`
