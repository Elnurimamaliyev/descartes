"""Reading decision maps and the code they link to."""
from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path

import yaml

SCHEMA_NAME = "decision-map.schema.json"


class MapError(Exception):
    """The map file cannot be read as a decision map."""


class _Loader(yaml.SafeLoader):
    """Safe loader that rejects duplicate keys and keeps dates as strings."""


# Without the timestamp resolver, `date: 2026-10-01` stays the string the schema expects.
_Loader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _construct_mapping(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise MapError(f"line {key_node.start_mark.line + 1}: duplicate key {key!r} (YAML keeps only the last one)")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def load_text(text: str):
    try:
        return yaml.load(text, Loader=_Loader)
    except yaml.YAMLError as e:
        raise MapError(f"not valid YAML: {e}") from None


def load_map(path: Path):
    """The parsed map at path; raises MapError when it cannot be read."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise MapError(f"cannot read {path}: {e.strerror}") from None
    data = load_text(text)
    if not isinstance(data, dict):
        raise MapError("the map must be a YAML mapping with descartes, study and decisions")
    return data


def compose(text: str):
    """The YAML node tree of text, with positions, for edits that keep comments and layout."""
    return yaml.compose(text, Loader=_Loader)


def schema() -> dict:
    """The JSON Schema of the map format: the installed copy, else the one in the source tree."""
    packaged = resources.files("descartes").joinpath(SCHEMA_NAME)
    if packaged.is_file():
        return json.loads(packaged.read_text(encoding="utf-8"))
    source = Path(__file__).resolve().parents[2] / "spec" / SCHEMA_NAME
    return json.loads(source.read_text(encoding="utf-8"))


def code_root(map_path: Path, data: dict) -> Path:
    return (Path(map_path).parent / data.get("root", ".")).resolve()


def code_lines(path: Path) -> list[str]:
    """Lines of a source file; for a Jupyter notebook, the lines of its code cells in order."""
    if path.suffix == ".ipynb":
        cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
        return [line for c in cells if c.get("cell_type") == "code" for line in "".join(c["source"]).splitlines()]
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def digest(lines: list[str]) -> str:
    """sha256 of lines with trailing whitespace removed, joined with newlines."""
    return hashlib.sha256("\n".join(line.rstrip() for line in lines).encode("utf-8")).hexdigest()


def find_block(lines: list[str], length: int, sha: str):
    """(start, end) of the first block of length lines whose digest is sha, or None."""
    for start in range(len(lines) - length + 1):
        if digest(lines[start:start + length]) == sha:
            return start + 1, start + length
    return None
