"""The checks behind `descartes check`."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from .mapfile import MapError, code_lines, code_root, digest, find_block, load_map, schema


@dataclass
class Issue:
    level: str  # "error" or "warning"
    where: str
    message: str

    def __str__(self):
        return f"{self.level}: {self.where}: {self.message}"


@dataclass
class LinkState:
    """What a code link points at now. state: ok | unstamped | drift | missing | bad-range."""
    decision: str
    index: int
    link: dict
    state: str
    message: str = ""
    sha: str | None = None
    moved_to: tuple[int, int] | None = None
    expect_found: bool = True

    @property
    def label(self):
        start, end = self.link["lines"]
        return f"{self.link['path']}:{start}" + (f"-{end}" if end != start else "")


def _json_path(parts) -> str:
    out = ""
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out or "map"


def schema_issues(data: dict) -> list[Issue]:
    validator = Draft202012Validator(schema())
    errors = sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    return [Issue("error", _json_path(e.absolute_path), _message(e)) for e in errors]


def _message(error) -> str:
    if error.validator == "additionalProperties" and isinstance(error.instance, dict):
        known = error.schema.get("properties", {})
        extra = [k for k in error.instance if k not in known and not str(k).startswith("x-")]
        if extra:
            names = ", ".join(repr(k) for k in extra)
            return f"unknown field{'s' if len(extra) > 1 else ''} {names} (extension fields must start with x-)"
    return error.message


def _squash(text: str) -> str:
    return " ".join(text.split())


def link_states(map_path: Path, data: dict) -> list[LinkState]:
    """The current state of every code link in the map."""
    root = code_root(map_path, data)
    out = []
    for d in data.get("decisions", []):
        for i, link in enumerate(d.get("code", [])):
            start, end = link["lines"]
            file = root / link["path"]
            if not file.is_file():
                out.append(LinkState(d["id"], i, link, "missing", f"{link['path']}: file not found"))
                continue
            try:
                lines = code_lines(file)
            except (OSError, ValueError, KeyError) as e:
                out.append(LinkState(d["id"], i, link, "missing", f"{link['path']}: cannot read ({e})"))
                continue
            if start > end or end > len(lines):
                out.append(LinkState(d["id"], i, link, "bad-range",
                                     f"lines {start}-{end} do not exist ({link['path']} has {len(lines)} lines)"))
                continue
            sha = digest(lines[start - 1:end])
            stored = link.get("sha256")
            found = "expect" not in link or _squash(link["expect"]) in _squash("\n".join(lines[start - 1:end]))
            if stored is None:
                out.append(LinkState(d["id"], i, link, "unstamped", "", sha, expect_found=found))
            elif stored == sha:
                out.append(LinkState(d["id"], i, link, "ok", "", sha, expect_found=found))
            else:
                moved = find_block(lines, end - start + 1, stored)
                out.append(LinkState(d["id"], i, link, "drift", lines[start - 1].strip()[:120], sha, moved, found))
    return out


def _cycles(deps: dict[str, list[str]]) -> list[list[str]]:
    """Each dependency cycle once, as the list of ids along it."""
    cycles, state, stack = [], {}, []

    def visit(n):
        state[n] = "active"
        stack.append(n)
        for m in deps.get(n, []):
            if m not in deps:
                continue
            if state.get(m) == "active":
                cycles.append(stack[stack.index(m):] + [m])
            elif m not in state:
                visit(m)
        stack.pop()
        state[n] = "done"

    for n in deps:
        if n not in state:
            visit(n)
    return cycles


def check(map_path: Path) -> list[Issue]:
    """All problems in the map at map_path. Schema errors stop the other checks."""
    map_path = Path(map_path)
    try:
        data = load_map(map_path)
    except MapError as e:
        return [Issue("error", str(map_path), str(e))]
    issues = schema_issues(data)
    if issues:
        return issues

    decisions = data["decisions"]
    ids = [d["id"] for d in decisions]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        issues.append(Issue("error", i, "duplicate decision id"))
    stage_ids = [s["id"] for s in data.get("stages", [])]
    for s in sorted({s for s in stage_ids if stage_ids.count(s) > 1}):
        issues.append(Issue("error", f"stages.{s}", "duplicate stage id"))

    known = set(ids)
    for d in decisions:
        if "stages" in data and "stage" in d and d["stage"] not in stage_ids:
            issues.append(Issue("error", d["id"], f"unknown stage {d['stage']!r}"))
        for dep in d.get("depends_on", []):
            if dep not in known:
                issues.append(Issue("error", d["id"], f"depends on unknown decision {dep!r}"))
        chosen = [o for o in d["options"] if o["state"] == "chosen"]
        if d["status"] == "decided" and len(chosen) != 1:
            issues.append(Issue("error", d["id"], f"decided, so exactly one option must be chosen ({len(chosen)} are)"))
        if d["status"] == "open":
            if chosen:
                issues.append(Issue("error", d["id"], f"open, so no option may be chosen ({len(chosen)} are)"))
            issues.append(Issue("warning", d["id"], "open: waiting for a person to decide"))

    deps = {d["id"]: d.get("depends_on", []) for d in decisions}
    for cycle in _cycles(deps):
        issues.append(Issue("error", cycle[0], "dependency cycle: " + " -> ".join(cycle)))

    for ls in link_states(map_path, data):
        where = f"{ls.decision}: code[{ls.index}] {ls.label}"
        if ls.state in ("missing", "bad-range"):
            issues.append(Issue("error", f"{ls.decision}: code[{ls.index}]", ls.message))
        if ls.state in ("ok", "unstamped") and not ls.expect_found:
            issues.append(Issue("warning", where, f"expect text not found in the linked lines: {ls.link['expect']}"))
        if ls.state == "unstamped":
            issues.append(Issue("warning", where, "not stamped: no person has reviewed these lines yet"))
        elif ls.state == "drift":
            hint = (f"; the reviewed lines are now at {ls.moved_to[0]}-{ls.moved_to[1]}, update lines" if ls.moved_to
                    else f"; line {ls.link['lines'][0]} now reads: {ls.message}")
            issues.append(Issue("error", where, "out of sync: the code changed since it was stamped" + hint))

    base = map_path.parent
    for key in ("changelog",):
        if key in data and not (base / data[key]).is_file():
            issues.append(Issue("warning", key, f"{data[key]} not found"))
    for p in data.get("papers", []):
        if not (base / p).is_file():
            issues.append(Issue("warning", "papers", f"{p} not found"))
    return issues
