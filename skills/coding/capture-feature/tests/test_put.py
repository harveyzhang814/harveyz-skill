import json

from conftest import dumps, features_dir, make_project, obj, run_feature


def snapshot(root):
    return {p.name: p.read_bytes() for p in features_dir(root).glob("*.json")}


def test_put_new_writes_canonical_bytes(tmp_path):
    root = make_project(tmp_path, [])
    raw = {
        "versions": {"introduced": "0.3.0"},
        "parent": None,
        "description": "右侧面板",
        "name": "工作区",
        "type": "interface",
        "id": "workspace",
        "schema": 1,
        "avoid": [{"name": "抽屉"}],
    }
    r = run_feature(["put", "--new"], root, stdin=dumps(raw))
    assert r.returncode == 0, r.stdout
    assert r.stdout.strip() == "wrote features/workspace.json"
    expected = (
        json.dumps(
            {
                "schema": 1,
                "id": "workspace",
                "type": "interface",
                "name": "工作区",
                "aliases": [],
                "avoid": [{"name": "抽屉", "note": None}],
                "description": "右侧面板",
                "parent": None,
                "code": [],
                "versions": {"introduced": "0.3.0", "changed": [], "deprecated": None},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    assert (features_dir(root) / "workspace.json").read_text(encoding="utf-8") == expected


def test_put_new_rejects_existing_id(tmp_path):
    root = make_project(tmp_path, [obj("a", "甲")])
    before = snapshot(root)
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("a", "乙")))
    assert r.returncode == 1
    assert "error: " in r.stdout
    assert snapshot(root) == before


def test_put_replace_requires_existing_id(tmp_path):
    root = make_project(tmp_path, [])
    r = run_feature(["put", "--replace"], root, stdin=dumps(obj("a", "甲")))
    assert r.returncode == 1
    assert not (features_dir(root) / "a.json").exists()


def test_put_rejects_missing_required_field(tmp_path):
    root = make_project(tmp_path, [])
    bad = obj("a", "甲")
    del bad["description"]
    r = run_feature(["put", "--new"], root, stdin=dumps(bad))
    assert r.returncode == 1
    assert any("description" in l for l in r.stdout.splitlines() if l.startswith("error: "))


def test_put_rejects_bad_type(tmp_path):
    root = make_project(tmp_path, [])
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("a", "甲", type="page")))
    assert r.returncode == 1


def test_put_rejects_bad_id(tmp_path):
    root = make_project(tmp_path, [])
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("Work_Space", "甲")))
    assert r.returncode == 1


def test_put_rejects_unknown_parent(tmp_path):
    root = make_project(tmp_path, [])
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("a", "甲", parent="nope")))
    assert r.returncode == 1


def test_put_replace_rejects_cycle(tmp_path):
    root = make_project(tmp_path, [obj("a", "甲"), obj("b", "乙", "a"), obj("c", "丙", "b")])
    before = snapshot(root)
    r = run_feature(["put", "--replace"], root, stdin=dumps(obj("a", "甲", "c")))
    assert r.returncode == 1
    assert "error: cycle" in r.stdout
    assert snapshot(root) == before


def test_put_rejects_duplicate_name(tmp_path):
    root = make_project(tmp_path, [obj("a", "Work Space")])
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("b", " work space ")))
    assert r.returncode == 1
    assert not (features_dir(root) / "b.json").exists()


def test_put_warns_on_alias_overlap(tmp_path):
    root = make_project(tmp_path, [obj("a", "甲", avoid=[{"name": "抽屉", "note": None}])])
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("b", "乙", aliases=["抽屉"])))
    assert r.returncode == 0
    assert "warn: " in r.stdout
    assert (features_dir(root) / "b.json").exists()


def test_put_creates_dir_at_git_root_from_subdir(tmp_path):
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "src" / "x"
    sub.mkdir(parents=True)
    r = run_feature(["put", "--new"], sub, stdin=dumps(obj("a", "甲")))
    assert r.returncode == 0, r.stdout
    assert (features_dir(tmp_path) / "a.json").exists()


def test_put_without_git_root_exits_2(tmp_path):
    r = run_feature(["put", "--new"], tmp_path, stdin=dumps(obj("a", "甲")))
    assert r.returncode == 2
    assert "no feature map" in r.stdout


def test_put_ignores_corrupt_sibling(tmp_path):
    root = make_project(tmp_path, [])
    (features_dir(root) / "bad.json").write_text("{not json", encoding="utf-8")
    r = run_feature(["put", "--new"], root, stdin=dumps(obj("a", "甲")))
    assert r.returncode == 0, r.stdout
    assert "skip: bad.json" in r.stderr


def test_show_existing_and_missing(tmp_path):
    root = make_project(tmp_path, [obj("workspace", "工作区", type="interface")])
    r = run_feature(["show", "workspace"], root)
    assert r.returncode == 0
    assert "## 工作区  [interface]  id=workspace" in r.stdout
    r = run_feature(["show", "nope"], root)
    assert r.returncode == 1
    assert r.stdout.strip() == "no such id: nope"


def test_readonly_without_data_dir_exits_2(tmp_path):
    root = make_project(tmp_path, None)
    r = run_feature(["show", "x"], root)
    assert r.returncode == 2
    assert "no feature map" in r.stdout


def test_remove_leaf_and_refuse_with_children(tmp_path):
    root = make_project(tmp_path, [obj("a", "甲"), obj("b", "乙", "a"), obj("c", "丙", "b")])
    r = run_feature(["remove", "c"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "removed c"
    assert not (features_dir(root) / "c.json").exists()
    r = run_feature(["remove", "a"], root)
    assert r.returncode == 1
    assert r.stdout.strip() == "has children: b"
