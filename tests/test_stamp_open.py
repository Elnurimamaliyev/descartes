from conftest import decision
from descartes.mapfile import load_map


def test_stamp_records_hashes_and_keeps_comments(tmp_path, run):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\nz = 3\n")
    path = tmp_path / "descartes.yaml"
    path.write_text(
        '# my note about this map\n'
        'descartes: "0.1"\n'
        'study: {title: T}\n'
        'decisions:\n'
        '  - id: block-style  # keep this comment\n'
        '    question: Q\n'
        '    status: decided\n'
        '    code:\n'
        '      - path: a.py\n'
        '        lines:\n'
        '          - 1\n'
        '          - 2\n'
        '    options: [{value: v, state: chosen}]\n'
        '  - id: flow-style\n'
        '    question: Q\n'
        '    status: decided\n'
        '    code:\n'
        '      - {path: a.py, lines: [3, 3]}\n'
        '    options: [{value: v, state: chosen}]\n')
    code, out = run("check", "--strict", path)
    assert code == 1 and out.count("not stamped") == 2
    code, out = run("stamp", path)
    assert code == 0, out
    assert "stamped block-style: a.py:1-2" in out and "stamped flow-style: a.py:3" in out
    text = path.read_text()
    assert text.startswith("# my note about this map\n") and "# keep this comment" in text
    assert run("check", "--strict", path)[0] == 0
    assert all("sha256" in c for d in load_map(path)["decisions"] for c in d["code"])


def test_stamp_after_review_clears_drift(toy, run):
    analysis = toy.parent / "analysis.py"
    analysis.write_text(analysis.read_text().replace("N_PERMUTATIONS = 10000", "N_PERMUTATIONS = 20000"))
    assert run("check", toy)[0] == 1
    code, out = run("stamp", toy)
    assert code == 0
    assert out.strip() == "stamped group-test: analysis.py:16"
    code, out = run("check", toy)
    assert code == 0, out
    assert "out of sync" not in out
    assert "expect text not found in the linked lines: N_PERMUTATIONS = 10000" in out


def test_stamp_refuses_moved_lines(toy, run):
    analysis = toy.parent / "analysis.py"
    analysis.write_text("# a new first line\n" + analysis.read_text())
    before = toy.read_text()
    code, out = run("stamp", toy)
    assert code == 1
    assert "rt-window: code[0] analysis.py:14: the reviewed lines moved to 15-15; update lines, then stamp" in out
    assert "stamped" not in out
    assert toy.read_text() == before


def test_stamp_refuses_invalid_map(write_map, run):
    code, out = run("stamp", write_map([decision("a", status="maybe")]))
    assert code == 1
    assert "does not match the schema" in out


def test_open_lists_open_and_unreviewed_agent_decisions(tmp_path, write_map, run):
    (tmp_path / "a.py").write_text("x = 1\n")
    path = write_map([
        decision("by-agent", decided_by="agent", code=[{"path": "a.py", "lines": [1, 1]}]),
        decision("by-human", decided_by="human", code=[{"path": "a.py", "lines": [1, 1]}]),
        decision("waiting", status="open", states=("untried", "untried"), notes="Needs the PI.\nSecond line."),
    ])
    code, out = run("open", path)
    assert code == 0
    assert "Open decisions (1):" in out and "waiting: Question waiting" in out and "notes: Needs the PI." in out
    assert "not reviewed since it changed (1):" in out and "by-agent" in out and "a.py:1 (not stamped)" in out
    assert "by-human" not in out
