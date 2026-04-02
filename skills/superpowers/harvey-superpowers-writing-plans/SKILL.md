---
name: harvey-superpowers-writing-plans
description: "当有规格说明或需求文档后，将设计拆解为可执行的小任务时使用。每个任务应该是 2-5 分钟可完成的，包含精确文件路径、完整代码和验证步骤。此技能与 brainstorming（生成规格）和 executing-plans（执行计划）配合使用，构成完整的工作流。"
user_invocable: true
version: "1.0.0"
---

# Writing Plans - 实施计划编写

## 概述

将设计文档拆解为详细、可执行的实施计划。假设执行者对代码库零上下文但技能熟练。

**开始时宣布：** "正在使用 writing-plans 技能创建实施计划。"

## 计划文件位置

保存到：`docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`

## 计划结构

### 文件头部（必须）

```markdown
# [功能名称] 实施计划

**目标：** [一句话描述构建内容]

**架构：** [2-3 句话描述方法]

**技术栈：** [关键技术和库]

---
```

### 任务结构

```
### Task N: [组件名称]

**文件：**
- 创建: `exact/path/to/file.py`
- 修改: `exact/path/to/existing.py:123-145`
- 测试: `tests/exact/path/to/test.py`

- [ ] **Step 1: 编写失败的测试**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: 运行测试确认失败**

运行: `pytest tests/path/test.py::test_name -v`
预期: FAIL

- [ ] **Step 3: 编写最小实现**

```python
def function(input):
    return expected
```

- [ ] **Step 4: 运行测试确认通过**

运行: `pytest tests/path/test.py::test_name -v`
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
```

## 任务粒度

**每个步骤 2-5 分钟完成：**
- "编写失败的测试" — 一步
- "运行测试确认失败" — 一步
- "编写最小实现" — 一步
- "运行测试确认通过" — 一步
- "提交" — 一步

## 文件结构规划

在定义任务前，先规划需要创建或修改的文件：
- 每个文件职责清晰
- 文件边界清晰
- 文件应一起修改的放一起
- 遵循现有代码库模式

## 禁止占位符

以下都是计划失败，禁止写入：
- "TBD"、"TODO"、"后续实现"
- "添加适当的错误处理"
- "参考 Task N"（必须重复代码）
- 描述做什么但不展示如何做
- 引用未在任何任务中定义的类型、函数或方法

## 自检清单

完成计划后，用新眼光检查：

### 1. 规格覆盖
浏览规格的每个部分，能否指向实现它的任务？列出任何空白。

### 2. 占位符扫描
搜索：TBD、TODO、"后续"、"类似 Task N" 等模式

### 3. 类型一致性
在后续任务中使用的类型、方法签名、属性名是否与前面定义一致？

## 执行移交

保存计划后，提供执行选项：

**"计划已完成并保存到 `docs/superpowers/plans/<filename>.md`。两个执行选项：**

**1. 子 Agent 驱动（推荐）** — 每个任务派发一个新的 subagent，任务间 review，快速迭代

**2. 内联执行** — 在当前 session 使用 executing-plans 执行，批量执行带检查点

**选择哪个？"**

## 典型计划示例

```markdown
# 用户认证功能 实施计划

**目标：** 添加邮箱+密码用户认证

**架构：** 使用 JWT，无状态认证，密码 bcrypt 哈希

**技术栈：** Python, Flask, PyJWT, bcrypt

---

### Task 1: 用户注册 API

**文件：**
- 创建: `src/api/users.py`
- 修改: `src/models/user.py`
- 测试: `tests/api/test_users.py`

- [ ] **Step 1: 编写注册失败测试**

```python
def test_register_creates_user():
    response = client.post('/api/register', json={
        'email': 'test@example.com',
        'password': 'secure123'
    })
    assert response.status_code == 201
```

- [ ] **Step 2: 运行测试**

...

- [ ] **Step 5: 提交**

```bash
git add src/api/users.py src/models/user.py tests/api/test_users.py
git commit -m "feat: add user registration endpoint"
```
```

## 与其他技能配合

- **brainstorming** — 生成规格文档
- **executing-plans** — 执行计划
- **using-git-worktrees** — 创建隔离工作区
- **systematic-debugging** — 调试问题

## 常见错误

| 错误 | 正确做法 |
|------|----------|
| 任务太大 | 拆分为 2-5 分钟的步骤 |
| 缺少测试代码 | 每个任务都要有完整测试 |
| "参考其他地方" | 重复必要的代码 |
| 未验证一致性 | 自检清单第三项 |
