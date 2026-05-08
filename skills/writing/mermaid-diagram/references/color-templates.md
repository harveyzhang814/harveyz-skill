# Roland Berger 完整配色模板

## 三层产业链 style 模板

直接复制以下 style 块到 flowchart，然后按实际节点 ID 调整：

```
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

## 完整示例：三层产业链板块地图

以下示例综合运用所有规则，可直接复制修改：

```mermaid
flowchart TD
    subgraph UP["上游 算力基础设施"]
        U1["AI芯片 / 晶圆代工<br/>NVIDIA AMD Broadcom<br/>寒武纪 海光"] --- U2["设备 / 存储 HBM<br/>ASML 北方华创<br/>SK海力士 Micron"]
        U3["光模块 / 服务器<br/>中际旭创 新易盛<br/>工业富联 Dell"]  --- U4["IDC / 液冷 / 电力<br/>英维克 Vertiv<br/>阳光电源 VST"]
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

## 极简两层模板

```mermaid
flowchart TD
    subgraph TOP["顶层"]
        T1["节点A"] --- T2["节点B"]
    end
    subgraph BOT["底层"]
        B1["节点C"] --- B2["节点D"]
    end

    TOP -->|"关系"| BOT

    style TOP fill:#00205B,color:#fff,stroke:#1E4A9A
    style BOT fill:#003E96,color:#fff,stroke:#1A6AC4
    style T1 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style T2 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style B1 fill:#0050B8,color:#fff,stroke:#1A6AC4
    style B2 fill:#0050B8,color:#fff,stroke:#1A6AC4
```
