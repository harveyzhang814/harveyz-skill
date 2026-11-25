import json

from conftest import dumps, features_dir, make_project, obj, run_feature


def test_malformed_but_parseable_file_is_skipped_not_crash(tmp_path):
    root = make_project(tmp_path, [obj("ok", "正常")])
    fdir = features_dir(root)
    (fdir / "n.json").write_text('{"id":"n","name":123}', encoding="utf-8")
    (fdir / "half.json").write_text('{"id":"half","name":"半个"}', encoding="utf-8")
    for args in (["lookup", "正常"], ["list"], ["tree"], ["dupcheck", "别的"]):
        r = run_feature(args, root)
        assert "Traceback" not in r.stderr, (args, r.stderr)
    r = run_feature(["lookup", "正常"], root)
    assert r.returncode == 0
    assert "skip: n.json" in r.stderr
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("new", "新的")))
    assert r.returncode == 0, r.stdout + r.stderr


def test_failed_put_does_not_create_data_dir(tmp_path):
    (tmp_path / ".git").mkdir()
    r = run_feature(["put", "--new"], tmp_path, stdin='{"id":"x"}')
    assert r.returncode == 1
    assert not (tmp_path / ".hskill").exists()
    r = run_feature(["lookup", "任何词"], tmp_path)
    assert r.returncode == 2
    assert "no feature map" in r.stdout


def test_dupcheck_and_suggest_parent_work_without_data_dir(tmp_path):
    root = make_project(tmp_path, None, vocab_md="## 工作区\n定义\n")
    r = run_feature(["dupcheck", "工作区"], root)
    assert r.returncode == 1
    assert "vocab | 工作区" in r.stdout
    r = run_feature(["dupcheck", "无关词"], root)
    assert r.returncode == 0
    r = run_feature(["suggest-parent", "--name", "无关词"], root)
    assert r.returncode == 1
    assert r.stdout.strip() == "no candidates"
    assert not (root / ".hskill" / "capture-feature").exists()


def test_put_new_refuses_to_overwrite_mismatched_file(tmp_path):
    root = make_project(tmp_path, [])
    victim = features_dir(root) / "foo.json"
    victim.write_text(dumps(obj("other", "别人")), encoding="utf-8")
    before = victim.read_bytes()
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("foo", "我")))
    assert r.returncode == 1
    assert victim.read_bytes() == before


def test_remove_mismatched_file_no_traceback(tmp_path):
    root = make_project(tmp_path, [])
    (features_dir(root) / "baz.json").write_text(dumps(obj("bar", "栏")), encoding="utf-8")
    r = run_feature(["remove", "bar"], root)
    assert "Traceback" not in r.stderr
    assert r.returncode == 1


def test_put_rejects_unparsable_versions(tmp_path):
    root = make_project(tmp_path, [])
    for versions in (
        {"introduced": "next"},
        {"introduced": "1.0.0", "deprecated": "later"},
        {"introduced": "1.0.0", "deprecated": ""},
        {"introduced": "1.0.0", "changed": [{"version": "soon", "note": None}]},
    ):
        r = run_feature(["put", "--new"], root, stdin=dumps(obj("a", "甲", versions=versions)))
        assert r.returncode == 1, versions
        assert any("version" in l for l in r.stdout.splitlines() if l.startswith("error: "))
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("a", "甲", versions={"introduced": "unknown"})))
    assert r.returncode == 0
