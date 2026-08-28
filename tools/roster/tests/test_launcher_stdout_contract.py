"""roster 的 stdout 有 JSON 契约，bootstrap 输出必须走 stderr。

sync-xtimeline / sync-ytchannel 的 roster_client.py 对 roster 的 stdout 做
`json.loads`（registry channels、state get）。roster.sh 的 bootstrap 分支会跑
`python3 -m venv` 和 `pip install`，它们默认往 stdout 写安装信息；一旦在
`hskill install --tool roster` 之后的第一次调用触发，stdout 就是"安装横幅 + JSON"，
`json.loads` 抛 JSONDecodeError —— 而 roster_client 只捕获 CalledProcessError 之类，
这个异常会直接穿透。browser-fetch 上已经踩过同一个坑。

与 browser-fetch 的同名测试一样做静态断言：钉住"命令末尾有没有 >&2"这个语法事实，
覆盖不到重定向语义是否真的让 stdout 干净（那要真跑一次 bootstrap）。
"""
import re
from pathlib import Path

SH_PATH = Path(__file__).resolve().parents[1] / "roster.sh"

# 四条会往 stdout 写安装信息的 bootstrap 命令，dev 分支两条 + installed 分支两条。
BOOTSTRAP_LINE_PATTERNS = [
    r'^\s*python3 -m venv --clear "\$\{DEV_VENV\}".*$',
    r'^\s*"\$\{DEV_VENV\}/bin/pip" install .*$',
    r'^\s*python3 -m venv --clear "\$\{VENV_DIR\}".*$',
    r'^\s*"\$\{VENV_DIR\}/bin/pip" install .*$',
]


def test_all_bootstrap_commands_redirect_stdout_to_stderr():
    lines = SH_PATH.read_text("utf-8").splitlines()

    for pattern in BOOTSTRAP_LINE_PATTERNS:
        regex = re.compile(pattern)
        hits = [line for line in lines if regex.match(line)]
        assert len(hits) == 1, (
            f"expected exactly one bootstrap line matching {pattern!r}, found {hits!r}"
        )
        assert hits[0].rstrip().endswith(">&2"), (
            f"bootstrap command not redirected to stderr, will pollute roster JSON stdout: {hits[0]!r}"
        )
