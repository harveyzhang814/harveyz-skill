# p-launch 调试回顾

记录 p-launch Ghostty/Cursor 集成开发过程中出现的所有问题、根源及解决方案，以及测试方法论的反思。

---

## 一、问题清单

### 问题 1：Cursor CLI 报错 "cursor CLI not found"

**根源：** `cursor` 命令不在 PATH 里，脚本没有 fallback。

**解决：** 先检测 `cursor` CLI，找不到时 fallback 到 `/usr/bin/open -na "Cursor"`。

---

### 问题 2：Ghostty 窗口打开但无提示符 / 空白界面

**根源：** 用 `open -na` 强制新进程，与已运行的 Ghostty 实例冲突，导致窗口状态异常。

**解决：** 放弃 `open` 系列，改用 macOS Services（NSPerformService）。

---

### 问题 3：Ghostty 窗口打开但目录是用户目录 `~`，不是项目目录

**根源：** `open -a Ghostty --args /path` 在 Ghostty 已运行时会被忽略，app 收不到路径参数。AppleScript `new surface configuration` 方案因 Ghostty 1.3.1 的 `withCString` 指针生命周期 bug 也失效。

**解决：** 改用 `NSPerformService("New Ghostty Window Here", pasteboard)`，和 Finder 右键菜单走同一代码路径。

---

### 问题 4：NSPerformService 返回 `false`

**根源：** pasteboard 数据类型错误。最初传的是 `NSURL` 对象（`public.file-url`），但 Ghostty 的服务声明要求 `NSFilenamesPboardType`（文件路径数组）。

**解决：** 改用 `setPropertyList:{"${path}"} forType:"NSFilenamesPboardType"`。

---

### 问题 5：Mac Mini 上始终显示 `⚠ Ghostty /Applications/Ghostty.app not found`

两个独立根源：

- **路径硬编码：** 只检测 `/Applications/Ghostty.app`，不覆盖 `~/Applications` 等自定义安装位置。解决：改用 `mdfind` 按 bundle ID 检测，附路径 fallback。
- **错误信息不区分原因：** 无论是"未安装"还是"调用失败"都显示同一条消息。解决：引入 `ghostty_err` 变量，分别输出 `not installed` / `failed to open`。

---

### 问题 6：`osascript` 命令找不到（exit 127），被 `2>/dev/null` 静默掩盖

**根源：** p-launch 函数在受限 zsh 子 shell 里运行，`/usr/bin` 不在 PATH，裸命令 `osascript` 不可用，脚本静默失败并显示 `failed to open`。

**解决：** 改用全路径 `/usr/bin/osascript`。直接在终端运行时 PATH 完整，所以没有出错——这也是为什么测试一直通过而人工触发失败（见第二部分）。

---

### 问题 7：Ghostty 窗口打开在 `Projects`，而不是 `Projects/harveyz-skill`

**根源：** Ghostty 的服务处理器对 `NSFilenamesPboardType` 里的路径统一做 `dirname`——把收到的路径当文件处理，取其所在目录作为工作目录。Finder 右键空白处触发时放的是"当前目录内的某项"，dirname 之后恰好落在正确位置；直接传项目路径，dirname 就落到了上级目录。

**解决：** 传项目目录内的第一个子项（`/bin/ls -1A "$path" | head -1`），dirname 结果就是项目目录本身。

---

## 二、为什么测试没有暴露实际问题

**根本原因：测试环境和运行环境不一致。**

### 1. PATH 环境不同

测试直接在终端运行 `osascript ...`，PATH 完整，`/usr/bin/osascript` 可以用裸命令找到。但 p-launch 实际运行时是在 zsh 函数体内的子 shell，PATH 被裁剪，裸命令不可用。测试成功，实际失败。

### 2. 错误被 `2>/dev/null` 吞掉

p-launch 里 `osascript 2>/dev/null` 把所有 stderr 丢弃。独立测试没有这个重定向，报错可见。实际运行时 exit 127 完全沉默，只能观察到 `ghostty_ok=false` 的副作用（显示 warning），看不到根本原因。

### 3. 测试断言停在返回值，没有验证实际行为

`NSPerformService` 返回 `true` 就认为成功，没有验证 Ghostty 实际打开在哪个目录。"调用成功"和"结果正确"是两件事：路径传错了，Ghostty 照样返回 `true`、照样开窗口，只是位置不对。

### 结论

测试脚本应在和实际代码完全相同的执行上下文中运行：同一 zsh 子 shell、保留 stderr、验证最终行为而非中间返回值。
