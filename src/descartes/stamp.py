"""`descartes stamp`: record the current hash of every code link after a person has reviewed the cards."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from .check import link_states, schema_issues
from .mapfile import MapError, compose, load_map


def _value(mapping_node, key):
    for k, v in mapping_node.value:
        if k.value == key:
            return v
    return None


def _link_nodes(root):
    """{(decision id, link index): mapping node of that code link}."""
    out = {}
    decisions = _value(root, "decisions")
    for d in decisions.value if decisions is not None else []:
        id_node, code = _value(d, "id"), _value(d, "code")
        for i, link in enumerate(code.value if code is not None else []):
            out[(id_node.value, i)] = link
    return out


def _last_scalar_end(node):
    """Text index just after the last scalar inside node, so insertions land on its line."""
    while isinstance(node, yaml.CollectionNode) and node.value:
        last = node.value[-1]
        node = last[1] if isinstance(node, yaml.MappingNode) else last
    return node.end_mark.index


def _edit(text, node, sha):
    """(position, length to replace, new text) that sets sha256 in one code-link mapping node."""
    current = _value(node, "sha256")
    if current is not None:
        return current.start_mark.index, current.end_mark.index - current.start_mark.index, sha
    if node.flow_style:
        close = node.end_mark.index - 1
        return close, 0, f", sha256: {sha}"
    indent = node.value[0][0].start_mark.column
    end = text.find("\n", _last_scalar_end(node))
    end = len(text) if end == -1 else end
    return end, 0, "\n" + " " * indent + f"sha256: {sha}"


def stamp(map_path: Path):
    """Stamp every link that points at existing lines. Returns (stamped labels, problems)."""
    map_path = Path(map_path)
    data = load_map(map_path)
    errors = schema_issues(data)
    if errors:
        raise MapError("the map does not match the schema; run descartes check first")
    ids = [d["id"] for d in data["decisions"]]
    if len(ids) != len(set(ids)):
        raise MapError("decision ids are not unique; run descartes check first")
    text = map_path.read_text(encoding="utf-8")
    nodes = _link_nodes(compose(text))
    edits, stamped, problems = [], [], []
    for ls in link_states(map_path, data):
        where = f"{ls.decision}: code[{ls.index}]"
        if ls.state in ("missing", "bad-range"):
            problems.append(f"{where}: {ls.message}; not stamped")
        elif ls.state == "drift" and ls.moved_to:
            problems.append(f"{where} {ls.label}: the reviewed lines moved to {ls.moved_to[0]}-{ls.moved_to[1]}; "
                            "update lines, then stamp")
        elif ls.state in ("unstamped", "drift"):
            edits.append(_edit(text, nodes[(ls.decision, ls.index)], ls.sha))
            stamped.append(f"{ls.decision}: {ls.label}")
    for pos, length, new in sorted(edits, reverse=True):
        text = text[:pos] + new + text[pos + length:]
    if edits:
        _write(map_path, text)
    return stamped, problems


def _write(path: Path, text: str):
    """Replace path in one step, so an interrupted write never leaves half a map."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
