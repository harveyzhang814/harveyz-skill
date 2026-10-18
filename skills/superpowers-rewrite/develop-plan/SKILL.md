---
name: develop-plan
description: Use after init-spec approves a software Spec, or when other clear requirements need a multi-step implementation plan before coding
user_invocable: true
version: 0.1.11
---

# 制定实施计划

## 作用（说明）

将已批准的 Spec 或明确需求转为实施计划，供不熟悉代码库的工程师执行。

## 指令

记录已确定的文件、接口、取值、测试和任务依赖；将实现选择留给实施者。遵循 DRY、YAGNI、TDD，按任务频繁提交。

### 1. 核对输入与边界

**开始时声明：**“我正在使用 develop-plan 技能制定实施计划。”

**输入：**接续 `init-spec` 时，读取已批准的 Spec，核对版本、范围和未决事项，沿用其中已确定的答案；独立调用时，直接依据用户给出的明确需求，无需查找 Spec。

**决定边界：**自行确定不改变已定结果的文件拆分、接口和测试；若输入缺口或冲突的不同答案会改变需求、验收结果或关键方案，说明影响：接续 `init-spec` 时返回其审查阶段，独立调用时请用户澄清，待确定后继续。

**工作区：**遵循项目的 Git 规则，沿用并核对已有工作树；需要新建时按项目规则准备，没有专门规则时在实施前使用 `superpowers:using-git-worktrees`。

**范围：**输入包含多个独立子系统时，每个子系统编写一份能独立产出可运行、可测试软件的计划；若拆分改变已定范围，按决定边界处理。

### 2. 拆解方案

**文件：**

先列出拟创建或修改的文件及其职责，再据此划分任务。优先选用职责单一、接口明确、便于理解的文件，并放在与其共同变化的代码附近；遵循现有结构，修改大文件时可按需计划拆分。

**任务：**

每项任务应有自己的测试周期和可独立审查的交付物；只有审查者能够批准一项、拒绝相邻一项时才拆分任务。将准备、配置、脚手架和文档并入所服务的交付任务。

优先交付可验证的用户行为或系统能力，不按数据库、API、UI 机械分层；基础设施或机械重构需要单独成任务时，写明它解除的阻碍和自身验证结果。

**步骤：**

每一步只写一个具有可检查结果的动作，例如编写失败测试、确认失败、实现最少代码、确认通过、提交；具体格式见任务模板。

### 3. 编写计划

**保存位置：**
- 接续 `init-spec`：与 Spec 同目录；默认路径为 `.hskill/spec/YYYY-MM-DD-<topic>/YYYY-MM-DD-<topic>-plan.md`，日期、topic 及同名序号沿用 Spec，修订沿用原路径。用户另有命名约定时遵循其约定。
- 独立调用：直接保存到项目根目录下的 `.hskill/spec/YYYY-MM-DD-<topic>/YYYY-MM-DD-<topic>-plan.md`；日期取首次建档日，topic 根据任务命名，独立任务同名时加序号，修订沿用原路径。

#### 文档开头

每份计划使用以下开头，字段名保持英文。接续 `init-spec` 时填写 `Spec` 和 `Spec Version and Scope`，删除 `Requirements`；独立调用时填写 `Requirements`，删除两个 `Spec` 字段。将需求中的全局约束按确切取值逐项写入，并应用于所有任务；从需求隐含、尚无测试覆盖的输入或故障模式中选最多五项，逐项写明预期行为，并把对应测试放入负责的任务。新增预期行为若越过决定边界，按上述规则处理。

```markdown
# [功能名称] 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐项实施；用 `- [ ]` 跟踪步骤。

**Goal:** [用一句话描述将构建什么]

**Architecture:** [用 2–3 句话描述方案]

**Tech Stack:** [关键技术/库]

**Spec:** [接续 init-spec：已批准 Spec 的路径；与计划一同交付]

**Spec Version and Scope:** [接续 init-spec：已批准的版本和范围]

**Requirements:** [独立调用：用户需求摘要及其来源]

## Global Constraints

[最低版本、依赖限制、命名和文案、平台要求等；每行一项]

## Review Focus

[输入或故障模式 → 预期行为；最可能发生的在前，每行一项]

---
```

#### 任务模板

任务标题必须保留 `Task N`，供两个执行技能提取任务；每项任务最后的 `Run` 命令应覆盖该任务的全部测试。

````markdown
### Task N: [可验证的交付成果]

**Prerequisites:** [无；或必须先完成的任务编号]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Interfaces:**
- Consumes: [其他任务的产出及确切签名]
- Produces: [后续任务依赖的名称、参数和返回类型]

- [ ] **Step 1: 编写失败测试**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL，提示 "function not defined"

- [ ] **Step 3: 在 `exact/path/to/file.py` 中实现 `function(input: InputType) -> ResultType`**

Approach: [仅在签名和测试未确定方案时填写关键库函数或数据结构]

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `pytest tests/path/test.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

#### 步骤内容

只写消除歧义所需的信息：

- **测试：**以代码写明名称、断言和输入中确定的取值。
- **实现：**写明文件、签名和输入中确定的取值；仅当签名与测试不足以确定算法，或输入固定了文案时，才写实现片段。
- **验证：**写明命令和预期输出。
- **任务引用：**通过“接口”区块引用，不重复代码；只将确实阻止开工的任务列为前置任务。

删除未作决定的占位语，如“TBD”“处理边界情况”；用签名和测试代替可由实施者写出的函数体。

### 4. 自查

写完后亲自对照输入检查，并直接修复发现的问题：

**1. 需求覆盖：**每项要求是否有对应任务？补齐缺口。

**2. 步骤：**每步是否只有一个明确动作和可检查结果？删除空话及不必要的函数体。

**3. 接口一致性：**跨任务使用的类型、签名和属性名是否一致？

**4. 任务依赖：**前置任务是否存在且确实阻塞开工？是否有环？可同时开工的任务是否争用文件或未定接口？调整冲突任务的边界或顺序；无需强制并行。

**5. 审查重点：**所列风险是否各有归属任务和测试？没有遗漏时明确写“无”，并检查新增行为是否越过决定边界。

**6. 篇幅：**计划是否主要由代码块组成？接续 `init-spec` 时，是否比 Spec 长数倍？用签名、测试名称和断言替代实现代码。

### 5. 执行交接

保存并自查后，提供计划链接，请用户确认计划符合意图，并在审阅完成前等待实施。若尚未指定执行方式，说明两种选择，结合任务依赖、数量和出错代价推荐其一，请用户决定；已有选择则沿用。

- **子代理驱动（Subagent-driven）**——每项任务由新子代理实施并独立审查，最后审查整个分支；审查更密集，上下文成本更高。
- **原生执行（Native）**——当前会话逐项实施，最后独立审查整个分支；上下文成本更低。

确认后，子代理驱动使用 `superpowers:subagent-driven-development`；原生执行使用 `superpowers:executing-plans`。
