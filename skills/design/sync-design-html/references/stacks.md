# 技术栈检测索引

初始化时读取此文件，确定项目技术栈并加载对应的 `stack-*.md`。

---

## 检测规则（按优先级从高到低）

检测到信号后即停止，取优先级最高的匹配。多平台项目（如 SwiftUI iOS+macOS）在单个 stack 文件中处理。

| 优先级 | 技术栈 | 检测信号 | Reference 文件 |
|--------|--------|---------|----------------|
| 1 | SwiftUI | 存在 `*.xcodeproj` 或 `Package.swift`，且项目中有 `*View.swift` | `stack-swiftui.md` |
| 2 | Flutter | 存在 `pubspec.yaml`，且 `lib/` 下有 `*.dart` | （暂无，手动配置） |
| 3 | Electron | `package.json` 含 `"electron"` 依赖，且存在 main/renderer 目录分离 | `stack-electron.md` |
| 4 | Next.js | 存在 `next.config.js` 或 `next.config.ts`，或 `package.json` 含 `"next"` | `stack-nextjs.md` |
| 5 | Nuxt | 存在 `nuxt.config.ts` / `nuxt.config.js`，或 `package.json` 含 `"nuxt"` | `stack-vue.md` |
| 6 | SvelteKit | 存在 `svelte.config.js`，或 `package.json` 含 `"@sveltejs/kit"` | （暂无，手动配置） |
| 7 | Vue | `package.json` 含 `"vue"`，且存在 `*.vue` 文件 | `stack-vue.md` |
| 8 | React | `package.json` 含 `"react"`，且存在 `*.tsx` 或 `*.jsx` 文件 | `stack-react.md` |
| 9 | Angular | 存在 `angular.json` | （暂无，手动配置） |
| — | 未知 | 以上均不匹配 | 手动配置 |

---

## "暂无 Reference" 的处理

若检测到的技术栈暂无对应 reference 文件，告知用户：

> "检测到技术栈 `<栈名>`，但暂无对应的自动配置预设。将引导您手动填写 platforms 配置。如您日后希望为此栈添加预设，可创建 `references/stack-<name>.md` 并参照已有文件的格式。"

然后手动引导用户填写：
- `uiFilePatterns`：询问"您的 UI 组件/视图文件在哪些目录？常用什么文件扩展名？"
- `designSystemFile`：询问"是否有集中定义颜色、字体等 token 的文件？"

---

## 新增栈的流程

当遇到本索引未覆盖的技术栈时：
1. 手动完成初始化
2. 在此索引表中添加一行（优先级参考相近的栈）
3. 创建 `references/stack-<name>.md`（参照已有格式）

这样下次遇到相同栈时就能自动处理。
