---
name: read-paper
version: "0.1.0"
description: "三遍精读单篇学术论文 PDF。第一遍：5C 结构化定向；第二遍：全文内容提取；第三遍：批判性重构。每遍产出独立 Markdown 文件，存放在以论文命名的文件夹中。触发场景：用户想精读一篇论文、分析论文质量、生成论文笔记。"
user_invocable: true
---

# read-paper

三遍精读单篇 PDF 论文。每遍独立产出一个 Markdown 文件。

底层方法论说明见 `docs/superpowers/specs/2026-06-16-read-paper-design.md`。

---

## 路径变量

```
ConfigPath: ~/.hskill/read-paper/config.json
```

---

## 执行流程

### Step 0：初始化配置

用 Read 工具读取 `~/.hskill/read-paper/config.json`。

若文件不存在，询问用户：

```
论文分析笔记保存到哪个目录？（直接回车使用默认：~/Documents/papers）
```

用户回复后，用 Bash 工具写入配置：

```bash
mkdir -p ~/.hskill/read-paper
echo '{"output_dir": "用户指定路径"}' > ~/.hskill/read-paper/config.json
```

若文件已存在，解析 JSON 取出 `output_dir` 字段直接使用。
