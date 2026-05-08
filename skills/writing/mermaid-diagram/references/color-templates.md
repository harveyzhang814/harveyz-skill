# Roland Berger 配色标准

## 色板总览

| 角色 | 用途 | fill | stroke |
|------|------|------|--------|
| **subgraph 上游** | 最底层 / 最重要 / 上游容器 | `#00205B` | `#1E4A9A` |
| **subgraph 中游** | 中间层 / 平台层容器 | `#003E96` | `#1A6AC4` |
| **subgraph 下游** | 应用层 / 端侧容器 | `#1E5C9E` | `#3A8ACC` |
| **节点 上游** | 上游 subgraph 内的节点 | `#0A2E7A` | `#1E4A9A` |
| **节点 中游** | 中游 subgraph 内的节点 | `#0050B8` | `#1A6AC4` |
| **节点 下游** | 下游 subgraph 内的节点 | `#2A6EAE` | `#3A8ACC` |

**规律**：同层的 subgraph 比其内节点颜色**深 10–15%**，形成层次感。文字颜色一律 `color:#fff`。

---

## 语义辅助色

用于传达风险信号，叠加在主色体系之上：

| 语义 | 场景 | fill | stroke |
|------|------|------|--------|
| 预警 / 高风险 / 规避 | 危险区域、卖出信号 | `#7B1010` | `#B52020` |
| 机会 / 买入 / 低风险 | 买入区域、推荐配置 | `#1A5E3A` | `#2A7E50` |
| 等待 / 持有 / 中性 | 观察区域、中性态度 | `#003E96` | `#1A6AC4` |
| 投机 / 主题 / 高波动 | 高风险高回报区域 | `#2E0078` | `#5A20A0` |
| 价值 / 配置 / 稳健 | 价值投资区域 | `#004060` | `#1A5E80` |

---

## 使用规则

1. **深色背景必须加白字**：任何 `fill` 颜色深于 `#4A4A4A`，必须加 `color:#fff`
2. **单图最多 3 种主色**：不要同时使用上游/中游/下游/语义色全部五组
3. **容器比节点深**：subgraph 的 fill 必须比其内节点的 fill 深，否则层次感消失
4. **sequenceDiagram / gantt / timeline 不着色**：这些类型使用库默认颜色，不应用 RB 色板
5. **语义色优先级低于主色**：只在需要传达明确风险信号时才使用语义辅助色

---

## style 片段速查

三层结构（直接复制，按实际节点 ID 替换）：

```
style UP   fill:#00205B,color:#fff,stroke:#1E4A9A
style MID  fill:#003E96,color:#fff,stroke:#1A6AC4
style DOWN fill:#1E5C9E,color:#fff,stroke:#3A8ACC

style U1 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
style M1 fill:#0050B8,color:#fff,stroke:#1A6AC4
style D1 fill:#2A6EAE,color:#fff,stroke:#3A8ACC
```

两层结构：

```
style TOP fill:#00205B,color:#fff,stroke:#1E4A9A
style BOT fill:#003E96,color:#fff,stroke:#1A6AC4

style T1 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
style B1 fill:#0050B8,color:#fff,stroke:#1A6AC4
```

语义色（按需挑选）：

```
style X fill:#7B1010,color:#fff,stroke:#B52020   /* 预警红 */
style X fill:#1A5E3A,color:#fff,stroke:#2A7E50   /* 机会绿 */
style X fill:#2E0078,color:#fff,stroke:#5A20A0   /* 投机紫 */
style X fill:#004060,color:#fff,stroke:#1A5E80   /* 价值蓝绿 */
```

> 含真实内容的完整产业链示例 → `references/flowchart.md`
