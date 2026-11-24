import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "feature.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("feature_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def obj(id, name, parent=None, **kw):
    base = {
        "schema": 1,
        "id": id,
        "type": "feature",
        "name": name,
        "aliases": [],
        "avoid": [],
        "description": "d",
        "parent": parent,
        "code": [],
        "versions": {"introduced": "unknown", "changed": [], "deprecated": None},
    }
    base.update(kw)
    return base


def make_project(tmp_path, objects, vocab_md=None):
    (tmp_path / ".git").mkdir(exist_ok=True)
    if objects is not None:
        features = tmp_path / ".hskill" / "capture-feature" / "features"
        features.mkdir(parents=True, exist_ok=True)
        feature = _load_module()
        for o in objects:
            (features / f"{o['id']}.json").write_text(feature.serialize(o), encoding="utf-8")
    if vocab_md is not None:
        vdir = tmp_path / ".hskill" / "capture-vocab"
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "vocab.md").write_text(vocab_md, encoding="utf-8")
    return tmp_path


def run_feature(args, cwd, stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        input=stdin,
        capture_output=True,
        text=True,
    )


def features_dir(root):
    return Path(root) / ".hskill" / "capture-feature" / "features"


def dumps(o):
    return json.dumps(o, ensure_ascii=False)
