import json

from jsonschema import Draft202012Validator

from conftest import decision
from descartes.mapfile import schema


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(schema())


def test_clean_example_passes(toy, run):
    code, out = run("check", "--strict", toy)
    assert code == 0, out
    assert "0 errors, 0 warnings" in out


def test_open_card_warns(write_map, run):
    path = write_map([decision("a"), decision("b", status="open", states=("untried", "untried"))])
    code, out = run("check", path)
    assert code == 0
    assert "warning: b: open" in out
    code, _ = run("check", "--strict", path)
    assert code == 1


def test_code_change_triggers_drift(toy, run):
    analysis = toy.parent / "analysis.py"
    analysis.write_text(analysis.read_text().replace("RT_MIN_MS, RT_MAX_MS = 200, 2000", "RT_MIN_MS, RT_MAX_MS = 150, 2000"))
    code, out = run("check", toy)
    assert code == 1
    assert "rt-window: code[0] analysis.py:14: out of sync" in out
    assert "RT_MIN_MS, RT_MAX_MS = 150, 2000" in out


def test_whitespace_only_change_does_not_drift(toy, run):
    analysis = toy.parent / "analysis.py"
    lines = analysis.read_text().split("\n")
    analysis.write_text("\r\n".join(line + " \t " for line in lines))
    code, out = run("check", "--strict", toy)
    assert code == 0, out


def test_indentation_change_drifts(toy, run):
    analysis = toy.parent / "analysis.py"
    analysis.write_text(analysis.read_text().replace("    observed = statistics.mean(diffs)", "      observed = statistics.mean(diffs)"))
    code, out = run("check", toy)
    assert code == 1
    assert "group-test: code[1] analysis.py:49-56: out of sync" in out


def test_moved_lines_are_reported(toy, run):
    analysis = toy.parent / "analysis.py"
    analysis.write_text("# a new first line\n" + analysis.read_text())
    code, out = run("check", toy)
    assert code == 1
    assert "the reviewed lines are now at 15-15, update lines" in out


def test_two_chosen_options_fail(write_map, run):
    code, out = run("check", write_map([decision("a", states=("chosen", "chosen"))]))
    assert code == 1
    assert "exactly one option must be chosen (2 are)" in out


def test_decided_without_chosen_fails(write_map, run):
    code, out = run("check", write_map([decision("a", states=("tested", "rejected"))]))
    assert code == 1
    assert "exactly one option must be chosen (0 are)" in out


def test_open_with_chosen_fails(write_map, run):
    code, out = run("check", write_map([decision("a", status="open", states=("chosen", "untried"))]))
    assert code == 1
    assert "open, so no option may be chosen" in out


def test_unknown_dependency_fails(write_map, run):
    code, out = run("check", write_map([decision("a", depends_on=["missing"])]))
    assert code == 1
    assert "depends on unknown decision 'missing'" in out


def test_cycle_fails(write_map, run):
    path = write_map([decision("a", depends_on=["c"]), decision("b", depends_on=["a"]), decision("c", depends_on=["b"])])
    code, out = run("check", path)
    assert code == 1
    assert "dependency cycle: a -> c -> b -> a" in out


def test_self_dependency_fails(write_map, run):
    code, out = run("check", write_map([decision("a", depends_on=["a"])]))
    assert code == 1
    assert "dependency cycle: a -> a" in out


def test_schema_violation_fails(write_map, run):
    code, out = run("check", write_map([decision("a", status="maybe")]))
    assert code == 1
    assert "decisions[0].status: 'maybe' is not one of" in out


def test_bad_id_and_unknown_field_fail(write_map, run):
    code, out = run("check", write_map([decision("Not_Kebab", colour="red")]))
    assert code == 1
    assert "does not match" in out
    assert "decisions[0]: unknown field 'colour' (extension fields must start with x-)" in out


def test_extension_fields_are_allowed(write_map, run):
    code, out = run("check", write_map([decision("a", **{"x-reviewer": "PI"})]))
    assert code == 0, out


def test_duplicate_id_fails(write_map, run):
    code, out = run("check", write_map([decision("a"), decision("a")]))
    assert code == 1
    assert "a: duplicate decision id" in out


def test_duplicate_yaml_key_fails(tmp_path, run):
    path = tmp_path / "descartes.yaml"
    path.write_text('descartes: "0.1"\nstudy: {title: T}\ndecisions:\n  - id: a\n    question: Q\n    status: decided\n'
                    '    options:\n      - value: v\n        state: chosen\n        evidence: first\n        evidence: second\n')
    code, out = run("check", path)
    assert code == 1
    assert "line 11: duplicate key 'evidence'" in out


def test_unquoted_date_is_a_string(tmp_path, run):
    path = tmp_path / "descartes.yaml"
    path.write_text('descartes: "0.1"\nstudy: {title: T}\ndecisions:\n  - id: a\n    question: Q\n    status: decided\n'
                    '    date: 2026-10-01\n    options: [{value: v, state: chosen}]\n')
    code, out = run("check", path)
    assert code == 0, out


def test_unknown_stage_fails(write_map, run):
    path = write_map([decision("a", stage="nowhere")], stages=[{"id": "clean", "name": "Cleaning"}])
    code, out = run("check", path)
    assert code == 1
    assert "unknown stage 'nowhere'" in out


def test_missing_file_and_bad_range_fail(tmp_path, write_map, run):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    path = write_map([decision("a", code=[{"path": "gone.py", "lines": [1, 1]}]),
                      decision("b", code=[{"path": "a.py", "lines": [2, 5]}])])
    code, out = run("check", path)
    assert code == 1
    assert "gone.py: file not found" in out
    assert "lines 2-5 do not exist (a.py has 2 lines)" in out


def test_expect_mismatch_warns(tmp_path, write_map, run):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    code, out = run("check", write_map([decision("a", code=[{"path": "a.py", "lines": [1, 1], "expect": "y = 2"}])]))
    assert "expect text not found in the linked lines: y = 2" in out


def test_root_moves_code_paths(tmp_path, write_map, run):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    code, out = run("check", write_map([decision("a", code=[{"path": "a.py", "lines": [1, 1]}])], root="src"))
    assert code == 0, out
    assert "not stamped" in out


def test_notebook_lines_count_code_cells_only(tmp_path, write_map, run):
    def notebook(outputs):
        cells = [{"cell_type": "markdown", "source": ["# Title\n", "text\n"], "metadata": {}},
                 {"cell_type": "code", "source": ["import math\n", "CUTOFF = 0.5\n"], "outputs": outputs,
                  "metadata": {}, "execution_count": None}]
        return json.dumps({"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}, indent=1)

    nb = tmp_path / "analysis.ipynb"
    nb.write_text(notebook([]))
    path = write_map([decision("a", code=[{"path": "analysis.ipynb", "lines": [2, 2], "expect": "CUTOFF = 0.5"}])])
    assert run("stamp", path)[0] == 0
    nb.write_text(notebook([{"output_type": "stream", "name": "stdout", "text": ["new output\n"]}]))
    code, out = run("check", "--strict", path)
    assert code == 0, out
