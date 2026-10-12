# Автомат Ахо — Корасик из заверенного olfactory_filter_run.py: сверка с наивным поиском всех вхождений.
import json
import os
import random

from conftest import RESULTS
from olfactory_filter_run import DANGER_PATTERNS, AhoCorasick, run_benchmark


def naive(text, patterns):
    """Every (end position, pattern index) where pattern occurs in text — by brute force."""
    out = set()
    for idx, p in enumerate(patterns):
        for s in range(len(text) - len(p) + 1):
            if text[s:s + len(p)] == p:
                out.add((s + len(p) - 1, idx))
    return out


def automaton(text, patterns):
    return {(i, idx) for i, ids in AhoCorasick(patterns).scan(text) for idx in ids}


def test_textbook_example():
    # пример из статьи Aho & Corasick (1975): he, she, his, hers в «ushers»
    pats = ["he", "she", "his", "hers"]
    assert automaton("ushers", pats) == naive("ushers", pats) == {(3, 0), (3, 1), (5, 3)}


def test_matches_naive_on_300_random_inputs():
    # один тест, 300 случайных наборов: число тестов не раздувается, падение называет seed
    for seed in range(300):
        rng = random.Random(seed)
        alphabet = "ab" if seed % 3 == 0 else "abc" if seed % 3 == 1 else "abcdxyz"
        pats = ["".join(rng.choice(alphabet) for _ in range(rng.randint(1, 5))) for _ in range(rng.randint(1, 12))]
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120)))
        assert automaton(text, pats) == naive(text, pats), f"seed {seed}: {pats!r} in {text!r}"


def test_duplicate_and_nested_patterns():
    pats = ["a", "aa", "aaa", "aa"]
    assert automaton("aaaa", pats) == naive("aaaa", pats)


def test_no_match_and_empty_text():
    assert automaton("", DANGER_PATTERNS) == set()
    assert automaton("all good here", ["error", "timeout"]) == set()


def test_danger_patterns_on_log_lines():
    found = automaton("HTTP 503 after timeout: connection refused", DANGER_PATTERNS)
    names = {DANGER_PATTERNS[i] for _, i in found}
    assert names == {"503", "timeout", "connection refused"}


def test_stamped_flag_rate_is_reproduced():
    # доля помеченных строк детерминирована (seed 42) и должна совпасть с заверенным файлом
    stamped = json.load(open(os.path.join(RESULTS, "olfactory_filter_result.json"), encoding="utf-8"))
    fresh = run_benchmark(n_samples=5000, seed=42)
    assert fresh["honest_measurement"]["danger_flagged_pct"] == stamped["honest_measurement"]["danger_flagged_pct"]
    assert fresh["configuration"]["n_patterns"] == stamped["configuration"]["n_patterns"] == 16
