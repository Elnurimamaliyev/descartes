# Instructions for coding agents

This repository records its analysis decisions in a Descartes decision map (`descartes.yaml`). The format is described in `spec/README.md` of the Descartes repository. Follow these rules whenever you work on the analysis.

## When you make or change an analysis decision

An analysis decision is any choice that can change a result: which data to exclude, filter settings, window lengths, the measure and how it is computed, the statistical test, corrections, thresholds, which participants or trials count.

1. Add a card for the decision, or update the existing card.
2. List every option you considered, not only the one you used. Give each option a `state`:
   - `chosen`: the option the code uses (exactly one per decided card)
   - `tested`: you ran it and compared it, but did not use it
   - `rejected`: you ruled it out without running it, or after running it
   - `untried`: you considered it but did not run it
3. Give the chosen option a `reason`. Give other options a reason where you have one.
4. Put numbers in `evidence`, each with its measure and unit, for example `Cue effect 31.0 ms, p = 0.0009, n = 20 participants`. Report the numbers for every option you ran, not only the chosen one.
5. Link the exact lines that implement the chosen option under `code`, with `path`, `lines: [start, end]` and `expect` (the key line as text). Do not add `sha256`.
6. Set `decided_by: agent` and `status: decided`. Set `depends_on` to the ids of earlier decisions this one depends on, and `risk` to how much the result could change if the decision is wrong.

## When you cannot justify a choice

Set `status: open`, mark no option as `chosen`, and explain in `notes` what is unclear and what a person needs to decide. If the code needs a value to run, use one, say so in `notes`, and leave the card open.

## Rules

- Never choose an option because it gives a significant result or a larger effect. Choose on grounds you could state before seeing the result, and say what they are in `reason`.
- Never run `descartes stamp`. A stamp records that a person has reviewed the cards; only a person runs it.
- Do not delete cards or options to hide what you tried. Change the `state` instead.
- Run `descartes check descartes.yaml` before you finish, fix every error, and report the remaining warnings to the person.

## Working on Descartes itself

If this file is in the Descartes repository: run `pytest` before you finish, keep `spec/decision-map.schema.json`, `spec/README.md` and the checks in `src/descartes/check.py` consistent, and keep `descartes check --strict examples/toy/descartes.yaml` passing.
