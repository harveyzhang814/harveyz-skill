# 全栈调试环境参考

## 日志目录

```
tmp/logs/
├── api.log      — API 容器 stdout/stderr（常驻）
├── worker.log   — Celery Worker 容器 stdout（任务驱动型）
└── db.log       — PostgreSQL 查询日志（常驻）
```

**任务驱动型**：`worker.log` 只在有 Celery 任务执行时才产生输出，验证脚本报 SKIP 属正常。

## 启动日志捕获

```bash
mkdir -p tmp/logs

# api 容器（常驻）
docker compose logs -f api 2>&1 \
  | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' \
  >> tmp/logs/api.log &
echo $! > tmp/logs/api-capture.pid

# worker 容器（任务驱动型）
docker compose logs -f worker 2>&1 \
  | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' \
  >> tmp/logs/worker.log &
echo $! > tmp/logs/worker-capture.pid

# PostgreSQL 查询日志
docker compose exec db bash -c "tail -f /var/log/postgresql/postgresql-*.log" 2>&1 \
  | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' \
  >> tmp/logs/db.log &
echo $! > tmp/logs/db-capture.pid
```

## 验证脚本

```bash
bash harness/debug/verify-logs.sh
```

- `OK` — 来源正常写入
- `SKIP` — 任务驱动型来源，暂无任务属正常
- `FAIL/MISSING` — 常驻来源未就绪，需排查

## 查询方式

```bash
# API 层错误
grep -iE "error|exception|500" tmp/logs/api.log | tail -20

# Worker 任务失败
grep -iE "FAIL|Traceback|retry" tmp/logs/worker.log | tail -20

# DB 慢查询
grep "duration:" tmp/logs/db.log | tail -20

# 跨层时序合并
sort -m <(grep "^2" tmp/logs/api.log) \
        <(grep "^2" tmp/logs/worker.log) \
        <(grep "^2" tmp/logs/db.log) | tail -50
```

## 停止捕获

```bash
for pid_file in tmp/logs/*-capture.pid; do
  kill "$(cat "$pid_file")" 2>/dev/null || true
done
```
