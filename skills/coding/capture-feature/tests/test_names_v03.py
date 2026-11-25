# Spec v0.3 §4.2 / §11-15：中英文名分开（D21）
from conftest import dumps, features_dir, make_project, obj, run_feature


def snapshot(root):
    return {p.name: p.read_bytes() for p in features_dir(root).glob("*.json")}


def bad_put(tmp_path, o, msg):
    root = make_project(tmp_path, [obj("existing", "已有", name_en="Existing One")])
    before = snapshot(root)
    r = run_feature(["put", "--new"], root, stdin=dumps(o))
    assert r.returncode == 1, r.stdout
    assert msg in r.stdout, r.stdout
    assert snapshot(root) == before


def test_put_requires_name_en(tmp_path):
    o = obj("a", "甲")
    del o["name_en"]
    bad_put(tmp_path, o, "error: name_en")


def test_put_rejects_latin_in_name(tmp_path):
    bad_put(tmp_path, obj("a", "Home 窗口"), "error: name must be Chinese only")


def test_put_rejects_cjk_in_name_en(tmp_path):
    bad_put(tmp_path, obj("a", "主页窗口", name_en="Home 窗口"), "error: name_en must be English only")


def test_put_rejects_name_en_without_latin(tmp_path):
    bad_put(tmp_path, obj("a", "主页窗口", name_en="123"), "error: name_en must be English only")


def test_put_rejects_mixed_alias(tmp_path):
    bad_put(tmp_path, obj("a", "标签栏", aliases=["Tab 栏"]), "error: aliases must not mix Chinese and English")


def test_put_rejects_duplicate_name_en(tmp_path):
    bad_put(tmp_path, obj("a", "另一个", name_en=" existing one "), "error: name_en already used by existing")


def test_put_allows_mixed_avoid(tmp_path):
    root = make_project(tmp_path, [])
    o = obj("home-window", "主页窗口", name_en="Home Window", avoid=[{"name": "Dashboard 窗口", "note": "旧名"}])
    r = run_feature(["put", "--new"], root, stdin=dumps(o))
    assert r.returncode == 0, r.stdout


def test_lookup_by_name_en_and_card_header(tmp_path):
    root = make_project(tmp_path, [obj("workspace", "工作区", name_en="Work Area", type="interface")])
    r = run_feature(["lookup", "work area"], root)
    assert r.returncode == 0
    assert r.stdout.splitlines()[0] == "## 工作区 / Work Area  [interface]  id=workspace"


def test_dupcheck_exact_on_name_en(tmp_path):
    root = make_project(tmp_path, [obj("workspace", "工作区", name_en="Work Area")])
    r = run_feature(["dupcheck", "Work Area"], root)
    assert r.returncode == 1
    assert "exact | workspace" in r.stdout
