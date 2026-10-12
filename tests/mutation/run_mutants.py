# ==============================================================================
# AIfa-BioBench: do the tests catch real bugs?
# Copyright (c) 2026 Maksim Galatin & CODE (Code of Digital Eternity) — https://aifa.works
# Licensed under the PolyForm Noncommercial License 1.0.0 — commercial use only under a written licence:
# contact@codeofdigitaleternity.com
#
# 12.10.2026. Тест, который проходит всегда, ничего не доказывает. Здесь в код по очереди вносятся десять
# намеренных ошибок (mutant_plugin.py) и проверяется, что каждую ловит хотя бы один тест, а без ошибок
# проходят все. Код репозитория не меняется: ошибка подставляется в память процесса pytest.
# ==============================================================================
"""python tests/mutation/run_mutants.py   — exit 0 if the clean run passes and every mutant is caught."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

MUTANTS = {
    1: "Hamming distance of one row off by one",
    2: "NDCG: ideal DCG summed over k+1 positions",
    3: "Merkle: inner node hashed with the leaf prefix 0x00",
    4: "Merkle: odd last node duplicated instead of promoted",
    5: "Merkle: proof verification ignores the fn == sn rule of RFC 9162",
    6: "clustering divided by k^2 instead of k(k-1)",
    7: "k-core reports k_max + 1",
    8: "Aho-Corasick without failure links",
    9: "README check rounds half-to-even instead of half-up",
    10: "path length silently drops one BFS source",
}


def run(n):
    env = dict(os.environ, MUTANT=str(n), PYTHONPATH=HERE + os.pathsep + os.environ.get("PYTHONPATH", ""))
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "mutant_plugin", "-p", "no:cacheprovider",
                        os.path.join(ROOT, "tests")], cwd=ROOT, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    failed = sorted(set(re.findall(r"^FAILED (\S+)", p.stdout, re.M)))
    summary = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]
    return p.returncode, failed, summary


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    code, failed, summary = run(0)
    clean_ok = code == 0
    print(f"clean run: {'PASS' if clean_ok else 'FAIL'} — {summary}")
    caught = 0
    for n, what in MUTANTS.items():
        code, failed, summary = run(n)
        ok = code != 0 and bool(failed)
        caught += ok
        print(f"mutant {n:>2} {'CAUGHT ' if ok else 'MISSED '} {what}")
        for f in failed:
            print(f"            by {f}")
    print(f"\n{caught} of {len(MUTANTS)} deliberate bugs caught; clean run {'passes' if clean_ok else 'FAILS'}.")
    return 0 if clean_ok and caught == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
