from todo.models import Project, ProjectCreate, ProjectUpdate


def test_project_create_defaults():
    p = ProjectCreate(repo_name="video-learner")
    assert p.repo_name == "video-learner"
    assert p.local_path is None


def test_project_create_with_path():
    p = ProjectCreate(repo_name="video-learner", local_path="/home/user/Projects/Video-Learner")
    assert p.local_path == "/home/user/Projects/Video-Learner"


def test_project_update_all_optional():
    p = ProjectUpdate()
    assert p.repo_name is None
    assert p.local_path is None


def test_project_full():
    p = Project(id=1, repo_name="video-learner", local_path=None, created_at="2026-06-12T10:00:00+00:00")
    assert p.id == 1
    assert p.repo_name == "video-learner"
