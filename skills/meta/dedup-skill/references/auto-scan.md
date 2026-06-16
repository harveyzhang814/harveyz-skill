# 全量扫描模式

对 `skills/` 目录下所有已注册 skill 执行重叠检测。这是低频操作，用于定期整体审查。

---

## 执行步骤

### Step 1 — 获取所有已注册 skill 列表

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
node -e "
  const idx = JSON.parse(require('fs').readFileSync('${REPO_ROOT}/skills-index.json','utf8'));
  idx.skills.forEach(s => console.log(s.path.split('/').pop()));
"
```

### Step 2 — 触发域扫描（轻量）

读取所有 skill 的 `description` 字段，两两比较触发意图：

- 找出 description 语义高度重叠的 skill 对（同一类用户需求可能触发多个 skill）
- 输出：触发域重叠对列表（若无，记录"触发域未发现重叠"后继续）

### Step 3 — 内容重叠分析

对触发域重叠对，以及其他你判断值得深入检查的 skill 对，
按主 SKILL.md 的流程执行：Step 1（语义块提取）→ Step 2（跨 skill 块聚类）→ Step 3（职责边界分析）。

### Step 4 — 汇总报告

按主 SKILL.md 的报告结构输出，在报告顶部标注"全量扫描"模式。

文件名格式：`dedup-full-<YYYYMMDD-HHMMSS>.md`

输出目录优先级与主 SKILL.md 相同（先查 DIR_METHOD.md，否则写入 `docs/skill-analysis/`）。
