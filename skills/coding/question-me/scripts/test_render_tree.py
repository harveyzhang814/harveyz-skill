import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from render_tree import parse_nodes, build_tree, find_current, Node

SAMPLE = """\
[goal:done]     id=G              将 tags 拆为 fixed_tags + candidate_tags
[success:done]  id=S              新文章有两字段；旧文章不迁移
[scope:done]    id=SC             只改 Python 脚本；SKILL.md 可补充
[storage:done]  id=ST  dep=SC     ~/.hskill/extract-url/fixed_tags.txt
[format:open]   id=FF  dep=ST     frontmatter 字段结构变化
[compat:infer]  id=CP  dep=FF     旧文章不迁移，新旧格式共存
[review:open]   id=RV  dep=SC     candidate_tags review 流程
"""

def test_parse_count():
    nodes = parse_nodes(SAMPLE)
    assert len(nodes) == 7

def test_parse_fields():
    nodes = parse_nodes(SAMPLE)
    g = next(n for n in nodes if n.node_id == 'G')
    assert g.label == 'goal'
    assert g.status == 'done'
    assert g.dep_id is None
    assert '将 tags' in g.text

def test_parse_dep():
    nodes = parse_nodes(SAMPLE)
    st = next(n for n in nodes if n.node_id == 'ST')
    assert st.dep_id == 'SC'

def test_build_roots():
    nodes = parse_nodes(SAMPLE)
    roots, id_map = build_tree(nodes)
    root_ids = {r.node_id for r in roots}
    assert root_ids == {'G', 'S', 'SC'}

def test_build_children():
    nodes = parse_nodes(SAMPLE)
    roots, id_map = build_tree(nodes)
    sc = id_map['SC']
    child_ids = {c.node_id for c in sc.children}
    assert 'ST' in child_ids
    assert 'RV' in child_ids

def test_find_current_highest_impact():
    # FF has CP depending on it (impact=1), RV has none (impact=0)
    # Both have satisfied deps (ST done, SC done)
    nodes = parse_nodes(SAMPLE)
    _, id_map = build_tree(nodes)
    current = find_current(nodes, id_map)
    assert current == 'FF'  # FF has higher impact (CP depends on it)

def test_find_current_none_when_all_done():
    text = "[goal:done] id=G 目标\n[success:done] id=S 成功\n"
    nodes = parse_nodes(text)
    _, id_map = build_tree(nodes)
    assert find_current(nodes, id_map) is None

def test_build_tree_self_dep_not_lost():
    text = "[goal:done] id=G 目标\n[bad:open] id=X dep=X 自引用节点\n"
    nodes = parse_nodes(text)
    roots, id_map = build_tree(nodes)
    root_ids = {r.node_id for r in roots}
    assert 'X' in root_ids, "Self-dep node must not be silently dropped"

def test_build_tree_mutual_dep_not_lost():
    text = "[a:open] id=A dep=B 节点A\n[b:open] id=B dep=A 节点B\n"
    nodes = parse_nodes(text)
    roots, id_map = build_tree(nodes)
    root_ids = {r.node_id for r in roots}
    assert 'A' in root_ids or 'B' in root_ids, "At least one node in a cycle must be reachable"
    # Both should be reachable
    all_ids = set()
    stack = list(roots)
    while stack:
        n = stack.pop()
        all_ids.add(n.node_id)
        stack.extend(n.children)
    assert {'A', 'B'}.issubset(all_ids), "Both nodes in mutual cycle must be reachable"

if __name__ == '__main__':
    import traceback
    passed = failed = 0
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith('test_')]:
        try:
            fn()
            print(f'  PASS  {name}')
            passed += 1
        except Exception as e:
            print(f'  FAIL  {name}: {e}')
            traceback.print_exc()
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
