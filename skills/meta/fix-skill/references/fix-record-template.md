---
date: {{YYYYMMDDTHHMMSS}}
skill: {{skill}}
fix_target: {{script|skill_logic}}
file: {{file_relative_path}}
status: {{AUTO_RETRY|NEEDS_MANUAL_RETRY|FAILURE}}
---

## 触发错误

```
{{error_output}}
```

## 根因

{{root_cause_one_line}}

## 修复内容

```diff
{{diff_or_empty_on_failure}}
```

## 验证

{{verify_detail}}

## 备份路径

{{backup_path}}
