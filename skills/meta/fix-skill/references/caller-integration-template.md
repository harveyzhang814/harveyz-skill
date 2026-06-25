# fix-skill 集成模板

其他 skill 在需要自动错误恢复时，将以下片段插入对应步骤之后，替换三个 `<占位符>` 即可。

---

## 使用说明

| 占位符 | 填写内容 |
|--------|----------|
| `<此 skill 名称>` | 本 skill 的 `name` 字段值，如 `extract-url` |
| `<出错文件的绝对路径>` | 根因文件路径（注意：不一定是调用的脚本，可能是其 import 的库或读取的配置文件） |
| `<验证用的参数列表，或 None>` | 修复后重跑脚本的参数列表，如 `["https://example.com", "/tmp/page.html"]`；若目标文件非脚本则填 `None` |

---

## 集成片段

```markdown
### Step N.5：错误恢复（自动）

若上一步返回非零 returncode 或运行时异常，在报告用户前先调用 fix-skill：

提供以下上下文给 fix-skill：
- skill: <此 skill 名称>
- skill_dir: SKILL_DIR
- file: <出错文件的绝对路径>
- error: result.stderr + returncode
- call_args: <验证用的参数列表，或 None>

解析 fix-skill 输出的 `FIX_RESULT:` 行（同时记录 `SESSION_PATH:` 和 `ATTEMPTS:` 供报告使用）：
- `AUTO_RETRY` → 重试上一步（仅一次）；通知用户「已自动修复，共 N 轮，记录见 SESSION_PATH」；再次失败则向用户报告原始错误
- `FAILURE` → 向用户报告原始错误 + 「已尝试 3 轮均失败，已回滚，诊断记录见 SESSION_PATH」
- `FAILURE+RESTORE_FAILED` → 立即告警用户：「修复失败且还原异常，文件状态不可知，backup 已保留，请手动处理，记录见 SESSION_PATH」
```

---

## 根因文件判断指引

`file` 参数填错是最常见的集成错误。判断规则：

- **脚本本身报错**（AttributeError、SyntaxError、NameError）→ 填脚本绝对路径
- **import 链报错**（ImportError、IndentationError 在被 import 的文件）→ 填 traceback 中报错的那个文件，不是调用方脚本
- **配置读取报错**（KeyError、JSONDecodeError、FileNotFoundError 在读配置时）→ 填配置文件路径
- **SKILL.md / Markdown 文件解析错误** → 填该 `.md` 文件绝对路径，`call_args` 填 `None`
