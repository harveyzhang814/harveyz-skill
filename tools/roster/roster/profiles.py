"""profiles/<creator-id>.md —— 人的画像。

全套数据里唯一不可重建的部分。「观察」段只追加不改写；「当前判断」段可以
重写，因为它能从观察重算。删除操作一律归档而非删除——一个日常动作不该能
永久销毁这份数据。

每条观察带日期和依据来源：三个月后看到「他擅长 X」，得能判断这是基于 40 条
推文写的，还是基于 3 个视频标题猜的。
"""
import re
from pathlib import Path

_OBS_RE = re.compile(r"^### (\d{4}-\d{2}-\d{2}) · 依据：(.*)$")


def _profiles_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "profiles"


def profile_path(data_dir: Path, creator_id: str) -> Path:
    return _profiles_dir(data_dir) / f"{creator_id}.md"


def read(data_dir: Path, creator_id: str) -> str | None:
    path = profile_path(data_dir, creator_id)
    return path.read_text(encoding="utf-8") if path.exists() else None


def _parse(text: str | None) -> tuple[str, list[dict]]:
    """→ (当前判断正文, [{date, source, body}, ...])。解析失败不抛异常：
    宁可把整段当成摘要保留，也不能因为用户手改过格式就丢掉观察。"""
    if not text:
        return "", []

    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    summary_part, _, obs_part = body.partition("## 观察")
    summary = summary_part.replace("## 当前判断", "", 1).strip()

    observations: list[dict] = []
    current: dict | None = None
    for line in obs_part.splitlines():
        match = _OBS_RE.match(line)
        if match:
            current = {"date": match.group(1), "source": match.group(2), "body": ""}
            observations.append(current)
        elif current is not None:
            current["body"] += line + "\n"
    for obs in observations:
        obs["body"] = obs["body"].strip()
    return summary, observations


def _render(creator_id: str, updated_at: str, summary: str, observations: list[dict]) -> str:
    parts = [
        "---",
        f"creator_id: {creator_id}",
        f"updated_at: {updated_at}",
        "---",
        "",
        "## 当前判断",
        "",
        summary,
        "",
        "## 观察",
        "",
    ]
    for obs in observations:
        parts += [f"### {obs['date']} · 依据：{obs['source']}", "", obs["body"], ""]
    return "\n".join(parts).rstrip() + "\n"


def _write(data_dir: Path, creator_id: str, updated_at: str,
           summary: str, observations: list[dict]) -> None:
    path = profile_path(data_dir, creator_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(creator_id, updated_at, summary, observations), encoding="utf-8")


def append_observation(data_dir: Path, creator_id: str, date: str,
                       source: str, body: str) -> None:
    summary, observations = _parse(read(data_dir, creator_id))
    observations.insert(0, {"date": date, "source": source, "body": body.strip()})
    _write(data_dir, creator_id, date, summary, observations)


def set_summary(data_dir: Path, creator_id: str, text: str, updated_at: str) -> None:
    _, observations = _parse(read(data_dir, creator_id))
    _write(data_dir, creator_id, updated_at, text.strip(), observations)


def archive(data_dir: Path, creator_id: str) -> Path | None:
    src = profile_path(data_dir, creator_id)
    if not src.exists():
        return None
    archived = _profiles_dir(data_dir) / "archived"
    archived.mkdir(parents=True, exist_ok=True)

    dest = archived / f"{creator_id}.md"
    n = 2
    while dest.exists():           # 早先归档的那份不能被盖掉
        dest = archived / f"{creator_id}-{n}.md"
        n += 1
    src.rename(dest)
    return dest


def merge(data_dir: Path, id_a: str, id_b: str, updated_at: str) -> None:
    _, obs_a = _parse(read(data_dir, id_a))
    _, obs_b = _parse(read(data_dir, id_b))
    if not obs_b:
        return
    merged = sorted(obs_a + obs_b, key=lambda o: o["date"], reverse=True)
    _write(data_dir, id_a, updated_at, "", merged)   # 摘要置空，等重算
    archive(data_dir, id_b)
