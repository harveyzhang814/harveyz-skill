# flowchart 详细规则与布局技法

## 基本语法

```yaml
方向:    TD 优先；LR 仅用于天然横向内容
节点:    ["标签"] 格式，标签内用 <br/> 换行
子图:    subgraph ID["显示名"] ... end
颜色:    style NodeID fill:#xxx,color:#fff,stroke:#xxx
边:      --> 有向；--- 无向（用于矩阵配对）；-.-> 虚线
禁止:    emoji, ·, →, direction TB in subgraph
```

## 矩阵布局（subgraph 内 2 列网格）

当 subgraph 内节点 ≥ 4 个时，用 `---`（无向边）配对强制 2 列布局：

```mermaid
flowchart TD
    subgraph LAYER["层级名称"]
        A["节点A"] --- B["节点B"]
        C["节点C"] --- D["节点D"]
        E["单数节点（居中）"]
    end
```

- `---` 产生细线连接，视觉上表示"同组"
- 奇数节点放最后一行，独立居中
- 严禁 4 个或以上节点堆在同一无连接行（会横向撑满）

## subgraph 间箭头

```mermaid
flowchart TD
    subgraph UP["上游"] end
    subgraph MID["中游"] end
    subgraph DOWN["下游"] end

    UP -->|"标签"| MID
    MID -->|"标签"| DOWN
```

- subgraph ID 可直接作为箭头端点（Mermaid v9+）
- 层间箭头标签保持**单行短语**，不用 `\n`

## 多行节点标签

```
✅ A["第一行<br/>第二行<br/>第三行"]
❌ A["第一行\n第二行\n第三行"]   ← \n 在部分渲染器失效
```

---

## 完整示例：三层产业链板块地图

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
