# 如何配置本地开发环境

## 前提条件

- 已安装 Node.js 18+
- 已安装 Git

## 步骤

### 1. 克隆仓库

```bash
git clone <repo-url>
cd <project-name>
```

### 2. 安装依赖

```bash
npm install
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入本地配置值。

### 4. 启动开发服务器

```bash
npm run dev
```

服务启动后访问 http://localhost:3000。

## 常见问题

**端口冲突** — 修改 `.env` 中的 `PORT` 值。

**依赖安装失败** — 删除 `node_modules/` 后重试：`rm -rf node_modules && npm install`。
