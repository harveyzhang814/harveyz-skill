# Mermaid 配色测试 — Bain & Company 风格

用于验证 Bain 近黑 subgraph + Bain Red 节点配色在各图类型下的视觉效果。
主题文件：`themes/bain.json`

---

## 1. flowchart TD — 三层产业链（核心场景）

```mermaid
flowchart TD
    subgraph UP["上游 算力基础设施"]
        U1["AI芯片 / 晶圆代工<br/>NVIDIA AMD Broadcom<br/>寒武纪 海光"] --- U2["设备 / 存储 HBM<br/>ASML 北方华创<br/>SK海力士 Micron"]
        U3["光模块 / 服务器<br/>中际旭创 新易盛<br/>工业富联 Dell"]  --- U4["IDC / 液冷 / 电力<br/>英维克 Vertiv<br/>阳光电源"]
    end

    subgraph MID["中游 模型与平台"]
        M1["大模型<br/>GPT Gemini 通义 DeepSeek"] --- M2["云平台<br/>Azure AWS 阿里云 腾讯云"]
    end

    subgraph DOWN["下游 应用与端侧"]
        D1["企业SaaS<br/>Palantir ServiceNow<br/>金山办公"] --- D2["AI编程 / 搜索<br/>Copilot Cursor Google"]
        D3["端侧硬件<br/>机器人 智驾 AI眼镜"]
    end

    UP -->|"卖铲子"| MID
    MID -->|"挖金子"| DOWN

    style UP   fill:#E8E8E8,color:#212427,stroke:#C8C8C8
    style MID  fill:#F0F0F0,color:#212427,stroke:#D0D0D0
    style DOWN fill:#F5F5F5,color:#212427,stroke:#D8D8D8
    style U1 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
    style U2 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
    style U3 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
    style U4 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
    style M1 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
    style M2 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
    style D1 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
    style D2 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
    style D3 fill:#FFFFFF,color:#212427,stroke:#BBBBBB
```

---

## 2. flowchart TD — 语义辅助色（风险信号）

```mermaid
flowchart TD
    subgraph ZONE["投资信号分区"]
        A["买入区<br/>估值低位 + 情绪修复"] --- B["持有区<br/>趋势延续 观察为主"]
        C["规避区<br/>高估值 + 衰退信号"]
    end

    A -->|"催化剂触发"| B
    B -->|"风险升温"| C
    C -->|"超跌反弹"| A

    style ZONE fill:#E8E8E8,color:#212427,stroke:#C8C8C8
    style A fill:#E87722,color:#fff,stroke:#BA5F1B
    style B fill:#666666,color:#fff,stroke:#525252
    style C fill:#CC0000,color:#fff,stroke:#A30000
```

---

## 3. sequenceDiagram — 系统调用时序（库默认色）

```mermaid
sequenceDiagram
    participant U as 用户
    participant C as Claude Code
    participant S as doc-forge
    participant P as Playwright

    U->>C: 将 report.md 转为 PDF
    C->>S: python3 md_to_pdf.py report.md
    S->>S: 提取 Mermaid 块
    S->>S: Markdown 转 HTML
    S->>P: page.goto(file:///tmp/...)
    activate P
    P->>P: 加载 mermaid.js
    P->>P: 渲染 SVG 图表
    P-->>S: SVG 渲染完成
    deactivate P
    S->>P: page.pdf(format="A4")
    P-->>S: PDF 字节流
    S-->>U: Saved: report.pdf
```

---

## 4. stateDiagram-v2 — 估值周期状态机

```mermaid
stateDiagram-v2
    direction TB
    classDef opportunity fill:#E87722,stroke:#BA5F1B,color:#fff
    classDef hold        fill:#666666,stroke:#525252,color:#fff
    classDef danger      fill:#CC0000,stroke:#A30000,color:#fff

    state "低估值区<br/>买入信号" as BUY
    state "合理区间<br/>持有观察" as HOLD
    state "高估值区<br/>规避风险" as AVOID
    state "超跌反弹<br/>博弈机会" as REBOUND

    [*] --> BUY
    BUY --> HOLD: 估值修复
    HOLD --> AVOID: 泡沫积累
    AVOID --> REBOUND: 情绪崩塌
    REBOUND --> BUY: 价值回归
    HOLD --> BUY: 回调企稳

    class BUY opportunity
    class HOLD hold
    class AVOID danger
    class REBOUND hold
```

---

## 5. quadrantChart — 2x2 机会矩阵（库默认色）

```mermaid
quadrantChart
    title 行业配置矩阵（确定性 vs 弹性）
    x-axis 低弹性 --> 高弹性
    y-axis 低确定性 --> 高确定性
    quadrant-1 核心配置
    quadrant-2 主题博弈
    quadrant-3 规避
    quadrant-4 观察
    AI算力: [0.85, 0.80]
    消费复苏: [0.60, 0.65]
    新能源: [0.70, 0.45]
    地产链: [0.40, 0.30]
    医药: [0.35, 0.60]
    红利资产: [0.20, 0.75]
```

---

## 6. timeline — 里程碑时间轴（库默认色）

```mermaid
timeline
    title AI 大模型发展里程碑
    2017 : Transformer 架构发布
    2020 : GPT-3 发布<br/>涌现能力首次展现
    2022 : ChatGPT 发布<br/>大模型商业化元年
    2023 : GPT-4 多模态<br/>Claude 2 / Gemini
    2024 : o1 推理模型<br/>端侧模型爆发
    2025 : DeepSeek R2<br/>Agents 规模化落地
```

---

## 7. gantt — 项目计划（库默认色）

```mermaid
gantt
    title 报告生产排期
    dateFormat  YYYY-MM-DD
    section 研究阶段
    数据收集       :a1, 2026-06-01, 5d
    行业访谈       :a2, after a1, 3d
    section 分析阶段
    框架搭建       :b1, after a2, 2d
    模型分析       :b2, after b1, 4d
    section 输出阶段
    报告撰写       :c1, after b2, 3d
    内审修改       :c2, after c1, 2d
    客户提交       :milestone, after c2, 0d
```
