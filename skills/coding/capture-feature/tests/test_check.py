import subprocess

from conftest import dumps, features_dir, make_project, obj, run_feature


def base_objects():
    return [
        obj("app-window", "应用窗口", type="surface"),
        obj(
            "workspace",
            "工作区",
            "app-window",
            type="surface",
            aliases=["右侧面板"],
            avoid=[{"name": "抽屉", "note": None}],
            code=[{"path": "src/PanelArea.tsx", "symbol": "PanelArea"}],
        ),
    ]


def project(tmp_path, **kw):
    return make_project(tmp_path, base_objects(), **kw)


def test_dupcheck_exact_on_avoid(tmp_path):
    r = run_feature(["dupcheck", "抽屉"], project(tmp_path))
    assert r.returncode == 1
    assert "exact | workspace" in r.stdout


def test_dupcheck_fuzzy(tmp_path):
    r = run_feature(["dupcheck", "工作区面板"], project(tmp_path))
    assert r.returncode == 1
    assert "fuzzy | workspace" in r.stdout


def test_dupcheck_vocab_header(tmp_path):
    root = project(tmp_path, vocab_md="## 席位\n_Avoid_: x\n")
    r = run_feature(["dupcheck", "席位"], root)
    assert r.returncode == 1
    assert "vocab | 席位" in r.stdout


def test_dupcheck_clean(tmp_path):
    r = run_feature(["dupcheck", "完全无关的词"], project(tmp_path))
    assert r.returncode == 0
    assert r.stdout == ""


def test_suggest_parent_by_path_first(tmp_path):
    r = run_feature(["suggest-parent", "--name", "拖拽手柄", "--path", "src/PanelArea.tsx"], project(tmp_path))
    assert r.returncode == 0
    assert r.stdout.splitlines()[0] == "workspace | 工作区 | same-file"


def test_suggest_parent_by_name(tmp_path):
    extra = [obj(f"w{i}", f"工作区{i}") for i in range(6)]
    root = make_project(tmp_path, base_objects() + extra)
    r = run_feature(["suggest-parent", "--name", "工作区 Tab 菜单"], root)
    assert r.returncode == 0
    assert "workspace | 工作区 | name" in r.stdout
    assert len(r.stdout.splitlines()) <= 5


def test_suggest_parent_none(tmp_path):
    r = run_feature(["suggest-parent", "--name", "完全无关的词"], project(tmp_path))
    assert r.returncode == 1
    assert r.stdout.strip() == "no candidates"


def test_project_version_sources(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    (a / ".git").mkdir()
    (a / "package.json").write_text('{"version":"1.2.0"}', encoding="utf-8")
    r = run_feature(["project-version"], a)
    assert (r.returncode, r.stdout.strip()) == (0, "1.2.0")

    b = tmp_path / "b"
    b.mkdir()
    (b / ".git").mkdir()
    (b / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.9.1"\n', encoding="utf-8")
    r = run_feature(["project-version"], b)
    assert (r.returncode, r.stdout.strip()) == (0, "0.9.1")

    c = tmp_path / "c"
    c.mkdir()
    for cmd in (
        ["git", "init", "-q"],
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x"],
        ["git", "tag", "v2.0.0"],
    ):
        subprocess.run(cmd, cwd=c, check=True)
    r = run_feature(["project-version"], c)
    assert (r.returncode, r.stdout.strip()) == (0, "v2.0.0")

    d = tmp_path / "d"
    d.mkdir()
    (d / ".git").mkdir()
    r = run_feature(["project-version"], d)
    assert (r.returncode, r.stdout.strip()) == (1, "unknown")


def test_check_clean_ok(tmp_path):
    r = run_feature(["check"], project(tmp_path))
    assert r.returncode == 0
    assert r.stdout.strip() == "ok"


def test_check_reports_structural_problems(tmp_path):
    root = make_project(tmp_path, [obj("same-a", "同名"), obj("same-b", "同名")])
    fdir = features_dir(root)
    (fdir / "broken.json").write_text("{nope", encoding="utf-8")
    (fdir / "wrong-name.json").write_text(dumps(obj("other-id", "改名")), encoding="utf-8")
    (fdir / "orphan.json").write_text(dumps(obj("orphan", "孤儿", "ghost")), encoding="utf-8")
    (fdir / "ca.json").write_text(dumps(obj("ca", "环甲", "cb")), encoding="utf-8")
    (fdir / "cb.json").write_text(dumps(obj("cb", "环乙", "ca")), encoding="utf-8")
    r = run_feature(["check"], root)
    assert r.returncode == 1
    for marker in ["invalid |", "id-mismatch |", "missing-parent |", "cycle |", "duplicate-name |"]:
        assert marker in r.stdout, r.stdout


def test_check_code(tmp_path):
    objs = [
        obj("a", "甲", code=[{"path": "src/gone.ts", "symbol": "X"}]),
        obj("b", "乙", code=[{"path": "src/there.ts", "symbol": "Missing"}]),
        obj("c", "丙", code=[{"path": "src/there.ts", "symbol": "Present"}]),
    ]
    root = make_project(tmp_path, objs)
    (root / "src").mkdir()
    (root / "src" / "there.ts").write_text("export const Present = 1\n", encoding="utf-8")
    r = run_feature(["check", "--code"], root)
    assert r.returncode == 1
    assert "code-missing | a" in r.stdout
    assert "symbol-missing | b" in r.stdout
    assert "| c |" not in r.stdout
    r = run_feature(["check"], root)
    assert r.returncode == 0
    assert "code-missing" not in r.stdout and "symbol-missing" not in r.stdout
