# Открытая арена поиска (bench/open_arena.py): popcount, метрики на ручных примерах, точный перебор,
# воспроизведение заверенной строки Sign-LSH, детерминизм, подключение своего метода и загрузка .npy.
import json
import os
import sys
import textwrap

import numpy as np
import pytest

from conftest import RESULTS
import open_arena as oa


def test_hamming_matches_unpackbits_both_paths():
    rng = np.random.RandomState(0)
    for nbytes in (1, 7, 8, 16, 256):                 # 7 — путь через таблицу, кратное 8 — через bitwise_count
        codes = rng.randint(0, 256, size=(300, nbytes)).astype(np.uint8)
        q = rng.randint(0, 256, size=nbytes).astype(np.uint8)
        want = np.unpackbits(np.bitwise_xor(codes, q), axis=1).sum(axis=1)
        assert np.array_equal(oa.hamming_to_all(codes, q), want), nbytes


def test_recall_and_ndcg_on_hand_computed_cases():
    gt = [np.arange(10)]
    assert oa.recall_ndcg([np.arange(10)], gt, 10) == (1.0, 1.0)
    assert oa.recall_ndcg([np.arange(100, 110)], gt, 10) == (0.0, 0.0)
    # попадания на позициях 0 и 2 из 10: recall 0.2, DCG = 1/log2(2) + 1/log2(4) = 1.5
    r, n = oa.recall_ndcg([np.array([0, 50, 1, 51, 52, 53, 54, 55, 56, 57])], gt, 10)
    idcg = sum(1 / np.log2(i + 2) for i in range(10))
    assert r == pytest.approx(0.2) and n == pytest.approx(1.5 / idcg)
    # пустой ответ (многотабличный LSH без кандидатов) — ноль, а не ошибка
    assert oa.recall_ndcg([np.array([], dtype=np.int64)], gt, 10) == (0.0, 0.0)


def test_exact_method_finds_every_true_neighbour():
    X, Q = oa.make_gaussian(3000, 64, 40, seed=1)
    gt = oa.ground_truth(X, Q, 10)
    row = oa.evaluate(oa.Exact(), X, Q, gt, 10)
    assert row["recall_at_10_pct"] == 100.0 and row["ndcg_at_10"] == 1.0


def test_queries_are_not_copies_of_indexed_vectors():
    for make in (oa.make_gaussian, oa.make_clustered):
        X, Q = make(2000, 32, 50, 3)
        d = np.linalg.norm(X[None, :, :] - Q[:, None, :], axis=2).min(axis=1)
        assert d.min() > 1e-3, make.__name__


def test_vectors_are_unit_length():
    for make in (oa.make_gaussian, oa.make_clustered):
        X, Q = make(500, 16, 20, 5)
        assert np.allclose(np.linalg.norm(X, axis=1), 1, atol=1e-5)
        assert np.allclose(np.linalg.norm(Q, axis=1), 1, atol=1e-5)


def test_stamped_sign_lsh_row_is_reproduced():
    # строка Sign-LSH заверенного раздела 2 (results/binary_arena_results.json): 25 000 x 512, 100 запросов, seed 42
    stamped = {r["method"]: r for r in json.load(open(os.path.join(RESULTS, "binary_arena_results.json")))}
    s = stamped["Sign-LSH / BQ 1-Bit"]
    res = oa.run(oa.parser().parse_args(["--methods", "signlsh"]))
    row = res["results"][0]
    # на машине замера совпадение точное; на другой библиотеке BLAS знак проекций около нуля может уйти,
    # поэтому допуск — один процентный пункт полноты и 0.01 NDCG
    assert abs(row["recall_at_10_pct"] - s["recall_at_10_pct"]) <= 1.0
    assert abs(row["ndcg_at_10"] - s["ndcg_at_10"]) <= 0.01


def test_runs_are_deterministic():
    args = ["--n", "4000", "--dim", "64", "--queries", "30", "--methods", "signlsh,multitable", "--bits", "256"]
    a = oa.run(oa.parser().parse_args(args))["results"]
    b = oa.run(oa.parser().parse_args(args))["results"]
    for x, y in zip(a, b):
        assert x["recall_at_10_pct"] == y["recall_at_10_pct"] and x["ndcg_at_10"] == y["ndcg_at_10"]


def test_larger_pool_never_lowers_sign_lsh_recall():
    X, Q = oa.make_gaussian(5000, 64, 40, seed=2)
    gt = oa.ground_truth(X, Q, 10)
    recalls = [oa.evaluate(oa.SignLSH(bits=256, pool=p), X, Q, gt, 10)["recall_at_10_pct"] for p in (20, 100, 500, 5000)]
    assert recalls == sorted(recalls) and recalls[-1] == 100.0     # пул на всю базу = точный перебор


def test_plug_in_method_from_module(tmp_path, monkeypatch):
    (tmp_path / "my_index.py").write_text(textwrap.dedent("""
        import numpy as np
        class FirstRows:
            name = "first rows (deliberately bad)"
            def build(self, X):
                self.n = len(X)
            def search(self, q, k):
                return np.arange(k)
    """), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    res = oa.run(oa.parser().parse_args(["--n", "1000", "--dim", "16", "--queries", "10",
                                         "--methods", "exact,my_index:FirstRows"]))
    names = [r["method"] for r in res["results"]]
    assert names == ["Exact brute force (float32)", "first rows (deliberately bad)"]
    assert res["results"][0]["recall_at_10_pct"] == 100.0
    assert res["results"][1]["recall_at_10_pct"] < 100.0
    sys.modules.pop("my_index", None)


def test_npy_dataset_and_json_output(tmp_path):
    X, Q = oa.make_clustered(1500, 24, 15, seed=9)
    np.save(tmp_path / "base.npy", X)
    np.save(tmp_path / "query.npy", Q)
    out = tmp_path / "r.json"
    res = oa.main(["--dataset", "npy", "--base", str(tmp_path / "base.npy"), "--query", str(tmp_path / "query.npy"),
                   "--methods", "exact,signlsh", "--bits", "128", "--output", str(out)])
    saved = json.load(open(out, encoding="utf-8"))
    assert saved["dataset"]["n"] == 1500 and saved["dataset"]["dim"] == 24
    assert saved["results"] == res["results"]
    assert {"python", "numpy", "platform", "utc", "popcount"} <= set(saved["provenance"])


def test_index_smaller_than_k():
    # найдено 12.10.2026: точный перебор падал на argpartition, когда в базе не больше k векторов
    X, Q = oa.make_gaussian(10, 8, 3, seed=4)
    gt = oa.ground_truth(X, Q, 10)
    for method in (oa.Exact(), oa.SignLSH(bits=64, pool=250)):
        row = oa.evaluate(method, X, Q, gt, 10)
        assert row["recall_at_10_pct"] == 100.0, method.name


def test_unknown_method_is_refused():
    with pytest.raises(SystemExit):
        oa.make_method("no-such-method", oa.parser().parse_args([]))
