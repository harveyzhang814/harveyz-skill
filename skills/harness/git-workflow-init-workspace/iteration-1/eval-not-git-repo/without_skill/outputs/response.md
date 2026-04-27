# Eval-3 without_skill: 执行记录

## 检测方式（凭直觉）
```
git rev-parse --show-toplevel
→ fatal: not a git repository
→ exit: 128
```

## 处理方式
向用户说明情况并提供两个选项：
- "当前目录 /tmp/gwi-test-nogit 不是 git 仓库。是否执行 git init？"

## 与 with_skill 的对比
两者行为一致：都检测到非 git 仓库，都询问用户，都在用户拒绝后停止。
差异：with_skill 的提问措辞由 skill 规格定义（保持一致性），without_skill 的措辞完全由 agent 即兴发挥。
