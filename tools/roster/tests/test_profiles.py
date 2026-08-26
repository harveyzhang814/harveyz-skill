from roster import profiles

D1, D2, D3 = "2026-08-19", "2026-08-26", "2026-09-02"


def test_read_missing_returns_none(data_dir):
    assert profiles.read(data_dir, "nobody") is None


def test_append_creates_file_with_frontmatter(data_dir):
    profiles.append_observation(data_dir, "karpathy", D2, "sync-xtimeline 12 条推文", "写得很密")
    text = profiles.read(data_dir, "karpathy")
    assert text.startswith("---\n")
    assert "creator_id: karpathy" in text
    assert f"updated_at: {D2}" in text
    assert "## 当前判断" in text
    assert "## 观察" in text
    assert "### 2026-08-26 · 依据：sync-xtimeline 12 条推文" in text
    assert "写得很密" in text


def test_profile_path_is_under_profiles_dir(data_dir):
    assert profiles.profile_path(data_dir, "karpathy") == data_dir / "profiles" / "karpathy.md"


def test_second_append_goes_on_top(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "旧观察")
    profiles.append_observation(data_dir, "k", D2, "晚", "新观察")
    text = profiles.read(data_dir, "k")
    assert text.index("新观察") < text.index("旧观察")


def test_append_never_rewrites_existing_observations(data_dir):
    """这是整个设计里唯一不可重建的数据，追加不能碰旧条目。"""
    profiles.append_observation(data_dir, "k", D1, "早", "旧观察原文")
    before = profiles.read(data_dir, "k")
    profiles.append_observation(data_dir, "k", D2, "晚", "新观察")
    after = profiles.read(data_dir, "k")
    assert "### 2026-08-19 · 依据：早\n\n旧观察原文" in before
    assert "### 2026-08-19 · 依据：早\n\n旧观察原文" in after


def test_append_bumps_updated_at(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "a")
    profiles.append_observation(data_dir, "k", D2, "晚", "b")
    assert f"updated_at: {D2}" in profiles.read(data_dir, "k")


def test_set_summary_replaces_only_summary(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "观察正文")
    profiles.set_summary(data_dir, "k", "他擅长把复杂的东西讲简单", D2)
    text = profiles.read(data_dir, "k")
    assert "他擅长把复杂的东西讲简单" in text
    assert "观察正文" in text


def test_set_summary_twice_does_not_accumulate(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "观察")
    profiles.set_summary(data_dir, "k", "第一版判断", D2)
    profiles.set_summary(data_dir, "k", "第二版判断", D3)
    text = profiles.read(data_dir, "k")
    assert "第一版判断" not in text
    assert "第二版判断" in text


def test_set_summary_on_missing_profile_creates_it(data_dir):
    profiles.set_summary(data_dir, "k", "判断", D2)
    assert "判断" in profiles.read(data_dir, "k")


def test_archive_moves_file_and_leaves_original_gone(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "观察")
    dest = profiles.archive(data_dir, "k")
    assert dest == data_dir / "profiles" / "archived" / "k.md"
    assert dest.exists()
    assert profiles.read(data_dir, "k") is None
    assert "观察" in dest.read_text(encoding="utf-8")


def test_archive_missing_returns_none(data_dir):
    assert profiles.archive(data_dir, "nobody") is None


def test_archive_twice_does_not_clobber(data_dir):
    """取关又重关又取关时，第一份归档不能被第二份盖掉。"""
    profiles.append_observation(data_dir, "k", D1, "早", "第一轮观察")
    profiles.archive(data_dir, "k")
    profiles.append_observation(data_dir, "k", D2, "晚", "第二轮观察")
    second = profiles.archive(data_dir, "k")
    assert second == data_dir / "profiles" / "archived" / "k-2.md"
    first = data_dir / "profiles" / "archived" / "k.md"
    assert "第一轮观察" in first.read_text(encoding="utf-8")


def test_merge_combines_observations_newest_first(data_dir):
    profiles.append_observation(data_dir, "a", D1, "a 源", "a 的旧观察")
    profiles.append_observation(data_dir, "b", D3, "b 源", "b 的新观察")
    profiles.merge(data_dir, "a", "b", D3)
    text = profiles.read(data_dir, "a")
    assert text.index("b 的新观察") < text.index("a 的旧观察")


def test_merge_clears_summary(data_dir):
    """两个人的判断合并之后，旧摘要不再成立，置空等重算。"""
    profiles.append_observation(data_dir, "a", D1, "源", "观察")
    profiles.set_summary(data_dir, "a", "旧判断", D2)
    profiles.append_observation(data_dir, "b", D2, "源", "观察 b")
    profiles.merge(data_dir, "a", "b", D3)
    assert "旧判断" not in profiles.read(data_dir, "a")


def test_merge_archives_b(data_dir):
    profiles.append_observation(data_dir, "a", D1, "源", "观察 a")
    profiles.append_observation(data_dir, "b", D2, "源", "观察 b")
    profiles.merge(data_dir, "a", "b", D3)
    assert profiles.read(data_dir, "b") is None
    assert (data_dir / "profiles" / "archived" / "b.md").exists()


def test_merge_when_b_has_no_profile_is_noop(data_dir):
    profiles.append_observation(data_dir, "a", D1, "源", "观察 a")
    profiles.merge(data_dir, "a", "b", D3)
    assert "观察 a" in profiles.read(data_dir, "a")


def test_merge_when_a_has_no_profile_adopts_b(data_dir):
    profiles.append_observation(data_dir, "b", D2, "源", "观察 b")
    profiles.merge(data_dir, "a", "b", D3)
    assert "观察 b" in profiles.read(data_dir, "a")
    assert "creator_id: a" in profiles.read(data_dir, "a")
