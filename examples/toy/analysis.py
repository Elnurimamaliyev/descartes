"""Toy analysis for the Descartes example: do cued trials get faster responses?

Reaction times (RT) are simulated for 20 participants, so the example runs without real data.
Run from any folder: python analysis.py
"""
import math
import random
import statistics

SEED = 7
N_PARTICIPANTS = 20
N_TRIALS = 60

RT_MIN_MS, RT_MAX_MS = 200, 2000
SUMMARY = statistics.median
N_PERMUTATIONS = 10000
ALTERNATIVE = "two-sided"


def simulate(rng):
    """RTs in ms per participant and condition. Cued trials are about 20 ms faster; each condition also has two
    anticipations (< 200 ms) and two lapses (> 2.5 s)."""
    data = []
    for _ in range(N_PARTICIPANTS):
        base = rng.gauss(520, 60)
        participant = {}
        for condition, shift in (("uncued", 0.0), ("cued", -20.0)):
            rts = [rng.lognormvariate(math.log(base + shift), 0.25) for _ in range(N_TRIALS)]
            rts += [rng.uniform(80, 180) for _ in range(2)] + [rng.uniform(2500, 4000) for _ in range(2)]
            participant[condition] = rts
        data.append(participant)
    return data


def window(rts):
    return [rt for rt in rts if RT_MIN_MS <= rt <= RT_MAX_MS]


def within_sd(rts, k=2.5):
    m, s = statistics.mean(rts), statistics.stdev(rts)
    return [rt for rt in rts if abs(rt - m) <= k * s]


def cue_effects(data, exclude=window, summary=SUMMARY):
    """Per participant: summary RT uncued minus summary RT cued, in ms (positive = cued faster)."""
    return [summary(exclude(p["uncued"])) - summary(exclude(p["cued"])) for p in data]


def sign_flip_test(diffs, n_permutations, rng, alternative="two-sided"):
    """Paired permutation test: flip the sign of each participant's difference at random."""
    observed = statistics.mean(diffs)
    count = 0
    for _ in range(n_permutations):
        m = statistics.mean([d if rng.random() < 0.5 else -d for d in diffs])
        count += abs(m) >= abs(observed) if alternative == "two-sided" else m >= observed
    return (count + 1) / (n_permutations + 1)


def report(label, diffs, rng, alternative=ALTERNATIVE):
    p = sign_flip_test(diffs, N_PERMUTATIONS, rng, alternative)
    print(f"{label:<36} cue effect {statistics.mean(diffs):6.1f} ms, p = {p:.4f}, n = {len(diffs)}")


def main():
    data = simulate(random.Random(SEED))
    report("Primary (200-2000 ms window, median)", cue_effects(data), random.Random(SEED))
    print("Alternatives:")
    report("  2.5 SD rule, median", cue_effects(data, exclude=within_sd), random.Random(SEED))
    report("  no exclusion, median", cue_effects(data, exclude=list), random.Random(SEED))
    report("  window, mean", cue_effects(data, summary=statistics.mean), random.Random(SEED))
    report("  no exclusion, mean", cue_effects(data, exclude=list, summary=statistics.mean), random.Random(SEED))
    report("  one-sided (cued faster)", cue_effects(data), random.Random(SEED), alternative="greater")


if __name__ == "__main__":
    main()
