---
date: {{YYYYMMDDTHHMMSS}}
skill: {{skill}}
file: {{file_relative_path}}
backup: {{backup_path}}
status: in_progress
---

## 原始错误

{{error_output}}

---

## 第 1 轮

**假设：** {{hypothesis}}

**改动：**
```diff
{{diff -u backup_path file 输出}}
```

**验证结果：** 通过 / 失败 — {{verify_detail}}

**失败原因：** {{若失败填写，说明为何假设不成立，为下一轮提供方向}}

---

<!-- 第 2、3 轮格式同上，append 在此处 -->

---

## 最终结果

状态：{{成功（第 N 轮）| 失败（3 轮均未解决）| 失败且还原异常}}
