# Spec v0.2 §4.2-4.3 / §11-13：feature 与 interface 两类对象，父节点须同类型（D20）
from conftest import dumps, features_dir, make_project, obj, run_feature


def base():
    return [
        obj("app-window", "应用窗口", type="interface"),
        obj("node-search", "节点检索"),
    ]


def snapshot(root):
    return {p.name: p.read_bytes() for p in features_dir(root).glob("*.json")}


def test_put_rejects_legacy_types(tmp_path):
    root = make_project(tmp_path, base())
    before = snapshot(root)
    for t in ("surface", "entry"):
        r = run_feature(["put", "--new"], root, stdin=dumps(obj("x-" + t, "甲" + t, type=t)))
        assert r.returncode == 1
        assert "error: type must be one of feature, interface" in r.stdout
    assert snapshot(root) == before


def test_put_new_rejects_cross_type_parent(tmp_path):
    root = make_project(tmp_path, base())
    before = snapshot(root)
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("filter", "按类型筛选", "app-window")))
    assert r.returncode == 1
    assert "error: parent type mismatch" in r.stdout
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("panel", "检索面板", "node-search", type="interface")))
    assert r.returncode == 1
    assert "error: parent type mismatch" in r.stdout
    assert snapshot(root) == before


def test_put_same_type_parent_ok(tmp_path):
    root = make_project(tmp_path, base())
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("filter", "按类型筛选", "node-search")))
    assert r.returncode == 0
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("top-bar", "顶栏", "app-window", type="interface")))
    assert r.returncode == 0


def test_put_replace_rejects_cross_type_parent(tmp_path):
    root = make_project(tmp_path, base() + [obj("filter", "按类型筛选", "node-search")])
    before = snapshot(root)
    r = run_feature(["put", "--replace"], root, stdin=dumps(obj("filter", "按类型筛选", "app-window")))
    assert r.returncode == 1
    assert "error: parent type mismatch" in r.stdout
    assert snapshot(root) == before


def test_check_reports_parent_type_mismatch(tmp_path):
    root = make_project(tmp_path, base() + [obj("filter", "按类型筛选", "app-window")])
    r = run_feature(["check"], root)
    assert r.returncode == 1
    assert "parent-type-mismatch | filter |" in r.stdout


def test_list_type_interface(tmp_path):
    root = make_project(tmp_path, base())
    r = run_feature(["list", "--type", "interface"], root)
    assert r.returncode == 0
    assert [l.split(" | ")[0] for l in r.stdout.splitlines()] == ["app-window"]
