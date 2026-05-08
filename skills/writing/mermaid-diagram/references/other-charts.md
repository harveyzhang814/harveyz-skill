# quadrantChart / mindmap 详细规则

## quadrantChart

```yaml
quadrant标签: 不含 / & → 等字符
              ❌ quadrant-3 减仓/规避
              ✅ quadrant-3 减仓规避
点标签:       "标签名: [x, y]"，x/y 在 0.0–1.0 之间
              中文标签可用，但不能有冒号之外的特殊字符
```

示例：

```mermaid
quadrantChart
    title 板块配置矩阵
    x-axis 确定性低 --> 确定性高
    y-axis 弹性低 --> 弹性高
    quadrant-1 重仓配置
    quadrant-2 高风险高回报
    quadrant-3 规避区域
    quadrant-4 低配持有
    AI算力: [0.8, 0.9]
    新能源: [0.5, 0.6]
    消费: [0.3, 0.3]
```

---

## mindmap

```yaml
缩进:    严格 2 空格/级，不混用 tab
节点文本: 纯文本，不含 : ( ) [ ] { } 等 Mermaid 控制字符
root:    root((显示文本)) 圆形；root[文本] 方形
分隔符:  同级用空格，不用 · / → 等
```

示例：

```mermaid
mindmap
  root((AI产业))
    算力层
      芯片
      存储
      服务器
    模型层
      基础模型
      微调模型
    应用层
      企业软件
      消费应用
```
