import io
import json

from roster.__main__ import main

RUN = "2026-08-26T09:14:00+08:00"


def _run(capsys, *argv) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out.strip(), captured.err.strip()


def test_registry_add(data_dir, capsys):
    code, out, _ = _run(capsys, "registry", "add", "https://x.com/karpathy")
    assert code == 0
    assert out == "OK karpathy x:karpathy"


def test_registry_add_persists_to_disk(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    reg = json.loads((data_dir / "registry.json").read_text(encoding="utf-8"))
    assert reg["creators"][0]["id"] == "karpathy"


def test_registry_add_bad_url_exits_1(data_dir, capsys):
    code, _, err = _run(capsys, "registry", "add", "https://example.com/x")
    assert code == 1
    assert "不是可识别的渠道 URL" in err


def test_registry_add_duplicate_exits_1(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    code, _, err = _run(capsys, "registry", "add", "https://x.com/karpathy")
    assert code == 1
    assert "已在名册" in err


def test_registry_list_empty(data_dir, capsys):
    code, out, _ = _run(capsys, "registry", "list")
    assert (code, out) == (0, "EMPTY")


def test_registry_list_shows_placeholder_and_channel(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _, out, _ = _run(capsys, "registry", "list")
    assert "karpathy" in out
    assert "placeholder" in out
    assert "x:karpathy" in out


def test_registry_list_shows_cursor_from_state(data_dir, capsys):
    """list 跨组读 state 是允许的——读跨组可以，写不行。"""
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "state", "set", "x:karpathy",
         "--type", "last_seen_id", "--value-json", '"123"', "--run-time", RUN)
    _, out, _ = _run(capsys, "registry", "list")
    assert "123" in out


def test_registry_channels_outputs_json(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "registry", "add", "https://youtube.com/@AK")
    code, out, _ = _run(capsys, "registry", "channels", "--platform", "x")
    assert code == 0
    assert json.loads(out) == [{
        "creator_id": "karpathy", "platform": "x",
        "handle": "karpathy", "url": "https://x.com/karpathy",
    }]


def test_registry_channels_empty_is_empty_json_array(data_dir, capsys):
    _, out, _ = _run(capsys, "registry", "channels", "--platform", "x")
    assert json.loads(out) == []


def test_registry_rename(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    code, out, _ = _run(capsys, "registry", "rename", "karpathy", "Andrej Karpathy")
    assert (code, out) == (0, "OK")
    _, listing, _ = _run(capsys, "registry", "list")
    assert "Andrej Karpathy" in listing
    assert "placeholder" not in listing


def test_registry_merge_combines_and_reports(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "registry", "add", "https://youtube.com/@AndrejKarpathy")
    code, out, _ = _run(capsys, "registry", "merge", "karpathy", "andrejkarpathy")
    assert code == 0
    assert out == "OK merged andrejkarpathy into karpathy"
    _, listing, _ = _run(capsys, "registry", "list")
    assert "x:karpathy" in listing and "youtube:AndrejKarpathy" in listing


def test_registry_merge_also_merges_profiles(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "registry", "add", "https://youtube.com/@AndrejKarpathy")
    _run(capsys, "profile", "append", "andrejkarpathy",
         "--date", "2026-08-26", "--source", "视频标题", "--body", "b 的观察")
    _run(capsys, "registry", "merge", "karpathy", "andrejkarpathy")
    _, out, _ = _run(capsys, "profile", "show", "karpathy")
    assert "b 的观察" in out


def test_registry_remove_creator_archives_profile(data_dir, capsys):
    """删人绝不删画像——那是唯一不可重建的数据。"""
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "profile", "append", "karpathy",
         "--date", "2026-08-26", "--source", "推文", "--body", "宝贵的观察")
    code, out, _ = _run(capsys, "registry", "remove", "karpathy")
    assert code == 0
    assert "archived" in out
    archived = data_dir / "profiles" / "archived" / "karpathy.md"
    assert "宝贵的观察" in archived.read_text(encoding="utf-8")


def test_registry_remove_creator_drops_its_state(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "state", "set", "x:karpathy",
         "--type", "last_seen_id", "--value-json", '"123"', "--run-time", RUN)
    _run(capsys, "registry", "remove", "karpathy")
    _, out, _ = _run(capsys, "state", "get", "x:karpathy")
    assert json.loads(out) is None


def test_registry_remove_channel_only(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    code, out, _ = _run(capsys, "registry", "remove", "x:karpathy")
    assert (code, out) == (0, "OK removed x:karpathy")
    _, listing, _ = _run(capsys, "registry", "list")
    assert "karpathy" in listing          # 人还在
    assert "x:karpathy" not in listing    # 渠道没了


def test_state_get_before_first_fetch_is_null(data_dir, capsys):
    code, out, _ = _run(capsys, "state", "get", "x:karpathy")
    assert (code, json.loads(out)) == (0, None)


def test_state_set_and_get_seen_urls(data_dir, capsys):
    _run(capsys, "state", "set", "youtube:AK", "--type", "seen_urls",
         "--value-json", '["https://a","https://b"]', "--run-time", RUN)
    _, out, _ = _run(capsys, "state", "get", "youtube:AK")
    assert json.loads(out) == {"type": "seen_urls", "value": ["https://a", "https://b"]}


def test_state_set_rejects_bad_type(data_dir, capsys):
    code, _, err = _run(capsys, "state", "set", "x:k", "--type", "nope",
                        "--value-json", '"1"', "--run-time", RUN)
    assert code == 1
    assert "未知的游标类型" in err


def test_state_fail_keeps_cursor(data_dir, capsys):
    _run(capsys, "state", "set", "x:k", "--type", "last_seen_id",
         "--value-json", '"123"', "--run-time", RUN)
    _run(capsys, "state", "fail", "x:k", "--error", "timed out", "--run-time", RUN)
    _, out, _ = _run(capsys, "state", "get", "x:k")
    assert json.loads(out)["value"] == "123"


def test_profile_append_and_show(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    code, out, _ = _run(capsys, "profile", "append", "karpathy",
                        "--date", "2026-08-26", "--source", "12 条推文", "--body", "观察正文")
    assert code == 0
    assert out.startswith("OK ")
    _, shown, _ = _run(capsys, "profile", "show", "karpathy")
    assert "观察正文" in shown
    assert "依据：12 条推文" in shown


def test_profile_show_missing_is_empty(data_dir, capsys):
    code, out, _ = _run(capsys, "profile", "show", "nobody")
    assert (code, out) == (0, "EMPTY")


def test_profile_summary_replaces(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/k")
    _run(capsys, "profile", "summary", "k", "--text", "第一版", "--updated-at", "2026-08-26")
    _run(capsys, "profile", "summary", "k", "--text", "第二版", "--updated-at", "2026-08-27")
    _, out, _ = _run(capsys, "profile", "show", "k")
    assert "第二版" in out and "第一版" not in out


def test_init_writes_config(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "fresh-config.json"
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(cfg))
    target = tmp_path / "my-data"
    code, out, _ = _run(capsys, "init", str(target))
    assert code == 0
    assert str(target) in out
    assert json.loads(cfg.read_text(encoding="utf-8"))["DATA_DIR"] == str(target)


def test_data_dir_prints_configured_path(data_dir, capsys):
    code, out, _ = _run(capsys, "data-dir")
    assert (code, out) == (0, str(data_dir))


def test_bad_channel_ref_exits_1(data_dir, capsys):
    code, _, err = _run(capsys, "state", "get", "no-colon-here")
    assert code == 1
    assert "platform:handle" in err


# —— 人工输入路径：依据默认「人工」、正文走 stdin、id 必须在名册里 ——

def _add_karpathy(capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")


def test_profile_append_defaults_source_to_manual(data_dir, capsys):
    """人工记录时不填依据——`人工` 这个值同时就是作者标记。"""
    _add_karpathy(capsys)
    code, _, _ = _run(capsys, "profile", "append", "karpathy",
                      "--date", "2026-08-27 14:32", "--body", "我的看法")
    assert code == 0
    _, shown, _ = _run(capsys, "profile", "show", "karpathy")
    assert "### 2026-08-27 14:32 · 依据：人工" in shown


def test_profile_append_reads_body_from_stdin(data_dir, capsys, monkeypatch):
    """归纳重写后的正文是多行 Markdown，塞命令行参数会被引号和换行折磨。"""
    _add_karpathy(capsys)
    monkeypatch.setattr("sys.stdin", io.StringIO("**关注领域**：agent memory\n\n分歧：重算成本\n"))
    code, _, _ = _run(capsys, "profile", "append", "karpathy", "--date", "2026-08-27 14:32")
    assert code == 0
    _, shown, _ = _run(capsys, "profile", "show", "karpathy")
    assert "**关注领域**：agent memory" in shown
    assert "分歧：重算成本" in shown


def test_profile_append_explicit_body_wins_over_stdin(data_dir, capsys, monkeypatch):
    _add_karpathy(capsys)
    monkeypatch.setattr("sys.stdin", io.StringIO("来自 stdin"))
    _run(capsys, "profile", "append", "karpathy",
         "--date", "2026-08-27 14:32", "--body", "来自参数")
    _, shown, _ = _run(capsys, "profile", "show", "karpathy")
    assert "来自参数" in shown and "来自 stdin" not in shown


def test_profile_append_unknown_creator_exits_1(data_dir, capsys):
    """手打 id 打错一个字母，不能安静地建出一个没人引用的孤儿画像。"""
    code, _, err = _run(capsys, "profile", "append", "karpthy",
                        "--date", "2026-08-27 14:32", "--body", "观察")
    assert code == 1
    assert "karpthy" in err
    assert not (data_dir / "profiles" / "karpthy.md").exists()


def test_profile_append_accepts_alias(data_dir, capsys):
    """merge 之后旧 id 进了 aliases，用旧 id 记录仍要能落到同一个人身上。"""
    _add_karpathy(capsys)
    _run(capsys, "registry", "add", "https://www.youtube.com/@AndrejKarpathy")
    _run(capsys, "registry", "merge", "karpathy", "andrejkarpathy")
    code, _, _ = _run(capsys, "profile", "append", "andrejkarpathy",
                      "--date", "2026-08-27 14:32", "--body", "用旧 id 记的")
    assert code == 0
    _, shown, _ = _run(capsys, "profile", "show", "karpathy")
    assert "用旧 id 记的" in shown


def test_profile_summary_unknown_creator_exits_1(data_dir, capsys):
    code, _, err = _run(capsys, "profile", "summary", "nobody",
                        "--text", "判断", "--updated-at", "2026-08-27")
    assert code == 1
    assert "nobody" in err
