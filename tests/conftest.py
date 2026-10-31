import shutil
from pathlib import Path

import pytest
import yaml

from descartes.cli import main

TOY = Path(__file__).resolve().parents[1] / "examples" / "toy"


@pytest.fixture
def toy(tmp_path):
    """A copy of the toy example; returns the path of its map."""
    shutil.copytree(TOY, tmp_path / "toy", ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path / "toy" / "descartes.yaml"


@pytest.fixture
def run(capsys):
    """Run the CLI; returns (exit code, combined output)."""
    def _run(*args):
        code = main([str(a) for a in args])
        out = capsys.readouterr()
        return code, out.out + out.err
    return _run


def decision(id, status="decided", states=("chosen", "rejected"), **extra):
    return {"id": id, "question": f"Question {id}", "status": status,
            "options": [{"value": f"option {i}", "state": s} for i, s in enumerate(states)], **extra}


@pytest.fixture
def write_map(tmp_path):
    """Write a map with the given decisions (and top-level extras) to tmp_path; returns its path."""
    def _write(decisions, **top):
        data = {"descartes": "0.1", "study": {"title": "Test"}, **top, "decisions": decisions}
        path = tmp_path / "descartes.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        return path
    return _write
