"""launcher 必须用 >=3.11 的解释器建 venv，且重建要能真的替换解释器。

实测过的失败链（在 browser-fetch 上复现并修复，本 tool 的 launcher 是同一模板）：
PATH 上 /usr/bin/python3（macOS 自带 3.9.6）排在 homebrew 前面时，launcher 用它
建 venv → `pip install` 因 requires-python >=3.11 失败 → venv 里没有入口脚本。
此后即使用正确的 python3 重跑也修不好：`python3 -m venv` 不带 --clear 不会替换
已存在的解释器，venv 永远停在 3.9。

跟 browser-fetch 的同名测试一样做静态断言：真跑 bootstrap 要建 venv 装依赖，
不能作为测试前置。这里钉住的是"两个分支的 venv 创建都带 --clear、且前面都有
版本校验"这个语法事实；覆盖不到的是校验逻辑在 3.9 上是否真的退出（那要一个
3.9 解释器才能测）。
"""
import re
from pathlib import Path

SH_PATH = Path(__file__).resolve().parents[1] / "sync.sh"
VENV_VARS = ["DEV_VENV", "VENV_DIR"]


def test_version_guard_is_defined_and_checks_3_11():
    src = SH_PATH.read_text("utf-8")
    assert "_require_python()" in src, "缺少 python 版本前置校验函数"
    assert "(3, 11)" in src, "版本门槛不是 3.11，与 pyproject requires-python 不一致"


def test_every_venv_creation_uses_clear_and_is_guarded():
    lines = SH_PATH.read_text("utf-8").splitlines()

    for var in VENV_VARS:
        regex = re.compile(r'^\s*python3 -m venv .*"\$\{%s\}"' % var)
        hits = [i for i, line in enumerate(lines) if regex.match(line)]
        assert len(hits) == 1, f"expected exactly one venv creation for {var}, found {hits!r}"
        idx = hits[0]

        assert "--clear" in lines[idx], (
            f"venv 创建缺 --clear，坏解释器无法被替换: {lines[idx]!r}"
        )
        assert lines[idx - 1].strip() == "_require_python", (
            f"venv 创建前没有版本校验，上一行是 {lines[idx - 1]!r}"
        )


def test_no_unguarded_venv_creation_remains():
    """新增分支时防止漏掉校验：脚本里 venv 创建的总数必须等于已知分支数。"""
    lines = SH_PATH.read_text("utf-8").splitlines()
    creations = [line for line in lines if re.match(r'^\s*python3 -m venv ', line)]
    assert len(creations) == len(VENV_VARS), (
        f"venv 创建点数量变了（{len(creations)}），新分支需同步加校验: {creations!r}"
    )
