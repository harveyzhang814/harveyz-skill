# Docker Compose 日志最佳实践

适用场景：用 docker-compose.yml 编排的多容器应用

## 日志产生方式

Docker 将每个容器的 stdout/stderr 统一收集为容器日志，通过 `docker logs` 读取。
容器内写到文件的日志，Docker 不会自动收集，需单独处理。

**最佳实践：让容器把日志写到 stdout/stderr，而不是文件。**
这样 Docker 统一管理，tail 最简单。如果应用写文件，考虑用 volume mount 后在宿主机 tail。

## 时间戳处理

Docker 自带时间戳（`docker logs --timestamps`），但格式是 RFC3339（`2024-01-15T14:30:01.234567890Z`），与 ISO 8601 兼容，**不需要额外处理**。

但默认 `docker logs -f` 不输出时间戳——需要加 `--timestamps` 标志：

```bash
docker logs -f --timestamps mycontainer 2>&1 >> container.log &
```

如果容器应用本身在日志行里也有时间戳，两者都会出现。这是无损的，不需要去掉任何一个。

## 接入方式

每个容器写入各自独立的日志文件，文件名即来源标识：

**遍历所有容器：**

```bash
LOGS=/tmp/myproject-logs
mkdir -p "$LOGS"

for c in $(docker compose ps -q); do
  name=$(docker inspect --format='{{.Name}}' "$c" | tr -d '/')
  docker logs -f --timestamps "$c" >> "$LOGS/${name}.log" 2>&1 &
done
```

**单容器：**

```bash
docker logs -f --timestamps <container_name> >> "$LOGS/api.log" 2>&1 &
```

**从历史日志开始（适合容器已在运行）：**

```bash
docker logs --since 5m -f --timestamps <container_name> >> "$LOGS/api.log" 2>&1 &
```

## 容器内写文件的日志

如果容器把日志写到容器内文件（如 `/app/logs/app.log`），有两种方案：

**方案 A：exec 进容器 tail（简单，适合临时调试）**

```bash
docker exec <container> tail -F /app/logs/app.log >> "$LOGS/api-file.log" &
```

**方案 B：volume mount 到宿主机（推荐，持久）**

在 docker-compose.yml 中挂载日志目录：
```yaml
volumes:
  - ./logs/api:/app/logs
```
然后在宿主机 tail 该目录（若文件无时间戳，capture 层注入）。

## 常见陷阱

- 容器重启后 `docker logs -f` 会断开 → 需要重新 attach，或用 `--follow` 加监控脚本
- 部分镜像把日志写到 `/dev/null`（silent by default）→ 检查应用的日志级别环境变量
- `docker compose logs -f` 会混合所有容器输出且格式难以 grep → 分容器 tail 更可控
- 容器时区与宿主机不同 → 日志时间戳可能不对齐，需注意 `TZ` 环境变量
