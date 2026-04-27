# 如何启动全栈调试环境（Docker Compose）

## 概述

本环境为 docker-app（Docker Compose 多容器）搭建了三层独立日志捕获：

- **api.log** — API 服务容器（Node.js）的完整 stdout/stderr
- **worker.log** — Celery Worker 容器的任务处理日志（任务驱动型）
- **db.log** — PostgreSQL 查询日志

`worker.log` 是**任务驱动型**来源：只有 Celery 任务实际运行时才产生输出。无活跃任务时验证脚本报 SKIP，属正常情况，不影响环境就绪状态。

## 前提条件

- Docker Desktop 已启动
- `docker compose up -d` 已成功运行
- `tmp/` 已加入 `.gitignore`

## 启动步骤

### 1. 创建日志目录

```bash
mkdir -p tmp/logs
```

### 2. 启动所有日志捕获

```bash
# API 容器
docker compose logs -f api 2>&1 \
  | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' \
  >> tmp/logs/api.log &
echo $! > tmp/logs/api-capture.pid

# Worker 容器（即使暂无任务也要提前启动捕获）
docker compose logs -f worker 2>&1 \
  | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' \
  >> tmp/logs/worker.log &
echo $! > tmp/logs/worker-capture.pid

# PostgreSQL
docker compose exec db bash -c "tail -f /var/log/postgresql/postgresql-*.log" 2>&1 \
  | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' \
  >> tmp/logs/db.log &
echo $! > tmp/logs/db-capture.pid
```

### 3. 验证环境就绪

```bash
bash harness/debug/verify-logs.sh
```

**常驻来源 OK + 任务驱动型 SKIP = 环境就绪。**

## 排查问题

**api.log MISSING**
- `docker compose ps` 确认 api 容器在运行
- 检查 PID 文件：`cat tmp/logs/api-capture.pid`

**db.log 为空**
- PostgreSQL 默认不开启查询日志，需在 docker-compose.yml 中添加：
  ```yaml
  command: postgres -c log_destination=stderr -c logging_collector=off -c log_min_duration_statement=0
  ```

**worker.log 一直 SKIP**
- 这是正常的（任务驱动型）。入队一个任务后再查：
  ```bash
  tail -f tmp/logs/worker.log
  ```

## 关闭环境

```bash
for pid_file in tmp/logs/*-capture.pid; do
  kill "$(cat "$pid_file")" 2>/dev/null || true
done
rm -rf tmp/logs/
```
