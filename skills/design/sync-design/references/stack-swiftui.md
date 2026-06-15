# SwiftUI 技术栈指南

适用于 iOS / macOS / visionOS 的 SwiftUI 项目，支持单平台和多平台双目录结构。

---

## 发现命令

```bash
# 发现 iOS UI 文件
find . -type f \( -name "*View.swift" -o -name "*Screen.swift" \) \
  | grep -v ".build" | grep -v "Tests" | grep -v "Preview" | sort

# 发现 macOS UI 文件（常在单独目录）
find . -type f \( -name "*View.swift" -o -name "*Section.swift" -o -name "*Card.swift" \) \
  | grep -v ".build" | grep -v "Tests" | sort

# 发现设计系统文件
find . -type f \( -name "*DesignSystem.swift" -o -name "*Theme.swift" -o -name "*Style.swift" \) \
  | grep -v ".build" | grep -v "Tests" | head -5
```

将发现的文件按目录分组，推导出各平台的目录前缀，生成 patterns。

---

## 平台识别逻辑

SwiftUI 项目通常有两种结构：

**单 target（iOS/macOS 共用）：**
```json
{
  "app": {
    "label": "App",
    "uiFilePatterns": ["<AppModule>/**/*View.swift", "<AppModule>/**/*Screen.swift"],
    "designSystemFile": "<AppModule>/<Name>DesignSystem.swift"
  }
}
```

**双 target（iOS + macOS 分离目录）：**
```json
{
  "ios": {
    "label": "iOS",
    "uiFilePatterns": ["<iOSModule>/**/*View.swift", "<iOSModule>/**/*Screen.swift"],
    "designSystemFile": "<iOSModule>/<Name>DesignSystem.swift"
  },
  "macos": {
    "label": "macOS",
    "uiFilePatterns": ["<macOSModule>/**/*View.swift", "<macOSModule>/**/*Section.swift", "<macOSModule>/**/*Card.swift"],
    "designSystemFile": "<macOSModule>/<Name>DesignSystem.swift"
  }
}
```

检测到 UI 文件后，通过目录路径判断是单 target 还是双 target，告知用户并按需拆分。

---

## 设计系统文件候选

```bash
find . -name "*DesignSystem.swift" -o -name "*Theme.swift" -o -name "*Tokens.swift" \
  | grep -v ".build" | grep -v Tests
```

SwiftUI 的设计 token 通常以 `Color` 扩展、`Font` 扩展、`CGFloat` 常量的形式定义：

```swift
extension Color {
    static let background = Color("Background")
    static let accent = Color("AccentColor")
}
extension CGFloat {
    static let cornerRadius: CGFloat = 12
    static let spacing: CGFloat = 16
}
```

---

## 源文件读取策略

SwiftUI 视图是声明式的，一个文件通常完整描述一个界面。读取时：

1. **读主视图文件**：包含 `body` 的 `View` struct
2. **识别 UI 状态来源**：
   - `@State private var isLoading: Bool` → state 驱动
   - `enum ViewState { case idle, loading, error }` → 枚举驱动
   - 函数参数 / `@Binding` → 外部注入
3. **处理子视图**：若文件中有 `SomeChildView()` 调用且子视图影响视觉，读取对应文件。优先处理项目内部自定义组件；系统组件（`Button`、`List`、`NavigationView`）凭知识推断。
4. **读取设计系统文件**：提取颜色常量名、字体定义、间距值，用于生成 CSS 变量。

---

## HTML 生成注意事项

- SwiftUI 的颜色常量名（如 `Color.accent`）直接映射为 CSS 变量名（`--accent`）
- `cornerRadius`、`padding`、`spacing` 等 `CGFloat` 常量转换为对应 CSS 值（px）
- `HStack`/`VStack`/`ZStack` → `display: flex` + `flex-direction`
- `LazyVGrid`/`LazyHGrid` → `display: grid`
- `.frame(width:height:)` → `width`/`height`，`.frame(maxWidth: .infinity)` → `width: 100%`
- Dark mode（`.colorScheme`）→ `@media (prefers-color-scheme: dark)`
- SF Symbols 用 Unicode 字符或 emoji 近似替代，不引用外部图标库

---

## 常见 Gotchas

- **Preview 文件**：`*_Previews.swift` 或 `PreviewProvider` 不是 UI 源文件，检测时排除
- **SwiftUI Representable**：`UIViewRepresentable` / `NSViewRepresentable` 包装的 UIKit/AppKit 视图，HTML 生成时只还原视觉外观，不还原底层实现
- **条件编译**：`#if os(iOS)` 块注意按平台分别处理
- **Assets Catalog**：颜色可能定义在 `.xcassets` 而非 Swift 代码，读设计系统文件时若颜色名以字符串引用（`Color("Background")`），需在 Assets 中查找实际值
