---
scan: simplify-skill 拟定建议（7 条）
bundle: mint
repo: harveyz-skill
base: staging @ 9af95ab（只读扫描，未改任何文件）
date: 2026-10-22
---

# mint bundle 精简扫描

主线：mint 的体积和风险都集中在 publish-skill 与 init-skill。两者的共同病根是同一份规则（动词词表、frontmatter 规则、installScope 是否必填）在多个文件里各存一份，并且已经互相漂移。其余 skill 以局部重复和少量自相矛盾为主，可减比例不高。

把握度标注：〔读到〕= 直接读了原文或运行结果；〔推断〕= 由读到的内容推出来，未实测；〔未查〕= 没有去核实。

## 0. 跨 skill 的共性问题（先看这节）

1. **动词词表有四份，已漂移**〔读到〕
   - 权威：`docs/reference/skill-spec.md:92` 起，27 个动词（含 `judge`、`fork`、`clip`、`fetch`）。
   - `skills/mint/publish-skill/SKILL.md:79-84`：26 个，缺 `judge`。
   - `skills/mint/init-skill/references/skill-standard.md:27-32`：23 个，缺 `fetch`/`fork`/`clip`/`judge`。
   - `skills/mint/init-skill/references/skill-authoring-guide.md:14-19`：24 个，缺 `fetch`/`fork`/`clip`/`judge`，多一个权威表没有的 `survey`。
   - 后果〔推断〕：`agent-canvas/judge-release` 在 publish-skill 下会报 F9 警告，在 skill-spec 下却是合规；init-skill 会拒绝 `fork-*`、`clip-*` 这类已在用的名字。
2. **installScope 是否必填，两个 skill 说法相反**〔读到〕：`init-skill/references/skill-standard.md:18` 列为「系统机制，违反 = 注册失败」；`publish-skill/SKILL.md:135` 定为缺失只报警告；`contribute-skill/SKILL.md:186-189` 注册时根本不写这个字段。哪个是真规则，需要你定（未确认）。
3. **单段动词名**〔读到〕：`skill-spec.md:73-81` 和 `publish-skill` F7 允许单段名（如 `handoff`），`skill-standard.md:25` 规定「2 词」。init-skill 会按 2 词去造名字。
4. **改动成本：测试钉死了版本号和措辞**〔读到〕
   - `tests/skill-platform-authoring.test.mjs:70` 钉死 init-skill 1.3.0、contribute-skill 1.1.0、publish-skill 1.6.1，并校验 `contentHash`。
   - `tests/skill-portability.test.mjs:106` 钉死 runby-opencode 1.1.1。
   - 改这四个 skill 的 SKILL.md，除了要 bump version、更新 `skills-index.json` 的 `contentHash`/`contentVersion`，还要同步改测试里的版本号。
   - 两个测试文件还对正文措辞做了正则断言，各节「必须保留」里列了具体条目。
5. **`platform-adaptation.md` 两份完全相同**〔读到 diff〕：`init-skill/references/` 与 `contribute-skill/references/` 下的这两份是 `scripts/sync-skill-platform-standard.mjs` 从 `docs/reference/skill-platform-adaptation.md` 生成的，文件头写着 "Do not edit"。重复是刻意的（为了装机后自包含），**不能删、不能手改**。两个 SKILL.md 第 7 行的 `<!-- platform-standard-sha256: ... -->` 也由该脚本校验，脚本要求每个文件恰好有一处。

## 1. bundle 总览

| skill | 当前规模（行，含 references） | 优化潜力 | 预估可减比例 | 一句话主要问题 |
|---|---|---|---|---|
| publish-skill | 329（仅 SKILL.md） | 高 | 30–35% | F7/F8/installScope 规则各写 3–5 遍；动词词表副本已漂移；只在修复时才用到的 83 行修复引导常驻加载 |
| init-skill | 613（SKILL.md 181 + 三份 references 432） | 高 | 30–35%（其中约 25% 来自一份无人引用的文件） | `skill-authoring-guide.md` 156 行没有任何地方读取；`skill-standard.md` 词表漂移、强度等级/编号自相矛盾；Step 4 一段话塞了 5 个条件 |
| contribute-skill | 371（SKILL.md 313 + platform-adaptation 57 + .gitignore 1） | 中 | 15–20% | 边界表 6 行全部和正文重复；Step 8 把「问用户 y/n」写成 bash 伪代码；「目标已存在」的检查写在 cp 之后 |
| learn-skill | 230（SKILL.md 168 + evals 62） | 中 | 15% | 「解读不是评审」说了 5 遍；读 references/脚本、标注证据来源各写两遍；evals 断言与正文顺序相反 |
| dedup-skill | 224（SKILL.md 187 + auto-scan 37） | 中 | 10–15% | 调用的 `dir-manage` skill 不存在（实际叫 `manage-dir`）；0 匹配的处理前后矛盾 |
| archive-skill | 174 | 中 | 10–15% | 边界表有一行永远走不到；bundleMeta 描述的改法写了「均可」；确认摘要漏掉一项写操作 |
| fix-skill | 236（SKILL.md 153 + 2 份模板 83） | 低 | 5–10% | 调用方响应表与集成模板重复，其余都是输出契约 |
| runby-opencode | 107 | 低 | 5–10% | 定位段与引用块重复；输出路径表重复命令里的路径 |
| scout-philosophy | 139 | 低 | 5–10% | 产出文件清单与写入顺序说明重复；少量解释句 |
| simplify-skill | 22 | 无 | 0% | 7 条规则 + 1 段执行，没有可删内容 |

---

## 2. publish-skill（高）

文件：`skills/mint/publish-skill/SKILL.md`

### 问题按 7 条标准归类

- **标准 2：重复**
  - F7 命名规则写了五处：表格行 `:62`（一整段规则）、检测方法 `:70-89`、示例 `:91-93`、报告样例 `:175-178`、修复引导 `:225-231`。〔读到〕
  - F8 的通过/违规条件写了三处：`:63`、`:106-113` 的表格、`:299-301`。〔读到〕
  - installScope 三档菜单原样写了两遍（`:263-268`、`:284-290`），`:135` 又列了一遍合法值。〔读到〕
  - 动词词表 `:79-84` 是 `docs/reference/skill-spec.md` 的副本，`:238` 还要求两边同时维护；这份副本已经缺了 `judge`。〔读到〕
- **标准 4：渐进式披露**
  - Step 6 修复引导 `:213-295`（83 行，约占全文 25%）只在「发现问题 + 用户同意修复」时才用到，可以挪到 `references/fix-guide.md`，在 Step 6 开头写读取条件。〔读到行数；节省比例为推断〕
  - Step 5 的三种报告样例 `:147-211` 里，后两种（全部通过）各只有一行有效信息，可以压成一行说明。〔读到〕
  - Step 4a `:137-141` 只在检查范围包含 init/contribute 时才用，但测试对这段措辞有断言，**不能挪出 SKILL.md**。〔读到测试〕
- **标准 5：含糊**
  - `:68`「纯英文 skill 如从其他项目贡献的可跳过此项，需用户确认」：没写什么时候问、在哪一步问。〔读到〕
  - `:141` 把指令（「继续按 F8 与 Step 7 核对」）和免责说明（「不判定语义兼容」）混在一段。〔读到〕
- **标准 6：解释单列**：`:66`、`:68` 的「检测方法」夹着例外条款，可以拆成「规则」和「例外」两行。〔读到〕
- **标准 7：术语不一致**：标题和报告头叫 `skill-publish`（`:8`、`:148`），但 name 是 `publish-skill`。报告头属于输出契约，本次不建议改（未确认）。

### 代表性修改

**① installScope 菜单只定义一次**（标准 2）

修改前（`:261-268` 与 `:282-290` 各一份）：
```
选择推荐级别（installScope）：
  1. essential — 所有安装场景默认包含
  2. global    — 推荐安装，跨项目通用
  3. project   — 按项目需要安装
  4. （不设置，跳过）
```
修改后：在 Step 4 R4 行下面写一次：「`installScope` 合法值：`essential`（所有安装场景默认包含）／`global`（推荐安装，跨项目通用）／`project`（按项目需要安装）。」R1、R4 的修复各改成一句：「列出 R4 的三个合法值和『跳过』让用户选；跳过时不写该字段。」
理由：菜单内容逐字相同，交互行为不变。约省 12 行。

**② 动词词表改为读权威文件**（标准 2、7）

修改前（`:77-86`）：
```
   a. 先在规范词表中查找：
   ```
   fetch    extract  learn ...  dedup    fork
   ```
   命中 → 直接合规。
```
以及 `:238`「……并同步追加到本文件 Step 3 的词表副本」。
修改后：「a. 读取 `${REPO_ROOT}/docs/reference/skill-spec.md`『动词判定』下的词表；命中 → 直接合规。」`:238` 删掉「并同步追加到本文件 Step 3 的词表副本」。
理由：description 已经写明 "Rules defined in docs/reference/skill-spec.md"；副本已漂移。
代价与风险：这**会改变一个判定结果**，`judge` 从 F9 警告变成合规（未确认你是否接受）；publish-skill 的 installScope 是 `project`，Step 2 已经依赖 `REPO_ROOT`，所以运行时能读到这个文件〔推断〕。

**③ F7 表格行改为指向下文**（标准 2）

修改前（`:62`）：「skill 目录名建议为 `<动词>-<名词>`（2 段）或单独 `<动词>`（1 段）格式，连字符分隔，全小写；第一段建议语义上是动词，名词（若存在）不建议为工具/平台专有名；不符合时仅作警告，不阻止发布；`archived/` 下的 skill 跳过此检查」
修改后：「目录名为 `<动词>-<名词>` 或单段 `<动词>`，判定见下方『F7 命名规范检测方法』；警告不阻断；`archived/` 下跳过。」
理由：同样的规则在 `:70-89` 有完整版，表格只需要当索引。

### 必须保留、不能动

- 检查码 F1–F9、R1–R4，以及每一项是阻断还是警告。〔读到〕
- F8 hash 算法：把 `version:` 行替换为 `version: __HASH_PLACEHOLDER__`，算 SHA-256，取前 16 位。测试里用 node 实现了同一算法（`tests/skill-portability.test.mjs`、`tests/skill-platform-authoring.test.mjs`），两边必须算出一样的值。〔读到〕
- 字段名：`contentHash`、`contentVersion`、`installScope`、`bundle`、`bundleMeta`、`path`、`archived`。〔读到〕
- `node scripts/generate-npmignore.js` 的调用点；Step 7 只 `git add`、不 commit；不 push。〔读到〕
- Step 4a 里被测试断言的字串：`npm pack --dry-run --ignore-scripts --json`、两条 `mint/.../references/platform-adaptation.md` 路径、`contentVersion…contentHash`、`未实测…未验证`、`不…宣称…语义兼容`。〔读到 `tests/skill-platform-authoring.test.mjs:58-65`〕
- 报告头 `skill-publish 检查结果` 和各分组标题（输出契约）；各处 `(y/n)` 确认点。〔读到〕

### 未确认

- 词表改为读取 skill-spec.md 后，`judge` 的判定会变（见②）。
- hash 算法有个细微差异：sed 会替换**所有**以 `version:` 开头的行，测试里的 node 只替换第一处。只有正文里另有一行以 `version:` 开头时两边才会算出不同的值〔推断〕。
- `_fm`（`:117-123`）用 awk/grep/sed 解析 frontmatter，而 init-skill 标准 Φ12（`skill-standard.md:156`）写着「解析 YAML 禁 grep/sed/awk」。两条规则哪条优先，不明。
- 报告头 `skill-publish` 要不要改成 `publish-skill`：改了就是改输出。

---

## 3. init-skill（高）

文件：`skills/mint/init-skill/` 下的 `SKILL.md`、`references/skill-standard.md`、`references/skill-authoring-guide.md`、`references/platform-adaptation.md`

### 问题按 7 条标准归类

- **标准 2：重复与无人引用的文件**
  - `references/skill-authoring-guide.md`（156 行）没有被 SKILL.md 或 skill-standard.md 引用。Step 2a（`SKILL.md:67`）只读 skill-standard 和 platform-adaptation。全仓 grep 只在旧计划 `docs/superpowers/plans/2026-06-16-init-skill.md` 里出现过。它的内容（命名、frontmatter、边界表、符号、hash）是 skill-standard 的旧版子集，词表也漂移了。〔读到〕
  - 「参考标准」一节 `SKILL.md:29-31` 和 Step 2a `:67` 说的是同一件事。〔读到〕
  - `skill-standard.md:210-219`「应用流程」与 `SKILL.md:89-99`（2c/2d）重复。〔读到〕
  - Step 4 `:140` 里列过的前置检查，`:155` 又写了一遍。〔读到〕
- **标准 3：可用术语压缩**：Step 0 澄清策略 `:46-49` 写的就是标准里的 Φ4/Φ14，可以压成一句「一次一问；上下文能推断的不问；问到无歧义为止」。注意 Step 0 在 Step 2a 加载标准之前执行，所以不能只写「见 Φ14」，要保留这句关键词。〔读到顺序；做法为推断〕
- **标准 5：含糊或矛盾**
  - `SKILL.md:140` 一段话里塞了「预览已确认 / 工作区干净 / staging 可解析 / 目标路径与分支不存在 / 原生 worktree 的使用条件 / 回退 / 停止」，应拆成条件清单。〔读到〕
  - `skill-standard.md:5` 只定义了 `[强]`、`[中]` 两档，`:188` Φ16 却标 `[弱]`。〔读到〕
  - 编号不连续：description 和 `:89` 说「16 条哲学」，`skill-standard.md:23` 有一条「Φ18」，没有 Φ17。〔读到〕
  - `skill-standard.md:18`「installScope 必填」与 publish-skill 矛盾（见 §0.2）；`:25`「2 词」与 skill-spec 矛盾（见 §0.3）。〔读到〕
- **标准 7：路径与约定漂移**：Step 4 的 worktree 路径是 `.worktrees/feature-init-<name>`（`:145`），项目 CLAUDE.md 规定新建 worktree 一律用 `.claude/worktrees/<分支名把 / 换成 +>`。这是行为层面的差异，不在精简范围内，只标出来；而且测试钉死了 `check-ignore -q .worktrees/`。〔读到〕

### 代表性修改

**① 删除 `references/skill-authoring-guide.md`**（标准 2）

修改前：156 行文件随包安装，运行时不被读取。
修改后：删除该文件。
理由：流程里没有任何一步读它，删掉不改变行为〔推断，依据 grep〕。init-skill 规模减少约 25%（156/613 行），整个 bundle 减少约 6%（156/2,445 行）。它仍是一个可能被误读的旧规范源（多一个 `survey`、缺 `fork/clip/fetch/judge`）。
代价：按 CLAUDE.md「不删除既有死代码，除非被要求」，这条需要你明确批准。

**② Step 4 拆成条件清单**（标准 5）

修改前（`:140`）：一整段，从「先确认 Step 3 的完整预览已获用户明确同意」写到「回退也不可用时停止，不在当前 checkout 写入」。
修改后：
```
前置（只读，在 REPO_ROOT）：任一不满足即停止：
- Step 3 预览已获用户明确同意
- 脏工作区停止（`status --porcelain` 为空）
- `staging` 可解析为提交
- 目标路径已存在停止，提示改为更新已有 skill；目标分支已存在同样停止
- `.worktrees/` 被 git 忽略（`check-ignore` 成功）
宿主原生 worktree 入口只有在能指定 `staging` 基线、独立分支和目标路径时才可使用；不能指定或绑定基线则回退到下列 Git 命令；回退也不可用时停止，不在当前 checkout 写入。
```
然后删掉 `:155` 里重复的「`status` 必须为空、`branch --list` 必须为空，`check-ignore` 必须成功；任一条件不满足即停止」，只保留「创建后重新确认分支名和目标目录不存在；创建或配置失败时保留现场并报告」。
理由：判定条件没变，只是从段落改成清单，并删掉第二遍。测试断言的「脏工作区…停止」「目标路径…已存在…停止」「不能…指定/绑定…基线…回退」都还在。

**③ 合并「参考标准」与 Step 2a**（标准 2）

修改前：`:29-31` 一节 + `:67` 又写一遍，内容同为「从安装目录读两份标准、不依赖源仓库 docs/」。
修改后：删掉 `:27-31` 这一节，把「两者随本 skill 安装，不依赖源仓库的 `docs/` 路径」并入 2a 的第一句。
理由：两处都描述同一个读取动作；测试要求的 `references/skill-standard.md`、`references/platform-adaptation.md` 字串仍在 2a 里。

### 必须保留、不能动

- `SKILL.md:7` 的 sha256 标记（sync 脚本要求恰好一处）；`references/platform-adaptation.md` 整个文件（生成物）。〔读到〕
- 测试断言的字串（`tests/skill-platform-authoring.test.mjs:11-44`）：
  - 2b 表里的 `目标宿主`、`有意限定`、`核心能力`、`路径来源`、`回退`、`验证状态`，以及 `通过／缺口／不适用`。
  - `platforms/SKILL.<host>.md`，以及「不…创建…空…适配器」这句。
  - `worktree add` 必须出现在「写入新 skill」之前；`git -C "$REPO_ROOT" worktree add …staging`、`core.hooksPath`、`merge.ff`、`check-ignore -q .worktrees/`。
  - 正文**不得**出现 `用 Read 工具`／`用 Write 工具`／`由 Claude 根据内容推断`；也不得出现 `git checkout -b feature/init`。
  - skill-standard.md 里必须有 `references/<dim>/`、`platforms/SKILL.<host>.md`、`references/platform-adaptation.md`。
- 两个用户确认点（Step 2 末、Step 3 末），以及交棒提示「下一步：运行 publish-skill…」。〔读到〕
- 分支名 `feature/init-<name>`、commit message `feat(skill): scaffold <name>`。〔读到〕

### 未确认

- 词表的修法：`SKILL.md:31` 明确要求标准「随本 skill 安装，不依赖源仓库的 docs/」，所以不能简单改成读 `docs/reference/skill-spec.md`。可选的两条路：(a) 照 platform-adaptation 的做法，用 sync 脚本从 skill-spec 生成，代价是要扩展脚本和测试；(b) 手工同步一次，代价是以后还会漂移。
- installScope 必填与否、单段名是否允许：要先定规则，再决定改 skill-standard 还是改 publish-skill。
- Φ16 的 `[弱]` 是笔误还是有意的第三档；Φ18 的编号是否要改成 Φ17。
- worktree 路径习惯是否要跟进 CLAUDE.md（这是行为变更，不属于精简）。
- `skill-authoring-guide.md` 是否被仓库外的东西引用〔未查：只 grep 了本仓库〕。

---

## 4. contribute-skill（中）

文件：`skills/mint/contribute-skill/SKILL.md`

### 问题按 7 条标准归类

- **标准 2：重复**：边界情况汇总 `:296-305` 的 6 行，正文里都已写过：目标已存在 `:205-212`、脚本失败 `:203`、.config 失效 `:59`、非 Git 源 `:32`/`:229`、无差异 `:236`。〔读到〕
- **标准 5：含糊**
  - Step 8 `:256-263` 用 `echo "…(y/n)"` 加注释表示「问用户」，执行者可能会把它当 shell 原样跑。〔读到；后果为推断〕
  - 「目标路径已存在」的处理写在 `cp -r` 命令**之后**（`:205`），没写清楚它要在复制之前检查。〔读到〕
  - Step 1a `:36-38` 三段长句，判定类别和后续动作交织在一起。〔读到〕
- **标准 6：解释单列**：`:201` 的引用块是解释，可以保留，但应和指令分开（现在已基本分开，可不动）。
- **标准 7：和仓库约定不一致**（行为或契约问题，只标出不改）
  - Step 9 `:286` 输出「下一步：git push origin feature/contribute-<name>，然后创建 PR → staging」，而 CLAUDE.md 规定用 `scripts/merge-to-staging.sh` 在本地合并、不推送。〔读到〕
  - Step 6b `:186-189` 注册时不写 installScope（见 §0.2）。〔读到〕
  - Step 6b 先把文件写进 harveyz-skill 当前所在的分支，Step 8 才 `checkout -b`；没有干净工作区的前置检查，基线也不是显式的 staging〔推断：未提交改动会被带到新分支，所以能跑通，但基线取决于当时停在哪个分支〕。

### 代表性修改

**① Step 8 的伪代码改成指令**（标准 5）

修改前（`:256-263`）：
```bash
if git show-ref --quiet refs/heads/feature/contribute-<name>; then
  echo "分支 feature/contribute-<name> 已存在，是否切换到该分支继续？(y/n)"
  # 若用户确认 → git checkout feature/contribute-<name>
  # 若用户拒绝 → 中止操作
else
  git checkout -b feature/contribute-<name>
fi
```
修改后：「先运行 `git show-ref --quiet refs/heads/feature/contribute-<name>`。分支已存在 → 问用户『是否切换到该分支继续？(y/n)』，y 则 `git checkout feature/contribute-<name>`，n 则中止；不存在 → `git checkout -b feature/contribute-<name>`。」
理由：分支逻辑和确认点不变，只是不再让执行者以为 shell 能等用户输入。

**② 删掉边界表，或删掉正文重复**（标准 2，二选一）

修改前：`:296-305` 的表格 + 正文各处的同义描述。
修改后（方案 A）：删掉整张表，正文保留。（方案 B）保留表，把正文 `:205-212` 改成「见边界情况：目标路径已存在」。
理由：同一规则有两处表述，以后改了一处就会漂移。
代价：init-skill 标准 Φ3（`skill-standard.md:70`）提倡「多分支 skill 在末尾放边界表」，方案 A 与这条家规冲突；方案 B 让读者在步骤中途跳转。这个选择需要你来定。

**③ 把「目标已存在」挪到 cp 之前**（标准 5）

修改前：`:205` 的「边界情况：目标路径已存在同名 skill」排在 `:175-179`「1. 复制 skill 目录」之后。
修改后：放到 Step 6b 第 0 项：「复制前检查 `<harveyzSkillPath>/skills/<bundle-category>/<name>/` 是否存在；存在则询问 覆盖／重命名／中止。」
理由：现在的写法下，执行者可能先复制、后检查。这只是把隐含的顺序写明，〔推断〕不改变设计意图。

### 必须保留、不能动

- `:7` 的 sha256 标记、`references/platform-adaptation.md`（生成物）。〔读到〕
- 测试断言（`tests/skill-platform-authoring.test.mjs:46-56`、`tests/skill-portability.test.mjs:11`）：
  - `references/platform-adaptation.md` 必须出现在 `### Step 5 — 确认摘要` 之前（这个标题本身也不能改）。
  - 正文必须有 `确认断点`、`有意限定`、`待验证风险`、`源目录`、`回退`、`source_skill_dir`、`~/.hskill/contribute-skill`。
  - 必须能匹配「diff…用户…确认」「同步回源…用户确认」。
  - 正文**不得**出现 `~/.claude/skills`、`.claude/skills`。
- 跨 skill 和外部接口：
  - 配置 `~/.hskill/contribute-skill/.config` 和其中的字段 `harveyzSkillPath`。
  - index 条目的形状、`node scripts/generate-npmignore.js`。
  - 分支名 `feature/contribute-<name>`，两条 commit message。
- Step 5 与 Step 7 是两个独立的确认点（`:220` 明说前者不能代替后者）。〔读到〕

### 未确认

- Step 9 的 push/PR 提示是否要改成 merge-to-staging.sh（这是改输出）。
- 注册时是否补写 installScope。
- 边界表的去留（见②）。

---

## 5. learn-skill（中）

文件：`skills/mint/learn-skill/SKILL.md`、`evals/evals.json`

### 问题按 7 条标准归类

- **标准 2：重复**
  - 「解读，不评审」写了 5 处：`:10`、`:12`、`:45`、`:129`、`:139`。〔读到〕
  - 读 references 和外部脚本、无法访问时怎么标注，在 `:39` 和 `:53` 各写一遍。〔读到〕
  - 证据来源的标注规则在 Step 3 `:119-121` 和 Step 5 `:139` 各写一遍。〔读到〕
- **标准 5：含糊**
  - `:35`「在当前 repo 及常见 skill 安装目录中搜索」：没说「常见」是哪些。contribute-skill 的写法是「当前 host 已知的用户级或项目级 skill 目录」，可以统一。〔读到〕
  - `:34` 示例路径 `skills/meta/analyze-skill/` 已不存在〔读到 `skills/meta/` 只有 clean-git、release-project〕。
- **标准 6：解释单列**：`:131` 是对摘要用途的解释。它确实影响摘要怎么写（要能用于跨 skill 比较），可以压成一句括注。〔读到〕
- **标准 7：evals 与正文冲突**（不影响运行）
  - `evals.json:7`、`:11-12` 断言「设计哲学是第一个维度」，而正文 Step 2/Step 5（`:45`、`:139`）规定按 1→4 输出，设计哲学排最后。〔读到〕
  - eval 里的路径 `skills/meta/contribute-skill` 已经过时。〔读到〕

### 代表性修改

**① Step 2 去掉重复的定位声明**（标准 2）

修改前（`:45`）：「……按顺序执行：先分析现象（流程、规范、边界），最后综合推断本质（设计哲学）。每个维度的目标是让读者理解，不是评判好坏。具体引用 skill 中的实际段落或步骤来说明，不要泛泛而谈。」
修改后：「按维度 1→4 顺序执行：先流程、规范、边界，最后综合出设计哲学。每个论点引用 skill 中的具体段落或步骤。」
理由：「不评判」已经由 `:12` 和 `:139` 管住了。

**② 合并 references/脚本的读取规则**（标准 2）

修改前：`:39`「若存在 `references/`……尝试完整读取这些脚本；无法访问的脚本记录路径和调用接口，留待分析时标注」＋ `:53`「流程中调用的 references 文件和外部脚本均属于分析范围……标注『不透明调用』……」。
修改后：`:39` 只保留读取动作：「读取目标 `SKILL.md`、`references/` 下每个文件、被调用的脚本；读不到的脚本记下路径和调用接口。」`:53` 保留「展开为该步骤的具体行为；读不到的在对应节点标注『不透明调用』并写明已知接口和预期行为」。
理由：读取在 Step 1 做，标注在维度 1 做，各写一次。

**③ 证据标注只在一处定义**（标准 2）

修改前：`:119-121`（找证据、标来源、找不到就删）＋ `:139`（「维度 4 中有证据支撑的结论，以括号标注来源，如『（来自维度 1）』或『（原文 Step N）』」）。
修改后：`:120` 写明格式「来源标注格式：『（来自维度 X）』或『（原文 Step N）』」；`:139` 删掉这句。
理由：自查和输出用的是同一套标注格式。

### 必须保留、不能动

- 共享配置 `$HOME/.hskill/config.json` 的 `skillDir` 字段：survey-skillrepo 也读它（`skills/research/survey-skillrepo/SKILL.md:28`），同一个文件里还有 clip-url 等用的 `knowledgeRoot`。〔读到〕
- 保存路径 `{skillDir}/{repo-name}/{skill-name}.md`：survey-skillrepo 依赖这个约定（`survey-skillrepo/SKILL.md:138`）。〔读到〕
- 报告 frontmatter 字段 `skill`、`repo`、`path`、`version`、`analyzed_at`、`summary`。〔读到〕
- 维度顺序 1→4、Mermaid 放在维度 1 节点分析之后、全中文规则、收尾问句「还有哪个部分想深入了解？」、遇到评估意图时的处理（`:12`）。〔读到〕

### 未确认

- evals 与正文哪个是现行意图：正文是 v2.0.1，eval 冻结于 2026-08-17，〔推断〕eval 落后于正文。
- 配置放在 `$HOME/.hskill/config.json`，不在 `~/.hskill/learn-skill/`，与 Φ5 和 memory 里的约定不符。但它是几个 skill 共用的文件，不能动。

---

## 6. dedup-skill（中）

文件：`skills/mint/dedup-skill/SKILL.md`、`references/auto-scan.md`

### 问题按 7 条标准归类

- **标准 7：跨 skill 接口名错误**：`:102`「调用 `dir-manage` skill」。仓库里没有这个 skill，实际是 `skills/writing/manage-dir`。〔读到〕
- **标准 5：前后矛盾**：0 匹配时，`:33` 写「询问是否重新输入」，`:178` 写「报错，列出所有可用 skill 名后退出」。〔读到〕
- **标准 2：重复**
  - 全库扫描的指引写了两处：`:43` 和 `:187`。〔读到〕
  - `:91`「附带步骤不作为重叠标记」与 `:77`「相似的触发词或元数据不算重叠」部分重叠。〔读到〕
- **标准 5：含糊**
  - `:23` 用 `require('./skills-index.json')`，依赖当前目录正好是仓库根；`auto-scan.md:12-16` 用的是 `REPO_ROOT`。〔读到〕
  - 边界表 `:175`「共享 references 不算重叠」：Step 1 `:49` 只读 SKILL.md 正文，从不读 references，所以这一行管不到任何情况〔推断〕。

### 代表性修改

**① 修正被调用的 skill 名**（标准 7）

修改前（`:102`）：「若找到，调用 `dir-manage` skill 处理目录路径」
修改后：「若找到，调用 `manage-dir` skill 处理目录路径」
理由：现在的名字找不到对应 skill，这条分支调用不到〔推断〕。改名会恢复原本设计的调用，属于修复，需要你确认。

**② 统一 0 匹配的处理**（标准 5）

修改前：`:33`「提示 skill 不存在，询问是否重新输入」与 `:178`「报错，列出所有可用 skill 名后退出」。
修改后（建议取并集）：两处都写「提示不存在，列出全部可用 skill 名，询问是否重新输入」。
理由：现在两种行为二选一是随机的；取哪种属于行为决定，需要你定。

**③ 匹配命令改用 REPO_ROOT**（标准 5）

修改前（`:23`）：`node -e "const idx=require('./skills-index.json'); …"`
修改后：沿用 `auto-scan.md:12-16` 的写法，先 `REPO_ROOT=$(git rev-parse --show-toplevel)`，再读 `${REPO_ROOT}/skills-index.json`。
理由：两个入口的路径来源一致，也不依赖 cwd。

### 必须保留、不能动

- 报告文件名 `dedup-<YYYYMMDD-HHMMSS>.md`、`dedup-full-<YYYYMMDD-HHMMSS>.md`；默认目录 `docs/skill-analysis/`；向上查找 `DIR_METHOD.md`、上限为仓库根。〔读到〕
- 报告模板的各级标题、无重叠时不生成文件、仅分析不改文件。〔读到〕
- `references/auto-scan.md` 的引用点（这已经是渐进式披露）。〔读到〕

### 未确认

- 0 匹配取哪种行为。
- `:175` 这一行该删，还是该让 Step 1 也去读 references（后者是行为变更）。

---

## 7. archive-skill（中）

文件：`skills/mint/archive-skill/SKILL.md`

### 问题按 7 条标准归类

- **标准 5／7：走不到的分支**：边界表 `:165`「skill 在磁盘但不在 index → 仅做文件移动，跳过 Step 5」。但 Step 1 `:16-33` 只在 index 里匹配，0 匹配直接退出，所以这一行永远到达不了。〔读到；可达性为推断〕
- **标准 5：含糊**：`:104`「将整个 `（<name>）` 删除，或保留空括号（均可）」，两种结果写进 `bundleMeta` 的内容不同。〔读到〕
- **标准 6／Φ1：确认摘要缺项**：Step 3 预览 `:67-76` 没有列出 Step 5 `:107` 会写 `archived.skills`。〔读到〕
- **标准 2：重复**：边界表前四行 `:161-164` 和 Step 2、Step 6 的提示逐条对应。〔读到〕
- **标准 7：与仓库约定不一致**（行为，只标出）：Step 8 `:137-138` 直接 `git checkout <ORIGINAL_BRANCH> && git merge --no-ff`。若原分支是 `staging`，就违反了 CLAUDE.md「不要手动 git checkout staging && git merge」的规定。〔读到〕

### 代表性修改

**① 删掉走不到的那一行**（标准 5）

修改前（`:165`）：`| skill 在磁盘但不在 index | 提示"仅做文件移动"，跳过 Step 5 |`
修改后：删除这一行；或者在 Step 1 加一条「index 0 匹配时再查 `skills/*/<name>/`」，让它可达（那就是行为变更）。
理由：现在这条规则写了却不生效，会让读者误以为有这条路径。

**② 空括号二选一**（标准 5）

修改前（`:104`）：「若括号内只剩该项：将整个 `（<name>）` 删除，或保留空括号（均可）」
修改后：「若括号内只剩该项：删除整个 `（<name>）`」（或者反过来选保留空括号，由你定）。
理由：同一操作两次运行可能写出不同的结果。

**③ 预览补上 archived 记录**（标准 6）

修改前（`:71-72`）：「从 skills-index.json 移除该条目 / 更新 bundleMeta.<bundle>…」
修改后：在这两行之后加一行「追加 `<name>` 到 `archived.skills`」。
理由：预览要列出全部写操作；执行内容没变。

### 必须保留、不能动

- `archived.skills`／`archived.tools` 的结构：`bin/cli.js:229-236` 的 `hskill update/install` 读它，`:109` 的解释说明了它为什么不能省，这句应保留。〔读到〕
- 分支名 `chore/archive-<name>`、commit message、`--no-ff`、`node scripts/generate-npmignore.js`、Step 3 的 y/n 确认、三项前置检查。〔读到〕
- `:91` 关于 check-similar-branch hook 警告的说明（影响执行者要不要停下来）。〔读到〕

### 未确认

- 边界表要不要整体去重（和 contribute-skill 是同一个取舍）。
- Step 8 在 staging 上的合并方式是否要改走 merge-to-staging.sh（行为变更）。

---

## 8. 潜力低／无的 skill

- **fix-skill（低）**：主要内容是输入字段、`FIX_RESULT`/`SESSION_PATH`/`ATTEMPTS` 输出契约和 HOTFIXES.md 条目格式；HOTFIXES.md 由 `skills/meta/sync-hotfix` 消费，都不能动。唯一可删的是 `SKILL.md:145-151` 调用方响应表，它与 `references/caller-integration-template.md:31-34` 重复，可改成一句指向模板。〔读到〕附带发现：仓库里唯一的调用方是已归档的 `skills/archived/extract-url`，目前没有活跃调用方〔读到 grep〕。
- **runby-opencode（低）**：`:12` 的引用块重复了 `:10` 的定位；`:101-107` 的输出路径表重复命令里的路径；标题 `opencode-runner` 与 name 不一致。可减约 10 行。测试钉死了 1.1.1 和四条措辞（`tests/skill-portability.test.mjs:90-96`），改了要同步改测试，收益很可能抵不上成本〔推断〕。
- **scout-philosophy（低）**：`:10-14` 的产出清单与 `:137` 的写入顺序说明重复；`:42`、`:122` 是解释句，可压缩。三个生态的固定路径 `:63-65` 属于平台标准里的「有意限定」（研究对象本身就在那里），应保留。未确认：产出目录 `knowledge/skill-philosophy/` 是相对哪个仓库的路径，原文没写。
- **simplify-skill（无）**：22 行，7 条规则 + 1 段执行流程，没有重复或空泛句。`.claude/skills/simplify-skill/SKILL.md` 与 `skills/mint/simplify-skill/SKILL.md` 内容完全相同〔读到 diff〕，是项目内的装机副本，不算冗余。

## 9. 未确认项汇总

1. 动词词表以 `docs/reference/skill-spec.md` 为准后，`judge` 等动词的判定会变（publish-skill）；init-skill 的词表是用脚本生成还是手工同步。
2. installScope 是必填（skill-standard）还是警告（publish-skill）；contribute-skill 注册时是否补写。
3. 单段动词名是否允许（skill-standard 说 2 词，skill-spec 允许单段）。
4. 是否删除无人引用的 `init-skill/references/skill-authoring-guide.md`；仓库外是否有引用〔未查〕。
5. Φ16 的 `[弱]` 和 Φ18 的编号。
6. publish-skill 的 `_fm` 用 awk/grep/sed 解析 frontmatter，与 Φ12 冲突，哪条优先。
7. publish-skill 的 sed 与测试的 node 在多行 `version:` 时算出的 hash 不同（边缘情况）。
8. dedup-skill 0 匹配取哪种行为；`dir-manage`→`manage-dir` 的改名。
9. archive-skill 的空括号规则；走不到的边界行是删掉还是补上可达路径。
10. 边界表与正文重复时保留哪一处（contribute-skill、archive-skill、dedup-skill 都有这个取舍，和 Φ3 家规有关）。
11. learn-skill 的 evals 与正文维度顺序矛盾，以哪个为准。
12. 行为层面的不一致，不在精简范围内，只记录：init-skill worktree 路径习惯、contribute-skill Step 9 的 push/PR 提示与分支基线、archive-skill 在 staging 上直接 merge。
