# References — 技术栈日志最佳实践

本目录按技术栈积累日志捕获的最佳实践。执行第三阶段（环境搭建）时，**先查这里**，找到对应技术栈后直接参照执行；没有找到再自行设计，设计完后把结论补充进来。

## 当前收录

最佳实践文件统一放在 `tech-stacks/` 子目录：

| 文件 | 适用技术栈 |
|---|---|
| `tech-stacks/node-process.md` | Node.js 裸进程（Express、Fastify、Koa、NestJS 等） |
| `tech-stacks/electron.md` | Electron（主进程 + preload + renderer） |
| `tech-stacks/docker-compose.md` | Docker Compose 多容器应用 |
| `tech-stacks/browser-spa.md` | 浏览器 SPA（React、Vue、Angular、Svelte 等） |

## 如何添加新条目

在新项目中设计了某个技术栈的日志捕获方案后，在 `tech-stacks/` 下新建文件：

```
references/tech-stacks/<tech-stack>.md

内容结构：
- 适用场景
- 日志产生方式（日志去哪里）
- 捕获原则（先决条件、权衡）
- 接入方式（具体做法）
- 常见陷阱
```

文件名用技术栈名，小写加连字符，如 `python-django.md`、`rails.md`、`kafka-consumer.md`。
