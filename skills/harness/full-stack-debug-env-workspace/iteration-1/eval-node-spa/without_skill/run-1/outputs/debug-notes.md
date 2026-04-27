# 调试环境搭建笔记

启动后端并把日志保存到文件：

```bash
node server.js > logs/app.log 2>&1 &
```

前端用浏览器 DevTools 看 console。

如果需要同时查看前后端日志，可以用 `tail -f` 跟踪文件。
