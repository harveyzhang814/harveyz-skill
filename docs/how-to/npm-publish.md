# 如何发布到 npm（npx 可用）

## 前提条件

```bash
npm whoami   # 应返回 harveyzhang96，否则先 npm login
```

---

## 1. 更新 skills-index.json（仅新增 skill 时）

在 `skills[]` 数组中添加条目：

```json
{ "path": "category/skill-name", "bundle": "bundle-name" }
```

若 bundle 是新的，同时在 `bundleMeta` 里添加一行描述。

`skills-index.json` 是唯一需要改动的地方——其他文件（`package.json files`、`.npmignore`）由脚本自动生成。

---

## 2. Bump 版本号

```bash
npm version patch   # bug fix / 小改动 → 0.1.2 → 0.1.3
npm version minor   # 新增 skill → 0.1.2 → 0.2.0
npm version major   # 破坏性变更 → 0.1.2 → 1.0.0
```

该命令会自动提交一个版本 commit 并打 tag。

---

## 3. 发布

```bash
npm publish
```

`prepack` 钩子会自动运行 `node scripts/generate-npmignore.js`，更新 `package.json files` 和 `.npmignore` 后再打包。

---

## 4. 验证

```bash
npm view harveyz-skill version          # 确认版本已更新
npx harveyz-skill list                  # 确认 CLI 可用
```

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `npm publish` 报 403 | 未登录或无权限 | `npm login` |
| 新 skill 未出现在安装列表 | 未加入 `skills-index.json` | 补充索引条目后重新发布 |
| `prepack` 脚本报找不到目录 | `skills-index.json` 引用了不存在的路径 | 检查 `path` 字段是否与实际目录一致 |
