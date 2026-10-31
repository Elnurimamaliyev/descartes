# Decision map format, version 0.1

A decision map is a YAML file, usually `descartes.yaml` at the root of an analysis repository. [decision-map.schema.json](decision-map.schema.json) (JSON Schema, draft 2020-12) defines it; this page explains it. `descartes check` validates a map against the schema and runs the checks the schema cannot express (marked "checked by descartes check" below).

## Top level

| Field | Required | Meaning |
|---|---|---|
| `descartes` | yes | Format version, the string `"0.1"`. |
| `study` | yes | `title` (required), `repository` (URL of the analysis code), `agent` (the coding agent that works on it). |
| `decisions` | yes | List of decision cards. |
| `root` | no | Folder that code paths are relative to, relative to the map file. Defaults to the map's folder. |
| `stages` | no | Pipeline stages in order, each with `id`, `name` and optional `notebook`. When present, every decision's `stage` must be one of these ids (checked by descartes check). |
| `changelog` | no | Markdown file whose entries mention decisions as `[decision-id]`. |
| `papers` | no | Paper maps: decision maps of published analyses to compare against. |
| `paper` | no | Only in a paper map: `title`, `authors`, `year`, `doi`, `pdf`, `stages` (`own` or `main`), `reader`. |

## Decision

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Kebab-case, e.g. `rt-window`. Unique in the map (checked by descartes check). |
| `question` | yes | The choice as a short noun phrase. |
| `status` | yes | `decided`: exactly one option is chosen. `open`: waiting for a person; no option is chosen (checked by descartes check). |
| `options` | yes | At least one option. |
| `stage` | no | Id of a stage. |
| `decided_by` | no | `agent` or `human`. |
| `risk` | no | `low`, `medium` or `high`: how much the result could change if the decision is wrong. |
| `depends_on` | no | Ids of earlier decisions this one depends on. They must exist and must not form a cycle (checked by descartes check). |
| `code` | no | Code links (below). |
| `notes` | no | Free text. |
| `date` | no | `YYYY-MM-DD`. |
| `notebook` | no | Notebook or script where the decision is made. |
| `matches` | no | Only in a paper map: ids of decisions in the main map that ask the same question. |

## Option

| Field | Required | Meaning |
|---|---|---|
| `value` | yes | The option, as text, a number or a boolean. |
| `state` | yes | `chosen` (used), `tested` (run and compared, not used), `rejected` (ruled out), `untried` (considered, not run). |
| `reason` | no | Why the option was chosen, tested, rejected or not tried. |
| `evidence` | no | The numbers behind the option, each with its measure and unit. |

## Code link

| Field | Required | Meaning |
|---|---|---|
| `path` | yes | File path relative to `root`. The file must exist (checked by descartes check). |
| `lines` | yes | `[start, end]`, 1-based and inclusive. The range must exist in the file (checked by descartes check). |
| `sha256` | no | Hash of the linked lines when a person last reviewed them. Absent means not reviewed yet. |
| `expect` | no | The key line as a person reads it. For orientation; a warning is shown when it is not in the linked lines. |

### The hash

`sha256` is the SHA-256 of the linked lines, with trailing whitespace (including `\r`) removed from each line, joined with `\n`, encoded as UTF-8, written as 64 lower-case hex digits. Changes to trailing whitespace or line endings do not change it; any other change, including indentation, does.

In a Jupyter notebook (`.ipynb`), lines are counted over the source of its code cells only, in order. Markdown cells and outputs do not count, so rerunning a notebook does not move or change a link.

`descartes stamp` writes the hashes. It only edits the `sha256` values, so comments and layout in the map are kept. If the reviewed lines only moved, it refuses to stamp that link until `lines` is updated.

## Extensions

Fields not listed here are errors, except fields whose names start with `x-`, which are allowed on the map, `study`, stages, decisions, options, code links and `paper`.
