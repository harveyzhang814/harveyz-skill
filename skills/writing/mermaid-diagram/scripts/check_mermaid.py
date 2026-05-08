#!/usr/bin/env python3
"""
Mermaid block validator — checks for known fatal characters and syntax errors.

Usage:
    python check_mermaid.py report.md
    python check_mermaid.py *.md
"""

import re
import sys

RISKY_CHARS = {
    '·': 'middle-dot ·',
    '→': 'arrow →',
    '—': 'em-dash —',
    '“': 'left-quote "',
    '”': 'right-quote "',
}


def check_mermaid_blocks(md_content: str) -> list[str]:
    blocks = re.findall(r'```mermaid\n(.*?)```', md_content, re.DOTALL)
    issues = []

    for i, block in enumerate(blocks, 1):
        dtype = block.strip().split('\n')[0]
        label = f"图{i} [{dtype}]"

        for ch, name in RISKY_CHARS.items():
            if ch in block:
                issues.append(f"{label}: 含禁用字符 {name}")

        if 'flowchart' in dtype or 'graph' in dtype:
            if re.search(r'"[^"]*\\n[^"]*"', block):
                issues.append(f"{label}: 节点标签含 \\n，应改 <br/>")

        if 'flowchart LR' in block:
            issues.append(f"{label}: 使用横向 LR，评估是否需改 TD")

        if 'direction LR' in block and 'stateDiagram' in dtype:
            issues.append(f"{label}: stateDiagram 使用 direction LR，建议改 TB")

        if 'quadrantChart' in dtype and re.search(r'quadrant-\d[^#\n]*/[^#\n]*', block):
            issues.append(f"{label}: quadrant 标签含 /")

        if 'gantt' in dtype and re.search(r'\d{4}-Q\d', block):
            issues.append(f"{label}: gantt 使用 YYYY-Q 格式，应改 YYYY-MM-DD")

        if 'stateDiagram' in dtype:
            lines = block.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('state ') and ' as ' not in line:
                    state_id = line.split()[1].strip('"\'')
                    if any(ord(c) > 127 for c in state_id):
                        issues.append(f"{label}: state ID 含中文，应用 ASCII ID + as 别名")

    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_mermaid.py <file.md> [file2.md ...]")
        sys.exit(1)

    all_clean = True
    for path in sys.argv[1:]:
        with open(path, encoding='utf-8') as f:
            content = f.read()
        issues = check_mermaid_blocks(content)
        if issues:
            all_clean = False
            print(f"\n{path}:")
            for issue in issues:
                print(f"  ❌ {issue}")
        else:
            print(f"{path}: ✅ 通过")

    sys.exit(0 if all_clean else 1)


if __name__ == '__main__':
    main()
