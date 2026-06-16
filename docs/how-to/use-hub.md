# 如何使用 hub

hub 是个人开发者 OS —— 在终端里管理项目列表和任务，支持 TUI 交互界面和 CLI 命令行两种用法。

## 安装

```bash
hskill install --tool hub
source ~/.zshrc
```

## 启动 TUI

```bash
hub
```

无参数启动，进入三栏 TUI 界面：Projects / Git / Tasks。按 `Tab` 切换列，`Enter` 打开项目，`q` 退出。

## 管理项目

```bash
# 注册项目
hub projects add my-repo --path ~/Projects/my-repo --desc "简短描述"

# 列出所有项目
hub projects list

# 从 p-launch 配置自动扫描（需已安装 p-launch）
hub projects sync
```

### 在新设备上批量初始化（不依赖 p-launch）

```bash
hub projects scan ~/Projects
hub projects scan ~/Projects ~/Work   # 多个目录
```

扫描每个目录的直接子目录，找到 git 仓库后自动以 origin remote URL 的仓库名注册。已存在的同名项目跳过，不覆盖。

## 管理任务

```bash
# 添加任务（--project 必填）
hub tasks add "修复登录 bug" --project my-repo --priority P1

# 列出任务（支持过滤）
hub tasks list
hub tasks list --project my-repo
hub tasks list --status todo
hub tasks list --priority P1

# 标记完成
hub tasks done 42

# 更新字段
hub tasks update 42 --title "新标题" --priority P2

# 删除任务
hub tasks rm 42
```

## 优先级值

| 值 | 含义 |
|----|------|
| `P1` | 紧急 |
| `P2` | 默认 |
| `P3` | 低优先级 |

## 状态值

| 值 | 含义 |
|----|------|
| `todo` | 待办（默认） |
| `done` | 已完成 |
