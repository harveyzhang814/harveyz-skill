# Docker 调试说明

查看所有容器日志：

```bash
docker compose logs -f
```

查看某个服务：

```bash
docker compose logs -f api
docker compose logs -f worker
```

把日志保存到文件：

```bash
docker compose logs > all-logs.txt
```
