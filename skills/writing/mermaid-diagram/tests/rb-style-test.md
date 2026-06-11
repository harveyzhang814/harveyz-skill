# Mermaid 配色测试 — Roland Berger 风格

用于验证 RB 深海军蓝配色在各图类型下的视觉效果。

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

    style UP   fill:#00205B,color:#fff,stroke:#1E4A9A
    style MID  fill:#003E96,color:#fff,stroke:#1A6AC4
    style DOWN fill:#1E5C9E,color:#fff,stroke:#3A8ACC
    style U1 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style U2 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style U3 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style U4 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style M1 fill:#0050B8,color:#fff,stroke:#1A6AC4
    style M2 fill:#0050B8,color:#fff,stroke:#1A6AC4
    style D1 fill:#2A6EAE,color:#fff,stroke:#3A8ACC
    style D2 fill:#2A6EAE,color:#fff,stroke:#3A8ACC
    style D3 fill:#2A6EAE,color:#fff,stroke:#3A8ACC
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

    style ZONE fill:#00205B,color:#fff,stroke:#1E4A9A
    style A fill:#1A5E3A,color:#fff,stroke:#2A7E50
    style B fill:#003E96,color:#fff,stroke:#1A6AC4
    style C fill:#7B1010,color:#fff,stroke:#B52020
```

---

## 3. sequenceDiagram — 系统调用时序

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
    classDef opportunity fill:#1A5E3A,stroke:#2A7E50,color:#fff
    classDef hold        fill:#003E96,stroke:#1A6AC4,color:#fff
    classDef danger      fill:#7B1010,stroke:#B52020,color:#fff

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

## 5. quadrantChart — 2x2 机会矩阵

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

## 6. timeline — 里程碑时间轴

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

## 7. gantt — 项目计划

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
