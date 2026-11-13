#!/usr/bin/env python3
"""
MANAGED 块 hash 的唯一实现（Step 4b 校验、Step 6 生成、合并脚本都用它）。
hash = BEGIN 行与 END 行之间（不含这两行）的原文整体去掉首尾空白后的 git blob hash 前 8 位，
等价于 printf '%s' "<内容>" | git hash-object --stdin | cut -c1-8。

用法：
  block_hash.py check <hook 文件>...   逐块输出 OK <块 ID> <hash> 或 MODIFIED <块 ID> <记录> <实际>；
                                        有 MODIFIED 时退出码 1
  block_hash.py stamp <hook 文件>...   只把 (hash:PLACEHOLDER) 换成算出的 hash，已有 hash 的块不动
"""
import hashlib
import re
import sys

PLACEHOLDER = 'PLACEHOLDER'
_BLOCK = re.compile(
    r'^(?P<begin>[ \t]*# --- BEGIN MANAGED: (?P<id>\S+) \(hash:(?P<hash>[^)]*)\) ---)\n'
    r'(?P<body>.*?)'
    r'^[ \t]*# --- END MANAGED: (?P=id) ---$',
    re.M | re.S)


def block_hash(content):
    data = content.strip().encode('utf-8')
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()[:8]


def check(text):
    """返回 [(块 ID, 记录的 hash, 实际 hash, 'OK'|'MODIFIED')]，按出现顺序。"""
    out = []
    for m in _BLOCK.finditer(text):
        actual = block_hash(m.group('body'))
        out.append((m.group('id'), m.group('hash'), actual,
                    'OK' if m.group('hash') == actual else 'MODIFIED'))
    return out


def stamp(text):
    def fill(m):
        if m.group('hash') != PLACEHOLDER:
            return m.group(0)
        return m.group(0).replace(f'(hash:{PLACEHOLDER})', f'(hash:{block_hash(m.group("body"))})', 1)
    return _BLOCK.sub(fill, text)


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('check', 'stamp'):
        print('用法：block_hash.py check|stamp <hook 文件>...', file=sys.stderr)
        sys.exit(2)
    mode, files, modified = sys.argv[1], sys.argv[2:], False
    for path in files:
        with open(path, encoding='utf-8', newline='') as f:
            text = f.read()
        if mode == 'stamp':
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(stamp(text))
            continue
        for bid, recorded, actual, status in check(text):
            prefix = f'{path} ' if len(files) > 1 else ''
            if status == 'OK':
                print(f'{prefix}OK {bid} {actual}')
            else:
                modified = True
                print(f'{prefix}MODIFIED {bid} {recorded} {actual}')
    sys.exit(1 if modified else 0)
