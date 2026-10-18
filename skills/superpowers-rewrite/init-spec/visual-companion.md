# 可视化辅助工具指南

基于浏览器的可视化头脑风暴辅助工具，用于展示模型图、示意图和选项。

## 何时使用

按每个问题判断，不按整场会话判断。判断标准：**相比阅读文字，用户看图是否更容易理解？**

当内容本身具有视觉性质时，**使用浏览器**：

- **UI 模型图**——线框图、布局、导航结构、组件设计
- **架构图**——系统组件、数据流、关系图
- **并排视觉比较**——比较两种布局、两种配色、两种设计方向
- **设计打磨**——问题涉及外观感受、间距、视觉层级时
- **空间关系**——用图呈现的状态机、流程图、实体关系

当内容是文字或表格时，**使用终端**：

- **需求与范围问题**——“X 是什么意思？”“哪些功能在范围内？”
- **概念性的 A/B/C 选择**——在用文字描述的方案之间选择
- **取舍列表**——优缺点、比较表格
- **技术决策**——API 设计、数据建模、架构方案选择
- **澄清问题**——任何答案是文字、而非视觉偏好的问题

一个*有关* UI 的问题，并不自动属于视觉问题。“你想要哪一类分步向导？”是概念问题，使用终端。“这些向导布局中，哪个感觉合适？”是视觉问题，使用浏览器。

## 工作原理

服务器监视某个目录中的 HTML 文件，并向浏览器提供最新文件。你将 HTML 内容写入 `screen_dir`，用户在浏览器中看到内容，并可点击选择选项。选择记录在 `state_dir/events`，供你下一轮读取。

**内容片段与完整文档：** 如果 HTML 文件以 `<!DOCTYPE` 或 `<html` 开头，服务器会原样提供它（仅注入辅助脚本）。否则，服务器会自动将内容包在框架模板中，添加页眉、CSS 主题、连接状态和所有交互基础设施。**默认编写内容片段。** 只有在需要完全控制页面时才编写完整文档。

## 启动会话

```bash
# 仅在用户同意使用辅助工具后启动。--open 会在第一个画面出现时
# 自动打开浏览器；--project-dir 会持久保存模型图，并支持使用同一端口重启。
bash scripts/start-server.sh --project-dir /path/to/project --open

# 返回：{"type":"server-started","port":52341,
#        "url":"http://localhost:52341/?key=ab12…",
#        "screen_dir":"/path/to/project/.superpowers/brainstorm/12345-1706000000/content",
#        "state_dir":"/path/to/project/.superpowers/brainstorm/12345-1706000000/state"}
```

保存响应中的 `screen_dir` 和 `state_dir`。使用 `--open` 时，推送第一个画面后浏览器会自行打开，无需请用户手动打开；但仍要提供 URL 作为后备（无界面或远程环境不会自动打开）。

**URL 含有会话密钥（`?key=…`）。** 服务器会拒绝没有密钥的请求，因此始终向用户提供 `url` 字段中的**完整** URL，绝不要删除查询字符串，也不要提供只有 `http://host:port` 的地址。密钥控制 HTTP 和 WebSocket 访问，防止无关浏览器标签页或网络中的其他机器读取画面或注入事件。首次加载后，浏览器通过 cookie 记住密钥，因此重新加载和访问 `/files/*` 资源无需重复传入密钥。

**查找连接信息：** 服务器会将启动 JSON 写入 `$STATE_DIR/server-info`。如果你在后台启动服务器但没有捕获标准输出，读取该文件即可获得 URL 和端口。使用 `--project-dir` 时，在 `<project>/.superpowers/brainstorm/` 中查找会话目录。

**注意：** 将项目根目录传给 `--project-dir`，这样模型图会保存在 `.superpowers/brainstorm/`，重启服务器后仍然保留。不传时，文件会放入 `/tmp` 并被清理。如果 `.gitignore` 尚未包含 `.superpowers/`，提醒用户添加。

**按平台启动服务器：**

**Claude Code：**
```bash
# 默认模式即可；脚本会自行将服务器放到后台。
bash scripts/start-server.sh --project-dir /path/to/project --open
```

在 Windows 上，脚本会自动检测并切换到前台模式（会阻塞工具调用）。在 Bash 工具调用中设置 `run_in_background: true`，让服务器跨对话轮次持续运行，然后在下一轮读取 `$STATE_DIR/server-info`，获取 URL 和端口。

**Codex：**
```bash
# Codex 会回收后台进程。脚本会自动检测 CODEX_CI，
# 并切换到前台模式。正常运行即可，无需额外参数。
bash scripts/start-server.sh --project-dir /path/to/project --open
```

**Gemini CLI：**
```bash
# 使用 --foreground，并在 shell 工具调用中设置 is_background: true，
# 使进程跨对话轮次持续运行。
bash scripts/start-server.sh --project-dir /path/to/project --open --foreground
```

**Copilot CLI：**
```bash
# 使用 Copilot CLI 的非阻塞/后台 shell 机制启动，让服务器跨轮次持续运行。
# 保留 --foreground，由宿主运行环境而非脚本管理后台运行。
# 启动器是 .sh 文件，因此通过 bash 调用
# （在 Windows 上，通过 PowerShell 工具调用 Git Bash 的 bash.exe）。
bash scripts/start-server.sh --project-dir /path/to/project --open --foreground
```

**其他环境：** 服务器必须在后台跨对话轮次持续运行。如果你的环境会回收脱离的进程，使用 `--foreground`，并通过该平台的后台执行机制启动命令。

如果浏览器无法访问 URL（常见于远程或容器环境），绑定非回环地址：

```bash
bash scripts/start-server.sh \
  --project-dir /path/to/project \
  --host 0.0.0.0 \
  --url-host localhost
```

使用 `--url-host` 控制返回的 URL JSON 中显示哪个主机名。

## 交互循环

1. **检查服务器仍在运行**，然后将 **HTML 写入** `screen_dir` 中的新文件：
   - **必须：在引用 URL 或推送画面前，确认服务器仍在运行。** 检查 `$STATE_DIR/server-info` 存在，且 `$STATE_DIR/server-stopped` 不存在。如果服务器已经关闭，用 `start-server.sh` 和**同一个 `--project-dir`** 重启：它会复用同一端口，用户已打开的标签页会自行重新连接（服务器停止期间会显示“已暂停”的覆盖层），无需发送新 URL。服务器空闲 4 小时后自动退出（可用 `--idle-timeout-minutes` 配置）。
   - 使用语义明确的文件名：`platform.html`、`visual-style.html`、`layout.html`
   - **绝不复用文件名**——每个画面都使用新文件
   - 使用文件创建工具——**绝不要使用 cat/heredoc**（会向终端倾倒大量无关内容）
   - 服务器会自动提供最新文件

2. **告诉用户将看到什么，并结束当前轮次：**
   - 提醒他们 URL（每一步都要，不只第一步）
   - 简短概述画面内容（例如：“正在展示主页的 3 种布局选项”）
   - 请他们在终端回复：“看看后告诉我你的想法。如果愿意，也可以点击选择一个选项。”

3. **下一轮**——用户在终端回复后：
   - 如果 `$STATE_DIR/events` 存在，读取它；其中以 JSON Lines 格式记录用户的浏览器交互（点击、选择）
   - 结合用户的终端文字，获得完整反馈
   - 终端消息是主要反馈；`state_dir/events` 提供结构化交互数据

4. **迭代或推进**——如果反馈会改变当前画面，写入新文件（如 `layout-v2.html`）。只有当前步骤得到确认后，才能进入下一个问题。

5. **回到终端时清空旧画面**——下一步无需浏览器时（例如澄清问题、讨论取舍），推送等待画面，清除过时内容：

   ```html
   <!-- 文件名：waiting.html（或 waiting-2.html 等） -->
   <div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
     <p class="subtitle">正在终端中继续……</p>
   </div>
   ```

   这样可避免对话已经推进，用户却仍盯着已解决的选择。下一个视觉问题出现时，照常推送新的内容文件。

6. 重复，直至完成。

## 编写内容片段

只编写页面内部的内容。服务器会自动套用框架模板（页眉、主题 CSS、连接状态和全部交互基础设施）。

**最简示例：**

```html
<h2>哪种布局更合适？</h2>
<p class="subtitle">请考虑可读性与视觉层级</p>

<div class="options">
  <div class="option" data-choice="a" onclick="toggleSelect(this)">
    <div class="letter">A</div>
    <div class="content">
      <h3>单栏</h3>
      <p>简洁、专注的阅读体验</p>
    </div>
  </div>
  <div class="option" data-choice="b" onclick="toggleSelect(this)">
    <div class="letter">B</div>
    <div class="content">
      <h3>双栏</h3>
      <p>侧边栏导航搭配主内容</p>
    </div>
  </div>
</div>
```

这样就够了。无需 `<html>`、CSS 或 `<script>` 标签，服务器会提供这些内容。

## 可用的 CSS 类

框架模板提供以下 CSS 类供内容使用：

### 选项（A/B/C 选择）

```html
<div class="options">
  <div class="option" data-choice="a" onclick="toggleSelect(this)">
    <div class="letter">A</div>
    <div class="content">
      <h3>标题</h3>
      <p>描述</p>
    </div>
  </div>
</div>
```

**多选：** 向容器添加 `data-multiselect`，即可允许用户选择多个选项。每次点击都会切换该项的选中样式。

```html
<div class="options" data-multiselect>
  <!-- 使用相同的选项标记；用户可选择或取消选择多个选项 -->
</div>
```

### 卡片（视觉设计）

```html
<div class="cards">
  <div class="card" data-choice="design1" onclick="toggleSelect(this)">
    <div class="card-image"><!-- 模型图内容 --></div>
    <div class="card-body">
      <h3>名称</h3>
      <p>描述</p>
    </div>
  </div>
</div>
```

### 模型图容器

```html
<div class="mockup">
  <div class="mockup-header">预览：仪表盘布局</div>
  <div class="mockup-body"><!-- 模型图的 HTML --></div>
</div>
```

### 分栏视图（并排）

```html
<div class="split">
  <div class="mockup"><!-- 左侧 --></div>
  <div class="mockup"><!-- 右侧 --></div>
</div>
```

### 优缺点

```html
<div class="pros-cons">
  <div class="pros"><h4>优点</h4><ul><li>益处</li></ul></div>
  <div class="cons"><h4>缺点</h4><ul><li>不足</li></ul></div>
</div>
```

### 模拟元素（线框图构建块）

```html
<div class="mock-nav">标志 | 首页 | 关于 | 联系</div>
<div style="display: flex;">
  <div class="mock-sidebar">导航</div>
  <div class="mock-content">主内容区域</div>
</div>
<button class="mock-button">操作按钮</button>
<input class="mock-input" placeholder="输入字段">
<div class="placeholder">占位区域</div>
```

### 排版与区块

- `h2`——页面标题
- `h3`——区块标题
- `.subtitle`——标题下方的次要文字
- `.section`——带下边距的内容区块
- `.label`——小号大写标签文字

## 浏览器事件格式

用户在浏览器中点击选项时，交互记录会写入 `$STATE_DIR/events`（每行一个 JSON 对象）。推送新画面时，该文件会自动清空。

```jsonl
{"type":"click","choice":"a","text":"选项 A - 简单布局","timestamp":1706000101}
{"type":"click","choice":"c","text":"选项 C - 复杂网格","timestamp":1706000108}
{"type":"click","choice":"b","text":"选项 B - 混合布局","timestamp":1706000115}
```

完整事件流展示用户的探索路径：他们可能点击多个选项后才做决定。最后一个 `choice` 事件通常是最终选择，但点击模式也可能揭示值得询问的犹豫或偏好。

如果 `$STATE_DIR/events` 不存在，说明用户没有与浏览器交互，只使用他们的终端文字反馈。

## 设计建议

- **按问题调整保真度**——布局问题使用线框图，细节打磨问题使用精细设计
- **每页都说明问题**——例如“哪种布局感觉更专业？”，而不只是“选一个”
- **先迭代，再推进**——如果反馈改变当前画面，编写新版本
- 每个画面**最多 2–4 个选项**
- **有必要时使用真实内容**——摄影作品集使用真实图片（Unsplash）。占位内容会掩盖设计问题。
- **保持模型图简单**——专注布局与结构，无需像素级精确设计

## 文件命名

- 使用语义明确的名称：`platform.html`、`visual-style.html`、`layout.html`
- 绝不复用文件名；每个画面必须使用新文件
- 迭代时添加版本后缀，如 `layout-v2.html`、`layout-v3.html`
- 服务器根据修改时间提供最新文件

## 清理

```bash
bash scripts/stop-server.sh $SESSION_DIR
```

如果会话使用了 `--project-dir`，模型图文件会保留在 `.superpowers/brainstorm/`，供日后参考。只有 `/tmp` 会话会在停止时被删除。

## 参考

- 框架模板（CSS 参考）：`scripts/frame-template.html`
- 辅助脚本（客户端）：`scripts/helper.js`
