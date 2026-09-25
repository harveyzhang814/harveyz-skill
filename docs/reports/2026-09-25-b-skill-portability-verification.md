# B 类 Skill 平台适配验证

日期：2026-09-25。范围：三个 feed sync、`question-me`、`rephrase`、`init-project`、`runby-opencode` 的共享表述、路径引用和模式前提。未对七个宿主做端到端运行，不声称运行时全面兼容。

| 检查 | 结果 |
|---|---|
| `node --test tests/skill-portability.test.mjs tests/templates.test.mjs` | 22 通过，0 失败 |
| 三个 feed skill 的 `python3 -m pytest -q .../tests`（逐目录） | 72、71、90 项分别通过 |
| `node --test tests/mcp.test.mjs tests/templates.test.mjs tests/skill-portability.test.mjs tests/harness/*.test.mjs` | 351 项：344 通过、7 跳过、0 失败 |
| `bats --negative-filter 'hook e2e: real LLM' tests/` | 166 通过、0 失败；显式排除两个依赖外部 Claude CLI 的用例 |
| `npm pack --dry-run --ignore-scripts --json` | 七项 `SKILL.md`、三个 Claude 适配文件以及 `init-project` 的 schema、README、AGENTS 骨架均在包清单中 |
| `git diff --check` | 通过 |

完整 `npm test` **未通过，未完成全套验证**。实施前的基线运行：`clip-url/tests/test_chrome_profile_config.py::test_get_reports_not_configured_initially` 超时；`tools/browser-fetch` 的 `test_eval_reads_js_from_file` 和 `test_fetch_article_thin_retry_uses_persisted_default_when_omitted` 在访问 `https://example.com` 时 `Page.goto` 30 秒超时。后续运行因外部浏览器测试耗时而中断。实施后的运行停在 Bats `hook e2e: real LLM detects semantic similarity between auth branches`，其 `claude -p` 子进程超过两分钟无输出；人工中断后 Bats 报告第 37 项状态 130，168 项中仅执行到第 37 项。该用例不在本批变更范围，不能记为通过或判定为本批回归。上述各问题需在独立环境稳定后复跑。

三个 feed skill 的 Python 测试不能在一次 pytest 命令中合并收集：不同目录里存在同名 `test_*.py` 模块，会触发 import file mismatch。按仓库现有逐目录方式执行后均通过；未改测试或删除缓存。
