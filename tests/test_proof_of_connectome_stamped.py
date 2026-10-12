# Заверенный proof_of_connectome.py: детерминизм (тот же корень, что в results/) и честная запись его слабости.
import json
import os

from conftest import RESULTS
from proof_of_connectome import merkle_root_of_list, run_benchmark


def test_stamped_root_is_reproduced():
    stamped = json.load(open(os.path.join(RESULTS, "proof_of_connectome_result.json"), encoding="utf-8"))
    cfg = stamped["configuration"]
    fresh = run_benchmark(n_neurons=cfg["n_neurons"], n_neuropils=cfg["n_neuropils"], seed=cfg["seed"])
    assert fresh["metrics"]["final_root_sha256"] == stamped["metrics"]["final_root_sha256"]
    assert fresh["metrics"]["tampering_detection_rate"] == 1.0
    assert fresh["metrics"]["single_subtree_verify_correct"] is True


def test_known_weakness_duplicate_last_leaf():
    # класс CVE-2012-2459: нечётный последний узел дублируется, поэтому [a,b,c] и [a,b,c,c] неразличимы.
    # Тест фиксирует слабость, а не одобряет её; исправленная схема — bench/merkle_rfc6962.py
    a, b, c = "aa", "bb", "cc"
    assert merkle_root_of_list([a, b, c]) == merkle_root_of_list([a, b, c, c])
