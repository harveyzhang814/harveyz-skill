from conftest import make_project, obj, run_feature


def fixture_objects(extra=()):
    return [
        obj("app-window", "应用窗口", type="surface"),
        obj(
            "workspace",
            "工作区",
            "app-window",
            type="surface",
            aliases=["右侧面板"],
            avoid=[
                {"name": "抽屉", "note": None},
                {"name": "Workspace", "note": "代码内部名，不向用户暴露"},
            ],
            code=[{"path": "src/PanelArea.tsx", "symbol": "PanelArea"}],
            versions={
                "introduced": "0.3.0",
                "changed": [{"version": "0.5.0", "note": "支持多 Tab"}],
                "deprecated": None,
            },
        ),
        obj("tab", "Tab", "workspace"),
        obj("view", "视图", "workspace"),
        obj("tab-bar", "Tab 栏", "tab", type="entry"),
        obj(
            "legacy",
            "旧面板",
            versions={"introduced": "0.1.0", "changed": [], "deprecated": "0.4.0"},
        ),
        *extra,
    ]


def project(tmp_path, extra=()):
    return make_project(tmp_path, fixture_objects(extra))


def test_lookup_by_name_prints_card(tmp_path):
    r = run_feature(["lookup", "工作区"], project(tmp_path))
    assert r.returncode == 0
    out = r.stdout
    for line in [
        "## 工作区  [surface]  id=workspace",
        "别称: 右侧面板",
        "避免: 抽屉；Workspace（代码内部名，不向用户暴露）",
        "位置: 应用窗口 > 工作区",
        "子项: Tab, 视图",
        "代码: src/PanelArea.tsx#PanelArea",
        "版本: 引入 0.3.0；变更 0.5.0（支持多 Tab）；废弃 —",
    ]:
        assert line in out
    positions = [out.index(l) for l in ["## 工作区", "别称:", "避免:", "位置:", "子项:", "代码:", "版本:"]]
    assert positions == sorted(positions)


def test_lookup_by_avoid_name_hits(tmp_path):
    r = run_feature(["lookup", "抽屉"], project(tmp_path))
    assert r.returncode == 0
    assert "id=workspace" in r.stdout


def test_lookup_sentence_contains_name(tmp_path):
    r = run_feature(["lookup", "右边的工作区怎么拖宽"], project(tmp_path))
    assert r.returncode == 0
    assert "id=workspace" in r.stdout


def test_lookup_omits_empty_lines(tmp_path):
    r = run_feature(["lookup", "视图"], project(tmp_path))
    assert r.returncode == 0
    for prefix in ["别称:", "避免:", "子项:", "代码:"]:
        assert prefix not in r.stdout


def test_lookup_short_query_is_miss(tmp_path):
    r = run_feature(["lookup", "a"], project(tmp_path))
    assert r.returncode == 1
    assert r.stdout.strip() == "no match: a"


def test_lookup_miss(tmp_path):
    r = run_feature(["lookup", "zzz"], project(tmp_path))
    assert r.returncode == 1
    assert r.stdout.strip() == "no match: zzz"


def test_lookup_degrades_above_three(tmp_path):
    extra = [obj(f"p{i}", f"面板{i}号") for i in range(4)]
    r = run_feature(["lookup", "面板"], project(tmp_path, extra))
    assert r.returncode == 0
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1
    import re

    m = re.match(r"^(\d+) matches: ", lines[0])
    assert m and int(m.group(1)) > 3


def test_lookup_degrades_avoid_hit_card_shows_note(tmp_path):
    r = run_feature(["lookup", "workspace"], project(tmp_path))
    assert r.returncode == 0
    assert "Workspace（代码内部名，不向用户暴露）" in r.stdout


def test_tree_default_depth_1(tmp_path):
    r = run_feature(["tree"], project(tmp_path))
    assert r.returncode == 0
    lines = r.stdout.splitlines()
    assert "应用窗口 [surface] app-window" in lines
    assert "旧面板 [feature] legacy" in lines
    assert "  工作区 [surface] workspace" in lines
    assert "Tab" not in r.stdout


def test_tree_subtree_depth_2(tmp_path):
    r = run_feature(["tree", "workspace", "--depth", "2"], project(tmp_path))
    assert r.returncode == 0
    assert "Tab 栏" in r.stdout


def test_list_type_filter(tmp_path):
    r = run_feature(["list", "--type", "entry"], project(tmp_path))
    assert r.returncode == 0
    lines = r.stdout.splitlines()
    assert len(lines) == 1
    assert lines[0].rstrip() == "tab-bar | Tab 栏 | entry | tab |"


def ids(out):
    return {l.split(" | ")[0] for l in out.splitlines()}


def test_list_at_boundaries(tmp_path):
    root = project(tmp_path)
    at = lambda v: ids(run_feature(["list", "--at", v], root).stdout)
    assert {"workspace", "legacy"} <= at("0.3.0")
    assert "legacy" not in at("0.4.0")
    low = at("0.2.0")
    assert "workspace" not in low
    assert "view" in low


def test_list_at_unparsable_exits_2(tmp_path):
    r = run_feature(["list", "--at", "abc"], project(tmp_path))
    assert r.returncode == 2


def test_refs_same_file_and_dir(tmp_path):
    root = project(tmp_path)
    r = run_feature(["refs", "src/PanelArea.tsx"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "workspace | 工作区 | same-file | src/PanelArea.tsx#PanelArea"
    r = run_feature(["refs", "src/"], root)
    assert r.returncode == 0
    assert "dir-contains" in r.stdout
    r = run_feature(["refs", "other.ts"], root)
    assert r.returncode == 1
    assert r.stdout.strip() == "no refs: other.ts"
