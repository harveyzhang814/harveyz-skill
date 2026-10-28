# 修复引导

逐项询问用户是否修复；每项单独确认。

**格式问题** — 展示 diff，用户确认后直接编辑 `SKILL.md`：
```
修复 F2（name 字段）：
  - name: my_skill
  + name: my-skill
应用此修复？(y/n)
```

**格式警告（F7）** — 命名不符合规范建议时，提示新名，跳过不影响发布：
```
F7 警告：目录名 'skill-analyzer' 不符合命名规范建议（'skill' 是名词而非动词）。
建议改为：analyze-skill（动词 analyze 在词表中，名词 skill）
是否重命名？(y/n/跳过)
```
选 `y` 则执行 `git mv` 重命名目录，并更新 `skills-index.json` 中对应的 `path` 值，最后运行 `node scripts/generate-npmignore.js`；选 `n`/跳过则保留警告，不做修改，不影响发布。

**格式警告（F9）** — 动词未命中词表但语义合理，不阻止发布，仅询问是否顺带补充词表：
```
F9 警告：动词 'probe' 未命中规范词表（语义合理）。
是否将 'probe' 加入 docs/reference/skill-spec.md 的规范动词词表？(y/n/跳过)
```
选 `y` 则用 Edit 工具在 `docs/reference/skill-spec.md` 的词表中追加该动词及含义（需用户补充一句含义描述）；选 `n`/跳过则保留警告，不做修改。

**格式问题（F8）** — 询问 bump 类型后自动更新版本号，随即执行 Step 7：
```
修复 F8（内容 hash 不匹配）：
  skill 内容自 v1.0.0 起已变更，但 version 仍为 1.0.0。
  请选择升级类型：
    [1] patch → 1.0.1（bugfix / 措辞调整）
    [2] minor → 1.1.0（新增步骤 / 行为变更）
    [3] major → 2.0.0（Breaking Change）
```
用户选择后，用 Edit 工具将 SKILL.md frontmatter 中的 `version:` 行更新为新版本号，然后直接进入 Step 7（hash 不同 + version 已递增，满足更新条件）。

**注册问题（R1）** — 交互引导补注册：
```
'meta/my-skill' 未注册。
现有 bundle：
  1. analysis — ...
  2. meta     — ...
  N. [新建 bundle]
选择目标 bundle：
```

选定 bundle 后，列出 R4 的三个合法值和「跳过」让用户选，在 `skills[]` 末尾追加（跳过则不写 installScope 字段）：
```json
{ "path": "meta/my-skill", "bundle": "meta", "installScope": "global" }
```

若新建 bundle，在 `bundleMeta` 中同步添加。

完成注册后运行：
```bash
cd "${REPO_ROOT}" && node scripts/generate-npmignore.js
```

**注册警告（R4）** — 为已注册但缺少 installScope 的 skill 补充推荐级别：列出 R4 的三个合法值和「跳过」让用户选；跳过则不写该字段。选定后用 Edit 工具在 `skills-index.json` 对应条目中添加 `installScope` 字段，再暂存：
```bash
git add skills-index.json
```
