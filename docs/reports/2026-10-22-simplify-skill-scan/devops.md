# devops bundle 精简扫描（simplify-skill「拟定建议」7 条）

扫描日期：2026-10-22。源：`skills/meta/`（staging 工作树）。只做到拟定建议，未改任何文件。

主线：这 4 个 skill 里，可删的内容主要是重复和通用命令示范，属于第 2 条；更要紧的是每个 skill 都有 1–3 处前后矛盾或字段没写清，属于第 5、7 条。这些地方即使不追求减行数也该改。

把握度标记：【读到】= 直接读到原文或代码；【推出】= 根据读到的内容推断；【未查】= 没有核实。

---

## 1. bundle 总览

| skill | 当前规模（含 references） | 优化潜力 | 预估可减比例 | 一句话主要问题 |
|---|---|---|---|---|
| sync-agent | 186 行（仅 SKILL.md） | 高 | 约 35–40% | 8 段 curl 重复同一请求头；`.stignore` 规则写了两遍且命令不同；暂停操作和错误处理各有一处自相矛盾；`config.json` 的字段名没写，和 CLI 的读取格式对不上 |
| release-project | 243 行（SKILL.md 224 + template 19） | 高 | 总量约 25–30%；日常 Execute 时 SKILL.md 加载量可减约 45% | 只跑一次的 Init（约 80 行）每次都加载；「常见问题」4 条全是正文的重复；semver 表属于通用教程；annotated tag 那句注释和命令本身矛盾 |
| clean-git | 189 行（仅 SKILL.md） | 中 | 约 20–25% | 跳过列表写了 3 遍，版本号、触发词和 frontmatter 重复；标题仍是旧名 git-cleanup；「三个分组均为空」指哪三个组没说清 |
| sync-hotfix | 188 行（仅 SKILL.md） | 中（以澄清为主） | 约 10–15% | 「Step 4/5 必须执行」说了两遍，Step 3 可以并进 Step 2；有 3 处分支没写结果；选项字母在不同步骤里含义不同 |

---

## 2. sync-agent（高）

### 2.1 问题归类（按 7 条）

- **第 2 条 重复/通用教程**
  - curl 调用写了 8 段，每段都重复 `-H "X-API-Key: ${API_KEY}"`，写请求的段还重复 `Content-Type`：`skills/meta/sync-agent/SKILL.md:46-52, 90-94, 115-117, 129-133, 143-145, 156, 161-165, 175-177`。调 REST 是通用能力，只有 method、路径、body 是本 skill 特有的。【读到】
  - `.stignore` 检查写了两遍：`SKILL.md:64-81`（查看状态时）和 `SKILL.md:98-108`（添加 folder 时）。两处 bash 写法不同，但判断条件等价：有 `.gitignore`，且 `.stignore` 不存在或不含 `#include .gitignore`。【读到 + 推出】
  - 第 10 行英文定位句和 description 重复：`SKILL.md:10`。【读到】
  - 「4xx/5xx 输出状态码和响应体」写了两遍：`SKILL.md:96` 和 `SKILL.md:185`。【读到】
- **第 3 条 用术语压缩**
  - device ID 格式用了一整句自然语言加算术：`SKILL.md:126`。可以换成一条正则 `^[A-Z0-9]{7}(-[A-Z0-9]{7}){7}$`，含义相同。【推出】
- **第 5 条 含糊或矛盾**
  - 暂停/恢复：`SKILL.md:168` 前半句说「回写 config.json」，括号里又说「不持久化到 config.json」。`tools/sync-agent/sync_agent/cli.py:164-181` 在 setup 时根本不读 `paused`，所以「不改 config.json」才是对的。【读到 cli.py，结论是推出】
  - 路径不存在时怎么办，两处说法冲突：`SKILL.md:87` 说「告知用户并询问是否继续」，`SKILL.md:186` 说「在调用 API 前就报错」。【读到】要用哪一种：未确认。
  - 错误处理原则要求「所有 curl 加 `-w "\nHTTP %{http_code}"`」（`SKILL.md:184`），但 8 段示范命令一个都没加：`SKILL.md:46-177`。【读到】
  - state.json 的字段：`SKILL.md:29` 写「提取 `API_KEY`、`API_URL`」，实际键名是小写的 `api_key`、`api_url`（`tools/sync-agent/sync_agent/config.py:47-49`）。agent 一般能对上，但这层映射应当写出来。【读到】
- **第 7 条 字段/接口核对**
  - 回写 `config.json` 时没写条目格式：`SKILL.md:97, 136`。`hskill sync setup` 读取时，folder 用 `id/path/label`，device 用 **`id`/`name`**（`cli.py:166-190`，第 186 行是 `device["id"]`）。REST body 里用的是 `deviceID`（`SKILL.md:132`）。agent 照抄 REST body 写进 config.json 的话，下次 `hskill sync setup` 会在 `device["id"]` 上出 KeyError。【读到代码，后果是推出】
- **第 6 条 指令和解释分开**：问题不大。

### 2.2 代表性修改

**(a) 把 curl 段改成一张端点表：`SKILL.md:42-178`**

修改前（节选，共 8 段这样的代码）：

```
curl -s -X DELETE \
  -H "X-API-Key: ${API_KEY}" \
  "${API_URL}/rest/config/folders/{FOLDER_ID}"
```

修改后：

```
所有请求：`curl -s -w "\nHTTP %{http_code}" -H "X-API-Key: ${API_KEY}"`，有 body 的加 `-H "Content-Type: application/json"`。

| 操作 | 请求 | body / 说明 | 回写 ~/.hskill/sync-agent/config.json |
|---|---|---|---|
| 查看状态 | GET /rest/config/folders；GET /rest/system/connections；每个 folder GET /rest/db/completion?folder={ID} | — | 不改 |
| 添加 folder | POST /rest/config/folders | {"id","path","label","type":"sendreceive","devices":[]} | folders 追加 {"id","path","label"} |
| 删除 folder | DELETE /rest/config/folders/{ID} | — | folders 移除该 id |
| 添加 device | POST /rest/config/devices | {"deviceID","name"} | devices 追加 {"id","name"}（键是 id，不是 deviceID） |
| 删除 device | DELETE /rest/config/devices/{ID} | — | devices 移除该 id |
| 暂停/恢复 | GET 再 PUT /rest/config/folders/{ID}，只改 paused | — | 不改 |
| 强制扫描 | POST /rest/db/scan?folder={ID} | — | 不改 |
```

理由：删掉重复的请求头；补上 `-w`，和错误处理原则一致；同时把 config.json 的字段名和第 168 行的矛盾一起写清。大约能删 60 行。

**(b) 两处 `.stignore` 合成一条规则：`SKILL.md:64-81, 98-108`**

修改前：两段 bash（一段分两次检查，一段合在一起检查），各自带「直接创建」和提示文案。

修改后：

```
**.stignore 规则**（查看状态时对每个 folder 检查；添加 folder 后对新 folder 检查）：folder 路径（`~` 展开）下有 `.gitignore`，且 `.stignore` 不存在或不含 `#include .gitignore` → 执行 `echo '#include .gitignore' > "$FOLDER_PATH/.stignore"`，并输出 `✓ Created .stignore for {id} ({path}) — linked to .gitignore`。
```

理由：两处判断条件等价，合并后只剩一份。`>`（覆盖写）的行为保持不变，见 2.4。

**(c) device ID 校验：`SKILL.md:126`**

修改前：「必须是 8 组 7 个大写字母数字，以 `-` 分隔（如 `XXXXXXX-…`），共 56 字符加 7 个分隔符 = 63 字符总长。」

修改后：「调 API 前校验 device ID 匹配 `^[A-Z0-9]{7}(-[A-Z0-9]{7}){7}$`，不匹配就报错。」

理由：用正则表达，含义不变，还把「在调 API 前报错」（原 `:186`）挪到了用得上的位置。

### 2.3 必须保留、不能动

- 开场播报 `"Using sync-agent to [describe action]."`：`SKILL.md:12`（输出契约）。
- 两条前置检查，以及它们的错误文案和恢复命令 `hskill sync setup`、`hskill sync start`：`SKILL.md:27, 38`。这是跨工具接口：daemon 的启停归 `hskill sync`，不归本 skill，description 里也写了。
- 路径 `~/.hskill/sync-agent/state.json`、`~/.hskill/sync-agent/config.json`，数组名 `folders`、`devices`。
- 状态输出格式：`SKILL.md:56-62`。
- folder 的 `type: sendreceive`、`devices: []`（和 `cli.py:174-180` 一致）。
- 「4xx/5xx 不继续后续步骤」。

### 2.4 未确认

- 路径不存在时，是「询问是否继续」（`:87`）还是「直接报错」（`:186`）？需要你定。
- `.stignore` 用 `>` 覆盖写：如果用户已经有一个不含 `#include` 的 `.stignore`，内容会被清掉。这是现有行为，精简时不改；是否本来就打算覆盖，未确认。
- 删除 folder/device 不需要用户确认。现有行为如此，只记录，不建议改。
- 查看状态时 paused folder 要不要也请求 completion：CLI 会跳过（`cli.py:125`），skill 没写。没查 API 对 paused folder 的返回值。【未查】

---

## 3. release-project（高）

### 3.1 问题归类

- **第 4 条 渐进式披露**：Init 阶段 `SKILL.md:31-109`（约 80 行）只在 profile 不存在或用户说「重新初始化」时才用，日常发版都走 Execute。可以挪到 `references/init.md`，入口判断那里写「→ 读 references/init.md 执行」。共同规则（profile 路径、「profile 是唯一依据」、只在本地操作）留在主文件。【读到结构；收益是推出】
- **第 2 条 重复/通用教程**
  - 「常见问题」4 条全是正文的重复：`:218` 重复 `:109`；`:220` 重复 `:135`（多出的只有「从 E-0 重来」）；`:222` 重复 `:165`；`:224` 重复 `:141`（多出的只有「或确认跳过」）。【读到】
  - semver 表：`:145-149`，属于通用概念。【读到】
  - E-2 单独一行 `TODAY=$(date +%Y-%m-%d)`：`:157-159`。后面没有任何地方用到这个变量。【读到】
  - 「保持现有格式」写了两遍：`:153` 和 `:155`。【读到】
  - 「不确定就问」写了三遍：`:33, :49, :73`。【读到】
  - E-0 的 git 命令示范：`:123-133`。用一句检查清单就能说清，但 `HEAD..origin/<branch>` 这个落后检查是具体的，应保留。【读到】
  - I-5 第 107 行重复了模板注释的内容（四个节、没有特殊规则就删掉该节）：`references/release-profile-template.md:7-19`。【读到】
- **第 3 条**：E-0「通常包括」后面跟了三段命令，可以压成「当前分支 = 起点分支、`git status --porcelain` 为空、不落后 `origin`」。
- **第 5 条 含糊或矛盾**
  - `:186-187`：`git tag <x> -m "<msg>"` 本身就会建 annotated tag，带 `-m` 时 git 隐含 `-a`。所以「若要求 annotated tag，加 -a」是错的：现在的写法总会建 annotated tag，即使 profile 要的是 lightweight tag。【读到；git 的这个语义属于通用知识】怎么改会影响要 lightweight tag 的项目，属于行为变更，需要你定，见 3.4。
  - `:139`「第一个『主版本声明文件』」：这个词在模板和 Init 里都没定义。【读到】
  - `:135`「profile 中有『发版前检查』」：模板没有这一节（`references/release-profile-template.md` 只有 4 节），I-4 收集到的检查项落在哪一节也没写。【读到】
  - E-8 第 212 行「可选：询问是否清理 release 分支」：问还是不问，没有给条件。
- **第 7 条**：标题和模板注释还是旧名 `project-release`：`SKILL.md:8`、`references/release-profile-template.md:2`。【读到】模板注释会写进生成的 profile，改它会让新生成的 profile 多一行差异，这一点不影响行为。

### 3.2 代表性修改

**(a) 入口 + 渐进式披露：`SKILL.md:17-109`**

修改前：入口判断之后，紧跟 80 行 Init 阶段正文。

修改后（主文件只留这些）：

```
## 入口判断
`.hskill/release-project/release-profile.md` 不存在，或用户说「重新初始化」 → 读 `references/init.md` 执行 Init（覆盖旧 profile）。
存在 → 执行下方 Execute。
```

理由：每次发版少加载约 80 行。Init 的逻辑原样搬过去，一行不删。

**(b) 删掉「常见问题」，把两条增量并回正文：`SKILL.md:216-224`**

修改前：4 条 Q&A。

修改后：E-0 末尾写「检查失败 → 停下告知用户；修复后从 E-0 重新开始」。E-1 第 141 行改成「没有 CHANGELOG 就询问本次改动摘要，或经用户确认跳过 CHANGELOG 更新」。

理由：只保留两处真正多出来的信息，删掉 9 行。

**(c) semver 表压成一句：`SKILL.md:143-149`**

修改前：一张 3 行的 patch/minor/major 表。

修改后：「按 semver 建议升级类型（只有 fix/docs/chore → patch；有兼容的新功能 → minor；有 breaking change → major），等用户确认后定下 NEW_VERSION。」

理由：只留关键词。「等用户确认」是授权边界，必须保留。

### 3.3 必须保留、不能动

- profile 路径 `.hskill/release-project/release-profile.md`，以及 `references/release-profile-template.md` 的四个顶级节名「分支模型 / 版本文件 / 发布方式 / 特殊规则」（E-4 按节名「特殊规则」读取）。
- **跨 skill 接口**：`init-project` 用这个路径作 probe，并以 `"/release-project 重新初始化"` 调用（`skills/coding/init-project/assets/templates/code.yml:26-28`、`references/template-schema.md:47-49`）。所以「重新初始化 → Init」这条入口规则（`:27`）连同触发词都不能删。
- Init 读取 `.hskill/init-workflow/workflow-config.yml`（`:39`），这是和 init-workflow 约定的路径。
- 授权边界：「profile 是唯一依据，不在 profile 里的事不要自己发明」（`:115`）；「所有操作只在本地做，不推送」（`:190`）；profile 先给用户看、确认后再保存（`:109`）；版本号由用户确认。
- E-0 到 E-8 的顺序。E-7 待执行清单的格式 `== 本地已完成，待执行 ==`（输出契约）。
- 「按 profile 顺序更新版本文件，然后用 `git diff` 核对」。

### 3.4 未确认

- annotated/lightweight tag：现在实际总是 annotated。改成「annotated：`-a -m`；lightweight：不带 `-m`」算行为修正，不算精简，要不要改需要你定。
- 「发版前检查」应该写进 profile 的哪一节？建议在 Execute 里明确写「从『特殊规则』读取」，或者给模板加一节。后者会改变 profile 的输出结构，需要你定。
- 「主版本声明文件」改成「版本文件清单第一项」，是否符合本意，未确认。
- `init-project` 的 check-report 说 release-project「执行时会先问『这个项目要发版吗？』」（`skills/coding/init-project/references/check-report.md:40`），这句话在 release-project 现有正文里找不到对应。这是 init-project 自己的行为，还是描述和实际已经不一致：【未查】。和本次拆分无关，但拆分时别误以为要在 Init 里补这一问。

---

## 4. clean-git（中）

### 4.1 问题归类

- **第 2 条 重复**
  - 跳过列表写了 3 遍：`skills/meta/clean-git/SKILL.md:48`、`:54`（「不在跳过列表中」）、`:56`（「预处理」整句）。【读到】
  - 版本号和 frontmatter 重复：`:10`；第 11 行定位句和 description 重复。【读到】
  - 「触发条件」一节：`:15-19`。触发由 frontmatter 的 description 决定，这一节不参与触发判断，见 4.4。
  - 「无配置时提示生成配置」写了两遍：`:31` 和 `:182-189`。【读到】
  - Keep 优先于 Delete 写了两遍：分类顺序（`:59` 排在 `:60` 前面）已经保证了这一点，`:65` 又单独警示一次。【读到】
  - Step 4 的「若为空跳过 / 若非空执行」：`:71-73`，一句话就能说清。
- **第 5 条 含糊**
  - `:104`「三个分组均为空」：一共有 4 个组名（KEEP / DELETE_RULE / AMBIGUOUS / DELETE_LLM），到这一步 AMBIGUOUS 已经分完。从上下文推断，指的是「组 A、组 B、组 C 全空」，也就是除跳过列表外没有任何分支。【推出】
  - `:89-90` prompt 里写死的保留/删除标准，和配置文件的「LLM 判断上下文」是叠加还是替代？默认 context（`:34`）又重复了一遍类似的标准。【读到】怎么处理未确认。
  - `:143`「对用户确认的分组」：只可能是组 A 和组 B，没有写明。
- **第 7 条**：标题 `# SKILL.md — git-cleanup`（`:8`）是旧名，name 是 `clean-git`。【读到】

### 4.2 代表性修改

**(a) Step 2/3 合并跳过列表：`SKILL.md:48-56`**

修改前：`:48`「跳过列表（不参与任何分析）：main、staging、当前分支名」；`:54`「对每条本地分支（不在跳过列表中）」；`:56`「预处理：先排除跳过列表（main、staging、当前分支名），剩余分支参与以下分类。」

修改后：在 Step 3 开头写一句「排除 `main`、`staging`、当前分支后，每条分支按以下顺序归类，命中即停：」。删掉 `:48` 和 `:56`。

理由：同一条规则写了 3 遍。「命中即停」把 `:65` 的 Keep 优先也包含进去了，`:65` 可以删。

**(b) 文件头：`SKILL.md:8-19`**

修改前：旧名标题、版本号、定位句、触发条件列表，共 12 行。

修改后：`# clean-git`，加一句定位「周期性梳理本地分支，识别并删除已合并的废弃分支」。

理由：版本号以 frontmatter 为准；触发条件的处理见 4.4。

**(c) 空分组边界：`SKILL.md:104`**

修改前：「若三个分组均为空（仓库只有主干分支或当前 repo 无需清理）」

修改后：「若排除跳过列表后没有任何分支，打印『✅ 所有分支已整理，无需清理』，跳到 Step 7；若只有组 C 非空，只展示组 C，再跳到 Step 7。」

理由：写明是哪几个组、各种情况下做什么。第二种情况（只有组 C）是我推出来的现有含义，需要核对。

### 4.3 必须保留、不能动

- 配置路径 `.hskill/clean-git/branch-cleanup.md`，三个段名 `## Always Delete`、`## Always Keep`、`## LLM 判断上下文`，每行 `` `pattern` `` 的格式（Step 7 生成的配置也要符合这个格式）。
- 内置默认规则：`:32-34`。
- glob 语义「`*` 不匹配 `/`」及示例：`:63`。
- 分类优先级：未合并 → Keep 规则 → Delete 规则 → LLM。
- 组 A/B 分别确认，组 C 只展示；`git branch -d`（不用 `-D`），失败时报告并跳过；remote 分支只提示手动删除命令，不自动删。
- 输出文案和格式：`:110-137, :161-164, :172-180, :185-186`。
- **跨 skill 接口**：`init-project` 把 clean-git 描述成「分支清理规则，跑完问是否存为配置」（`skills/coding/init-project/SKILL.md:144`），所以 Step 7 的询问不能删。

### 4.4 未确认

- 删掉正文「触发条件」一节，「梳理分支」这类中文触发词就只能靠 description 的语义去匹配。要不要把中文触发词补进 description？那属于改触发条件，需要你定。只删正文、不动 description 时，对触发的实际影响【未查】。
- prompt 里写死的标准（`:89-90`）和配置 context 是叠加还是被配置覆盖：未确认。建议精简时原样保留。
- `git branch -r | grep "origin/<branch>"`（`:155`）是子串匹配，`feature/foo` 会误命中 `origin/feature/foo-bar`。这是行为问题，不属于精简范围，只记录。
- `git branch --merged staging` 写死了 `staging`，仓库没有 staging 分支时会报错，skill 没写这种情况怎么办。也是行为问题，只记录。
- 文档漂移（不在本 skill 内）：`docs/reference/branch-cleanup-config.md`、`docs/how-to/git-cleanup.md:20,34` 仍写旧路径 `.claude/branch-cleanup.md`。【读到】

---

## 5. sync-hotfix（中，以澄清为主）

### 5.1 问题归类

- **第 2 条 重复**
  - 「Step 4/5 无论如何都执行」写了两遍：`skills/meta/sync-hotfix/SKILL.md:62` 和 `:123`。【读到】
  - 「跳过的条目不改标记」写了两遍：`:86` 和 `:95`。Step 3 整节（`:91-95`）可以并进 Step 2 的选项：A/D 处理完立即改成 `merged_back: true`，S 不改。【读到】
- **第 5 条 含糊**
  - 5.1「仅安装版」的文件，用户回答 y 之后做什么（复制到 `source_dir` 的同一相对路径？）没写：`:130`。【读到】
  - 5.3 `[CONFLICT]` 选「取源仓库（R）」后，安装版要不要改回去？「安装版改动放弃」可以理解为不写任何文件，也可以理解为覆盖安装版：`:162`。【读到】
  - Step 4 的提交提示里有 `<platform>`（`:116`），本次处理的多条条目可能来自不同平台，这时填什么没写。【推出】
  - 选项字母在不同步骤含义不同：S 在 Step 2 是「跳过」（`:86`），在 5.3 是「同步」（`:149, :155`）；R 在 UNLOGGED 里是「登记」（`:150`），在 CONFLICT 里是「取源仓库」（`:162`）。【读到】改字母会改变交互契约，只记录。
  - Step 4 叫「收尾」，但后面还有 Step 5：`:99`。建议改名为「HOTFIXES 摘要」。
- 第 3、4、6 条：没有明显问题。全文是一条线性流程，没有只在少数情况下才用的大段内容，不需要拆分。

### 5.2 代表性修改

**(a) Step 3 并进 Step 2：`SKILL.md:85-95`**

修改前：Step 2 的选项 A 写「→ 进入 Step 3 标记」，S 写「`merged_back` 保持 `false`」，D 写「→ 进入 Step 3 标记」；Step 3 再单独写「应用或作废后立即改为 true；跳过不改」。

修改后：「A/D 处理完，立即把 `skill_dir/references/HOTFIXES.md` 里该条目改成 `merged_back: true`；S 不改，下次调用还会出现。」删掉 Step 3，后续步骤重新编号或保留原编号。

理由：同一个状态转移写了两遍。注意 Step 1 的「跳过 Steps 2-3」也要同步改。

**(b) 去掉重复的「必须执行」：`SKILL.md:62, 123`**

修改前：两处都写了「无论哪种情况 / 无论是否有条目，Step 4 和 Step 5 都执行」。

修改后：只在 Step 1 末尾保留一句「无论有没有待合并条目，都执行 Step 4 和 Step 5」，删掉 `:123`。

理由：重复。

### 5.3 必须保留、不能动

- **跨 skill 接口：HOTFIXES.md 格式**。字段 `platform/date/file/section/change/reason/merged_back`、编号 `HF-NNN`、位置 `skill_dir/references/HOTFIXES.md`，由 fix-skill 写入（`docs/reference/hotfix-lifecycle.md`）。Step 2 用 `section` 定位章节标题，5.3「登记」追加新条目时也要符合这个格式。
- 配置 `~/.hskill/sync-hotfix/config.json` 的结构 `source_root` + `skills.<name>: <category>`，合并写入、不覆盖其他条目；`source_dir` 的拼接规则。
- 三个平台的安装路径表：`:22-26`。
- 4 个差异标记 `[UNLOGGED]/[PLATFORM]/[SRC_AHEAD]/[CONFLICT]` 和各自的选项；分类时要注明推断理由。
- 两条 commit message 模板：`:116`、`:187`；两份摘要的格式。
- 应用或同步之前「先展示修改结果，用户确认后再写入」。

### 5.4 未确认

- 5.1 选 y 后的具体动作，以及 CONFLICT 选 R 后安装版改不改：这两处需要你补规则，不然 agent 只能自己猜。
- 多平台条目同时存在时，commit message 里的 `<platform>` 填什么：未确认。

---

## 6. 潜力低/无

本 bundle 4 个 skill 都在「中」及以上，没有评为低/无的。sync-hotfix 是 4 个里最紧凑的，评「中」只是因为有 3 处要补的规则，能删的行数有限（约 10–15%）。
