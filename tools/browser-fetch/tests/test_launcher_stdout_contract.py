"""CLI 契约：stdout 只能有一行 compact JSON，人类可读信息一律走 stderr。

browser-fetch.sh 有两个 bootstrap 分支（dev venv / installed venv），各自跑
`python3 -m venv`、`pip install`、`playwright install chromium` 三条命令。这三条
命令默认往 stdout 写下载/安装横幅，一旦触发就会污染 CLI 的 JSON 输出，导致所有
消费端 `json.loads(proc.stdout)` 抛 JSONDecodeError（详见修复项 1 报告）。

真跑一次 bootstrap 会触发 `playwright install chromium` 的真实下载（几百 MB），
不能作为测试前置条件，所以这里改为对脚本源码做静态断言：确认两个分支里的三条
bootstrap 命令都显式重定向到 stderr（`>&2`）。这个测试钉住的是"命令末尾有没有
>&2"这个语法事实，覆盖不到的是：重定向语义是否真的让 stdout 干净（要覆盖那个，
只能真的跑一次 bootstrap，而这需要真实网络下载，权衡后放弃）。
"""
import re
from pathlib import Path

SH_PATH = Path(__file__).resolve().parents[1] / "browser-fetch.sh"

# 六条会往 stdout 写安装信息的 bootstrap 命令，dev 分支三条 + installed 分支三条。
BOOTSTRAP_LINE_PATTERNS = [
    r'^\s*python3 -m venv "\$\{DEV_VENV\}".*$',
    r'^\s*"\$\{DEV_VENV\}/bin/pip" install .*$',
    r'^\s*"\$\{DEV_VENV\}/bin/python3" -m playwright install chromium.*$',
    r'^\s*python3 -m venv "\$\{VENV_DIR\}".*$',
    r'^\s*"\$\{VENV_DIR\}/bin/pip" install .*$',
    r'^\s*"\$\{VENV_DIR\}/bin/python3" -m playwright install chromium.*$',
]


def test_all_bootstrap_commands_redirect_stdout_to_stderr():
    src = SH_PATH.read_text("utf-8")
    lines = src.splitlines()

    matched_count = 0
    for pattern in BOOTSTRAP_LINE_PATTERNS:
        regex = re.compile(pattern)
        hits = [line for line in lines if regex.match(line)]
        assert len(hits) == 1, (
            f"expected exactly one bootstrap line matching {pattern!r}, found {hits!r}"
        )
        matched_count += 1
        line = hits[0]
        assert line.rstrip().endswith(">&2"), (
            f"bootstrap command not redirected to stderr, will pollute CLI stdout: {line!r}"
        )

    assert matched_count == len(BOOTSTRAP_LINE_PATTERNS)
