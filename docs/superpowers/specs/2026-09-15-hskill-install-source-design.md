# hskill 双来源安装与粘性更新设计

## 元信息

- **设计日期**：2026-09-15
- **状态**：待实施
- **涉及组件**：`bin/cli.js`（`update` / `version` 两个子命令）、`lib/version-check.js`（`compareVersions`）、新增 `lib/install-source.js`、新增 `tests/install-source.bats`、扩写 `tests/version-check.bats`
- **前置文档**：无
- **本文范围**：只解决 hskill **自身**的安装来源与更新路径。不涉及 skill 内容如何从仓库同步到 `~/.claude/skills/`（那是 `hskill install` / `hskill upgrade` 的职责，本文一行不改）

---

## 0. 主线

> 安装来源的事实由**全局安装目录里的痕迹**承载，不由任何独立持久化的状态承载。

`npm install -g` 是替换式的：它会先清空 `$(npm root -g)/<pkg>/` 再解包。因此任何写在该目录内的痕迹，都会被下一次安装——**包括绕过 hskill 的手工 `npm i -g harveyz-skill@latest`**——自动抹除。这使"记录的来源"与"实际的来源"不可能分叉。

可证伪：只要出现任何一处把来源信息写到全局安装目录**之外**（`~/.hskill/`、`~/.config/`、环境变量、用户级配置文件），主线即被推翻——那样的状态能在用户绕过 hskill 安装后继续存活，报出一个与现实不符的来源，而这正是本设计要消灭的故障。

---

## 1. 背景与要解决的故障

今天 `hskill update` 的实现是一行硬编码（`bin/cli.js`）：

```js
execSync('npm install -g harveyz-skill@latest', { stdio: 'inherit' })
```

没有任何来源判断。`lib/version-check.js` 同样只认 npm registry。整个更新机制只有一条轨道：npm 远端发布。

想要的能力是：**在真正发到 npm 之前，先把工作树的改动装成全局 hskill 用一阵子**。今天要做这件事只能手工 `npm install -g <路径>`，而一旦这么做，下次随手一句 `hskill update` 就会把它替换成 npm 上的版本——**没有任何提示，没有任何报错**，本地那份改动凭空消失，而且事后从 `hskill version` 的输出里看不出曾经发生过替换。

本文解决这一件事：让两种来源共存于同一个命令行工具，并让"当前处在哪条轨道"这件事随时可见、不会被静默切换。

---

## 2. 关键事实（实测，非推断）

以下四条决定了整个设计形态，均在 npm 11.19.0 / Node 25.6.1 上实测确认。任何实施偏离，请先复验这四条。

| # | 事实 | 后果 |
|---|---|---|
| 1 | `npm install -g <目录>` 建的是**软链**，指向该目录本身 | 这条路拿不到独立快照，也绕过 `files[]` 白名单，**本设计不采用** |
| 2 | `npm pack` 生成 tarball 后 `npm install -g <tgz>`，得到**真实拷贝**，且完整执行 `prepack` 与 `files[]` 白名单（实测未列入白名单的文件确实没进安装目录） | 本设计采用这条路 |
| 3 | tarball 安装在 `npm ls -g --json` 里**没有 `resolved` 字段**，与 registry 安装完全无法区分（只有软链安装才有 `resolved: "file:..."`） | **npm 不替我们记来源**，必须自己留痕迹 |
| 4 | 任何 `npm install -g` 都会**清空并重建**安装目录，先前写入的自定义文件一律消失 | 痕迹写在安装目录内即可自失效，见 §0 |

补充事实：semver build metadata（`0.33.0+local`）全程无损——`npm pack` 的 tarball 文件名带 `+`，安装后 `package.json` 原样保留，`npm ls -g` 原样显示。

---

## 3. 来源模型

只有两种来源，没有第三种：

| 来源 | 安装动作 | 判定依据 |
|---|---|---|
| `npm` | `npm install -g harveyz-skill@latest` | **默认**——安装目录里没有 `.hskill-source.json` |
| `local` | 在指定仓库 `npm pack` → `npm install -g <tgz>` | 安装目录里存在 `.hskill-source.json` |

`npm` 是缺省语义，不写任何东西来表达它。这不是省事：它保证了"文件丢失"与"来源是 npm"是同一个状态，不存在第三种"文件损坏，来源未知"的中间态需要处理。

### 3.1 痕迹一：`.hskill-source.json`

路径：`$(npm root -g)/harveyz-skill/.hskill-source.json`

```json
{
  "repo": "/Users/harveyzhang96/Projects/harveyz-skill",
  "branch": "staging",
  "commit": "8f63508",
  "dirty": false,
  "version": "0.33.0",
  "installedAt": "2026-09-15T21:10:00Z"
}
```

- `repo` 是**唯一不能编码进版本号的字段**（路径含 `/`，在 build metadata 里非法），也是粘性 update 唯一必需的字段。其余字段仅供 `hskill version` 展示与 `version --check` 比对。
- `version` 记录的是**追加 `+local` 之前**的原始版本号。
- git 三项（`branch` / `commit` / `dirty`）必须在 `npm pack` **之前**采集。理由见 §6.4。

### 3.2 痕迹二：版本号后缀 `+local`

安装完成后，就地改写 `$(npm root -g)/harveyz-skill/package.json` 的 `version` 字段，追加 `+local`：

```
0.33.0  ->  0.33.0+local
```

**为什么改安装目录而不是改工作树再打包**：后者需要"改 tracked 文件 → pack → 还原"三步，进程在中途被打断就会在用户仓库里留下一个被篡改的 `package.json`。改安装目录没有这个风险，且与 §0 的自失效性质一致——下次安装连同痕迹一起抹掉。

**后缀只标 `local`，不含分支与 commit。** 两个不同提交装出来的版本串因此完全相同。这是有意的取舍：版本串只承担"这是不是本地装的"这一个标识职责，**不承担任何新旧判断职责**。新旧判断全部交给 `.hskill-source.json` 里的 `commit`（见 §5.2）。附带好处是分支名里的 `/` 不必洗成 `-`（build metadata 只允许 `[0-9A-Za-z-]`），少一处字符转换。

---

## 4. 新模块 `lib/install-source.js`

四个导出函数，不含任何 I/O 之外的业务判断：

| 函数 | 职责 |
|---|---|
| `globalRoot()` | 返回 npm 全局 node_modules 路径。实现为 `execSync('npm root -g')`，结果在进程内缓存。**可被环境变量 `HSKILL_GLOBAL_ROOT` 覆盖**（供测试注入，沿用仓库已有的 `HSKILL_NPM_REGISTRY` 套路） |
| `readSource()` | 读 `.hskill-source.json`。文件不存在或 JSON 解析失败 → 返回 `null`（= npm 来源）。解析失败不抛错：那是一个必须被当作"来源未知，按缺省处理"的状况，抛错只会让 `hskill version` 这种只读命令崩掉 |
| `writeSource(info)` | 写 `.hskill-source.json` |
| `gitInfo(repo)` | 返回 `{ branch, commit, dirty }`。`git -C <repo> rev-parse --abbrev-ref HEAD` / `rev-parse --short HEAD` / `status --porcelain` 非空即 dirty |

**所有路径一律以 `globalRoot()` 为基准，不得使用 `path.join(__dirname, '..')`。** 后者在"从仓库直接跑 `node bin/cli.js update`"时会指向仓库本身，导致把用户的工作树误当成安装目录去改写 `package.json`。`update` 的作用对象永远是全局安装，与 CLI 自己跑在哪无关。

---

## 5. 命令面

不新增子命令。`update` 加两个互斥旗标：

```
hskill update                 更新，沿用当前来源（粘性）
hskill update --local <路径>   切到 / 刷新本地来源
hskill update --npm           切回 npm registry
```

### 5.1 `update` 的分支

```
读 readSource()
├─ null（npm 来源）        → npm install -g harveyz-skill@latest
└─ 非 null（local 来源）    → 从 info.repo 重新 pack + install
```

`--local` 的路径**必须显式给出**，没有默认值，不回退到当前目录。理由：回退到 cwd 意味着在别的仓库里手滑跑一次就会试图安装别的包。第一次切本地要打一次全路径，之后粘性接管，再不用打。

`--npm` 与 `--local` 同时出现 → 报错退出。

`update` 之后的既有动作（skill 重命名迁移 `migrateRenamedSkills`、`checkArchivedInstalls`、legacy 数据目录提示）在两条分支上**都要执行**，与今天一致。

### 5.2 `version` 与 `version --check`

`hskill version`——npm 来源时输出与今天逐字节一致（裸版本号一行）；local 来源时追加两行：

```
0.33.0+local

source: local  /Users/harveyzhang96/Projects/harveyz-skill
branch: staging  commit: 8f63508 (dirty)
```

`hskill version --check` 按来源分叉：

| 来源 | 比什么 | 判定 |
|---|---|---|
| npm | 本地版本 vs registry 的 `latest`（今天的逻辑，不动） | `compareVersions >= 0` 即最新 |
| local | `.hskill-source.json` 的 `commit` vs `info.repo` 的当前 HEAD | commit 相同**且**仓库当前不 dirty 才算最新 |

local 分支下**版本号不参与判断**——开发分支上版本号常常几十个提交不动，唯一会动的是 commit。仓库 dirty 时一律报"有未打包的改动"，即使 commit 相同：工作树里那些改动确实不在已安装的那份里。

---

## 6. 边界与失败处理

### 6.1 `info.repo` 路径已失效

仓库被移走或删除 → `update` **直接失败退出**，输出两条出路：

```
✗ 本地来源仓库不存在：/path/that/is/gone
  改用 npm：   hskill update --npm
  指向新路径： hskill update --local <新路径>
```

**不静默回退到 npm。** 静默替换正是本设计要消灭的故障（§1），在失败路径上重新引入它是自毁。

### 6.2 `npm pack` 失败

就地中止，非零退出。此时全局安装原封未动——`npm install -g` 还没被调用，不存在中间态，**因此不需要任何回滚逻辑**。

### 6.3 跨来源切换的可见性

`--npm` 或 `--local` 触发跨来源切换时，打印完整迁移行：

```
0.33.0+local (staging@8f63508) → 0.32.0 (npm)
```

**不加交互确认**，即使是版本降级。跨来源切换只可能由显式旗标触发，旗标本身就是意图；再加一道确认是对已表达的意图重复发问。

### 6.4 `prepack` 会改写 tracked 的 `.npmignore`

本仓库的 `prepack` 钩子是 `node scripts/generate-npmignore.js`，它写入 `.npmignore`，而该文件**是被 git 跟踪的**（`.gitignore` 第 15 行 `!.npmignore` 显式反排除）。所以 `npm pack` 可能弄脏用户的工作树。两项处理：

1. **git 信息在 pack 之前采集**。否则 prepack 写完 `.npmignore`，`dirty` 会被污染成恒为真。
2. pack 之后检查 `.npmignore` 是否变动，变了就提示一句。**不自动还原**——那可能抹掉一次合理的重新生成（比如用户刚改过 `skills-index.json`）。

### 6.5 `compareVersions` 必须先剥 build metadata

`lib/version-check.js` 现在是：

```js
const pa = a.split('.').map(Number)
```

喂 `0.33.0+local` 得到 `[0, 33, NaN]`，`NaN - x` 恒为 `NaN`，`!== 0` 为真，比较结果无意义。修法是比较前先截断 `+` 及其后内容——按 semver 规范 build metadata 本就不参与优先级比较，截断是规范行为而非权宜。

**这不是可选项。** 不修的话，local 安装下连 npm 来源的 `version --check` 路径也会跟着坏（它拿本地版本串去比 registry）。

---

## 7. 测试

新增 `tests/install-source.bats`，扩写 `tests/version-check.bats`。沿用仓库既有的环境变量注入套路：`HSKILL_GLOBAL_ROOT` 把"全局安装目录"指到临时目录，PATH 上放 `npm` shim 拦住真实安装。

必须覆盖：

- `readSource()`：文件不存在 → `null`；JSON 损坏 → `null` 且不抛
- `update` 粘性分叉：有痕迹走 local、无痕迹走 npm（用 npm shim 记录实际收到的参数来断言）
- `--local` 缺路径参数 → 报错；`--npm` 与 `--local` 并用 → 报错
- `info.repo` 不存在 → 非零退出，且**没有**调用过 npm shim
- `compareVersions`：`0.33.0+local` vs `0.33.0`、`0.34.0`、`0.32.0` 三组
- `version --check` local 分支：commit 相同且干净 / commit 不同 / commit 相同但 dirty，三种
- `version` 输出：npm 来源时与今天逐字节一致（防止给 local 加的展示行泄漏到 npm 路径上）

**真实的 `npm install -g` 不进自动化测试**——它会改动运行测试的机器的全局环境。这条留一次人工验证，见 §8。

---

## 8. 人工验收清单

自动化测试拦不住 npm 的真实行为（§2 那四条事实都是实测得来的），所以实施完成后必须人工跑一遍：

1. `hskill update --local <仓库路径>` → `hskill version` 显示 `+local` 与正确的 branch/commit
2. 确认 `$(npm root -g)/harveyz-skill/` 里**没有**未列入 `files[]` 的文件（验证 §2 事实 2 在真实包上依然成立）
3. 再跑一次 `hskill update`（不带旗标）→ 仍走 local，不跳去 npm
4. 手工跑 `npm i -g harveyz-skill@latest` 绕过 hskill → `hskill version` 应正确报告已回到 npm 来源（验证 §0 的自失效性质）
5. `hskill update --npm` → 版本号恢复裸串，痕迹文件消失
6. 全程结束后 `git status` 检查工作树，除 `.npmignore` 外不应有任何改动

---

## 9. 明确不做

- **不做第三种来源**（软链 / `npm link`）。§2 事实 1 说明它绕过 `files[]`，会让未发布和 archived 的 skill 出现在列表里，与"预演真实发布"的目的相反。
- **不做从 git ref 打包**（如固定从 `staging` 取）。本地安装的用途就是预演工作树里那份改动，固定取集成分支会让这个用途消失。
- **不做自动来源推断**（比较两边版本号取新的）。开发分支版本号未必单调递增，推断会在错误的时刻把用户弹到另一条轨道上——这正是 §1 那个故障的变体。
- **不改 `hskill install` / `hskill upgrade`**。skill 内容如何落到 `~/.claude/skills/` 与本文无关。
