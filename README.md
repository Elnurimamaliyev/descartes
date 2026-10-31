# Descartes

Descartes records the analysis decisions of a data analysis as cards in a YAML file that lives next to the code. Each card holds one question (for example, which reaction times to exclude), every option that was considered, which option was chosen, the reason, and the numbers behind it.

It is built for analyses written with LLM coding agents. An agent can make dozens of choices in one session, and most of them end up buried in code and chat logs. Descartes asks the agent to write each choice down as a card, so a person can review the decisions instead of reconstructing them.

Each card links to the exact lines of code that implement it, with a hash of those lines. When the code changes after a person reviewed it, `descartes check` reports the card as out of sync.

## Status

Early prototype, version 0.1. The map format and the command line tool may still change. Descartes has been used on one neuroscience study with 39 recorded decisions.

## Quick start

Requires Python 3.9 or newer. The only dependencies are PyYAML and jsonschema.

```sh
git clone https://github.com/Elnurimamaliyev/descartes.git
cd descartes
pip install -e .
descartes check examples/toy/descartes.yaml
```

```
descartes check: 0 errors, 0 warnings (examples/toy/descartes.yaml)
```

The toy example in `examples/toy/` is a small reaction-time analysis on simulated data (`python examples/toy/analysis.py`) and its decision map.

## Drift check demo

Change the exclusion window in `examples/toy/analysis.py` from 200 ms to 150 ms and run the check again:

```sh
sed -i.bak 's/RT_MIN_MS, RT_MAX_MS = 200, 2000/RT_MIN_MS, RT_MAX_MS = 150, 2000/' examples/toy/analysis.py
descartes check examples/toy/descartes.yaml
```

```
error: rt-window: code[0] analysis.py:14: out of sync: the code changed since it was stamped; line 14 now reads: RT_MIN_MS, RT_MAX_MS = 150, 2000
descartes check: 1 error, 0 warnings (examples/toy/descartes.yaml)
```

The exit code is 1, so the check can run in a pre-commit hook or in CI. After a person has reviewed the change and updated the card, `descartes stamp` records the new hash. Restore the example with `mv examples/toy/analysis.py.bak examples/toy/analysis.py`.

## Example card

```yaml
- id: rt-summary
  question: Per-participant RT summary
  status: decided
  stage: summary
  decided_by: agent
  risk: low
  depends_on: [rt-window]
  code:
    - path: analysis.py
      lines: [15, 15]
      expect: SUMMARY = statistics.median
      sha256: d3c6b67dea029e672174d9493bc01bcf8ebf5d1b48f960643b6af058341e7089
  options:
    - value: Median
      state: chosen
      reason: RT distributions are skewed to the right; the median is robust to the long tail.
      evidence: Cue effect 31.0 ms, p = 0.0009.
    - value: Mean
      state: tested
      reason: Pulled by the right tail. Its p-value is smaller, which is not a reason to choose it.
      evidence: Cue effect 27.3 ms, p = 0.0005 (200-2000 ms window).
```

The format is described in [spec/README.md](spec/README.md) and defined by the JSON Schema in [spec/decision-map.schema.json](spec/decision-map.schema.json).

## Commands

| Command | What it does |
|---|---|
| `descartes check <map> [--strict]` | Validates the map and checks its code links. Exit 1 on errors, or on warnings with `--strict`. |
| `descartes open <map>` | Lists open decisions, and decisions made by an agent whose code has not been reviewed since it changed. |
| `descartes stamp <map>` | Records the current hash of every code link. Run it only after a person has reviewed the cards. |

## What check verifies

Errors:

- The map matches the JSON Schema (draft 2020-12), and the YAML has no duplicate keys.
- Decision ids are unique, and every stage named by a decision is listed under `stages`.
- Every id in `depends_on` exists, and there are no dependency cycles.
- A decided card has exactly one chosen option; an open card has none.
- Every linked file exists and contains the linked line range.
- The hash of the linked lines matches the stored `sha256`. Trailing whitespace is ignored. If the reviewed lines only moved, check says where they are now.

Warnings:

- A card is open (waiting for a person).
- A code link has no `sha256` yet (no person has reviewed it).
- The `expect` text of a link is not in the linked lines.

## Use with coding agents

Copy [AGENTS.md](AGENTS.md) into your analysis repository, or point your agent's instruction file to it. It tells the agent to write a card for every analysis decision it makes or changes, list all options it considered, put numbers in the evidence, link the exact lines, mark its own decisions with `decided_by: agent`, leave a card open when it cannot justify a choice, and run `descartes check` before it finishes. It also tells the agent never to run `descartes stamp`, because a stamp means a person has reviewed the cards.

## Roadmap

- Write maps automatically from an agent's session and code changes.
- A multiverse runner that reruns the analysis with the recorded alternatives (tested and untried options) and reports how much the result changes.
- A visual viewer for maps: cards by stage, dependency graph, open and out-of-sync cards.
- Plugins for coding agents that create and update cards while they work.
- A controlled study of whether people catch more agent errors when they review a decision map than when they review code and chat logs.

## License

Apache License 2.0. See [LICENSE](LICENSE). Copyright 2026 Elnur Imamaliyev.
