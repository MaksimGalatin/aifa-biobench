# ==============================================================================
# AIfa-BioBench: Open Retrieval Arena
# Copyright (c) 2026 Maksim Galatin & CODE (Code of Digital Eternity) — https://aifa.works
# Licensed under the PolyForm Noncommercial License 1.0.0 — commercial use only under a written licence:
# contact@codeofdigitaleternity.com
#
# Открытая арена поиска ближайших соседей: точный ответ, честные метрики и ОТКРЫТЫЕ базовые методы
# (точный перебор, Sign-LSH / SimHash, многотабличный LSH). Движок FlyHash здесь не участвует — он в
# платной части; любой свой метод подключается одной строкой (--methods модуль:Класс).
#
# 12.10.2026: написано заново, независимо от закрытого binary_retrieval_arena.py, с тем же генератором
# данных и тем же определением Sign-LSH, чтобы строку Sign-LSH из раздела 2 README мог воспроизвести
# любой. Расстояние Хэмминга считается через popcount по словам, а не через np.unpackbits: второе
# раскладывает каждый бит в отдельный байт (25 000 x 2048 бит = 51 МБ на КАЖДЫЙ запрос).
# ==============================================================================
"""Open retrieval arena: exact ground truth, fair metrics, open baselines, plug-in API.

A method is any class with
    build(self, X: np.ndarray) -> None          # X: (n, dim) float32
    search(self, q: np.ndarray, k: int) -> ids  # q: (dim,) float32, returns k row indices of X
and optionally index_bytes(self) -> int.

Examples
    python bench/open_arena.py                                      # reproduces the Sign-LSH row of README §2
    python bench/open_arena.py --dataset clustered --methods exact,signlsh
    python bench/open_arena.py --dataset npy --base base.npy --query query.npy
    python bench/open_arena.py --methods signlsh,my_pkg.my_module:MyIndex
"""
import argparse
import importlib
import json
import os
import platform
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------------------
# popcount: np.bitwise_count есть с NumPy 2.0; для старых — таблица на 256 значений
# ------------------------------------------------------------------------------
_POP8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def hamming_to_all(codes: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Hamming distance from one packed code q (nbytes,) to every row of codes (n, nbytes), uint8."""
    x = np.bitwise_xor(codes, q)
    if hasattr(np, "bitwise_count") and x.shape[1] % 8 == 0:
        # по 64 бита за раз: (n, nbytes/8) счётчиков вместо (n, nbytes*8) распакованных битов
        return np.bitwise_count(x.view(np.uint64)).sum(axis=1, dtype=np.int64)
    return _POP8[x].sum(axis=1, dtype=np.int64)


# ------------------------------------------------------------------------------
# Данные
# ------------------------------------------------------------------------------
def _unit(a: np.ndarray) -> np.ndarray:
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    return a


def make_gaussian(n, dim, n_queries, seed):
    """Isotropic unit vectors — the generator of the stamped arena (README §2).

    The hardest case for any ANN method: no structure, true neighbours are barely closer than random points.
    """
    rng = np.random.RandomState(seed)
    X = _unit(rng.randn(n, dim).astype(np.float32))
    Q = _unit(rng.randn(n_queries, dim).astype(np.float32))
    return X, Q


def make_clustered(n, dim, n_queries, seed, n_clusters=100, spread=0.8):
    """Gaussian mixture on the unit sphere — has cluster structure, like real embeddings.

    Queries are fresh draws from the same mixture, never copies of indexed vectors.
    """
    rng = np.random.RandomState(seed)
    C = _unit(rng.randn(n_clusters, dim).astype(np.float32))
    noise = np.float32(spread / np.sqrt(dim))
    X = _unit(C[rng.randint(n_clusters, size=n)] + noise * rng.randn(n, dim).astype(np.float32))
    Q = _unit(C[rng.randint(n_clusters, size=n_queries)] + noise * rng.randn(n_queries, dim).astype(np.float32))
    return X, Q


def load_npy(base, query, normalize):
    X = np.load(base).astype(np.float32)
    Q = np.load(query).astype(np.float32)
    if X.ndim != 2 or Q.ndim != 2 or X.shape[1] != Q.shape[1]:
        raise SystemExit(f"base {X.shape} and query {Q.shape} must be 2-D with the same dimension")
    if normalize:
        X, Q = _unit(X), _unit(Q)
    return X, Q


# ------------------------------------------------------------------------------
# Точный ответ и метрики
# ------------------------------------------------------------------------------
def ground_truth(X, Q, k):
    """Exact L2 top-k for every query (same computation as the stamped arena: float32 norm, full sort)."""
    return np.array([np.argsort(np.linalg.norm(X - q, axis=1))[:k] for q in Q])


def recall_ndcg(retrieved, gt, k):
    """Recall@k and NDCG@k with binary relevance (a hit = one of the exact top-k)."""
    rec, ndcg = [], []
    idcg = sum(1.0 / np.log2(r + 2) for r in range(k))
    for r, g in zip(retrieved, gt):
        r = list(r)[:k]
        g = set(int(x) for x in g[:k])
        rec.append(len(set(int(x) for x in r) & g) / k)
        ndcg.append(sum(1.0 / np.log2(i + 2) for i, x in enumerate(r) if int(x) in g) / idcg)
    return float(np.mean(rec)), float(np.mean(ndcg))


# ------------------------------------------------------------------------------
# Открытые базовые методы
# ------------------------------------------------------------------------------
class Exact:
    """Brute-force float32 L2 via one matrix-vector product (a different code path from ground_truth)."""

    name = "Exact brute force (float32)"

    def build(self, X):
        self.X = X
        self.sq = np.einsum("ij,ij->i", X, X)

    def search(self, q, k):
        d = self.sq - 2.0 * (self.X @ q)
        if k >= len(d):                                   # база меньше k: просто полная сортировка
            return np.argsort(d)
        top = np.argpartition(d, k)[:k]
        return top[np.argsort(d[top])]

    def index_bytes(self):
        return self.X.nbytes + self.sq.nbytes


class SignLSH:
    """1-bit sign random projection (Charikar 2002 SimHash / "binary quantisation") + exact rerank of a pool.

    Same definition as the stamped arena: hyperplanes RandomState(seed).randn(bits, dim), code = (x . h >= 0),
    shortlist = `pool` smallest Hamming distances, rerank by exact L2.
    """

    def __init__(self, bits=2048, pool=250, seed=42):
        self.bits, self.pool, self.seed = bits, pool, seed
        self.name = f"Sign-LSH ({bits} bits, pool {pool})"

    def build(self, X):
        self.X = X
        self.H = np.random.RandomState(self.seed).randn(self.bits, X.shape[1]).astype(np.float32)
        self.codes = np.packbits((X @ self.H.T) >= 0.0, axis=1)

    def search(self, q, k):
        # (1, dim) @ H.T — тот же вызов BLAS, что и при построении: иначе у проекций около нуля может
        # разойтись знак из-за другого порядка сложения
        qc = np.packbits((q[None, :] @ self.H.T)[0] >= 0.0)
        d = hamming_to_all(self.codes, qc)
        pool = min(self.pool, len(self.X))
        cand = np.argpartition(d, pool)[:pool] if pool < len(self.X) else np.arange(len(self.X))
        exact = np.linalg.norm(self.X[cand] - q, axis=1)
        return cand[np.argsort(exact)[:k]]

    def index_bytes(self):
        return self.codes.nbytes + self.H.nbytes + self.X.nbytes


class MultiTableLSH:
    """Classic multi-table LSH: `tables` hash tables of `table_bits` sign bits each; union of buckets, exact rerank.

    No random fallback: a query whose buckets are all empty returns nothing (the stamped arena filled such
    queries with unseeded random candidates, which made its 0.1% row unrepeatable).
    """

    def __init__(self, tables=8, table_bits=14, pool=250, seed=42):
        self.tables, self.table_bits, self.pool, self.seed = tables, table_bits, pool, seed
        self.name = f"Multi-table LSH ({tables} x {table_bits} bits)"

    def build(self, X):
        self.X = X
        rng = np.random.RandomState(self.seed)
        self.H = [rng.randn(self.table_bits, X.shape[1]).astype(np.float32) for _ in range(self.tables)]
        self.buckets = []
        for H in self.H:
            keys = np.packbits((X @ H.T) >= 0.0, axis=1)
            t = {}
            for i, key in enumerate(map(bytes, keys)):
                t.setdefault(key, []).append(i)
            self.buckets.append(t)

    def search(self, q, k):
        cand = []
        seen = set()
        for H, t in zip(self.H, self.buckets):
            for i in t.get(bytes(np.packbits((q[None, :] @ H.T)[0] >= 0.0)), ()):
                if i not in seen:
                    seen.add(i)
                    cand.append(i)
            if len(cand) >= self.pool:
                break
        if not cand:
            return np.array([], dtype=np.int64)
        cand = np.array(cand[: self.pool])
        exact = np.linalg.norm(self.X[cand] - q, axis=1)
        return cand[np.argsort(exact)[:k]]

    def index_bytes(self):
        ids = sum(len(v) for t in self.buckets for v in t.values())
        return self.X.nbytes + sum(H.nbytes for H in self.H) + ids * 8


BUILTIN = {"exact": Exact, "signlsh": SignLSH, "multitable": MultiTableLSH}


def make_method(spec, args):
    if spec == "exact":
        return Exact()
    if spec == "signlsh":
        return SignLSH(bits=args.bits, pool=args.pool, seed=args.seed)
    if spec == "multitable":
        return MultiTableLSH(tables=args.tables, table_bits=args.table_bits, pool=args.pool, seed=args.seed)
    if ":" in spec:
        mod, cls = spec.split(":", 1)
        sys.path.insert(0, os.getcwd())
        m = getattr(importlib.import_module(mod), cls)()
        if not getattr(m, "name", None):
            m.name = spec
        return m
    raise SystemExit(f"unknown method {spec!r}: use exact, signlsh, multitable or module:Class")


# ------------------------------------------------------------------------------
# Прогон
# ------------------------------------------------------------------------------
def evaluate(method, X, Q, gt, k):
    t0 = time.perf_counter()
    method.build(X)
    build_s = time.perf_counter() - t0
    lat, out = [], []
    for q in Q:
        t0 = time.perf_counter_ns()
        ids = method.search(q, k)
        lat.append((time.perf_counter_ns() - t0) / 1e6)
        out.append(np.asarray(ids))
    rec, ndcg = recall_ndcg(out, gt, k)
    lat = np.array(lat)
    row = {
        "method": method.name,
        # 6 знаков: двойное округление (0.871492 -> 0.8715 -> 0.872) уже раз исказило README
        f"recall_at_{k}_pct": round(rec * 100, 4),
        f"ndcg_at_{k}": round(ndcg, 6),
        "p50_latency_ms": round(float(np.percentile(lat, 50)), 3),
        "p95_latency_ms": round(float(np.percentile(lat, 95)), 3),
        "mean_latency_ms": round(float(lat.mean()), 3),
        "qps_single_query": round(float(len(Q) / (lat.sum() / 1000.0)), 1),
        "build_time_sec": round(build_s, 3),
    }
    if hasattr(method, "index_bytes"):
        row["index_mb"] = round(method.index_bytes() / 2**20, 2)
    return row


def _git_commit():
    try:
        return subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=10).stdout.strip() or None
    except Exception:
        return None


def run(args):
    if args.dataset == "gaussian":
        X, Q = make_gaussian(args.n, args.dim, args.queries, args.seed)
    elif args.dataset == "clustered":
        X, Q = make_clustered(args.n, args.dim, args.queries, args.seed, args.clusters, args.spread)
    else:
        if not (args.base and args.query):
            raise SystemExit("--dataset npy needs --base and --query")
        X, Q = load_npy(args.base, args.query, args.normalize)
    t0 = time.perf_counter()
    gt = ground_truth(X, Q, args.k)
    gt_s = time.perf_counter() - t0
    rows = [evaluate(make_method(s.strip(), args), X, Q, gt, args.k) for s in args.methods.split(",") if s.strip()]
    return {
        "benchmark": "AIfa-BioBench open retrieval arena",
        "dataset": {"kind": args.dataset, "n": int(X.shape[0]), "dim": int(X.shape[1]), "queries": int(Q.shape[0]),
                    "seed": args.seed, "queries_are_independent_of_index": args.dataset != "npy" or None,
                    **({"clusters": args.clusters, "spread": args.spread} if args.dataset == "clustered" else {})},
        "k": args.k,
        "ground_truth": "exact L2, float32, full sort per query",
        "ground_truth_time_sec": round(gt_s, 3),
        "results": rows,
        "provenance": provenance(),
    }


def provenance(argv=None):
    return {"python": platform.python_version(), "numpy": np.__version__,
            "popcount": "np.bitwise_count" if hasattr(np, "bitwise_count") else "lookup table",
            "platform": platform.platform(), "processor": platform.processor() or platform.machine(),
            "git_commit": _git_commit(), "argv": sys.argv[1:] if argv is None else argv,
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def parser():
    ap = argparse.ArgumentParser(description="AIfa-BioBench open retrieval arena")
    ap.add_argument("--dataset", choices=["gaussian", "clustered", "npy"], default="gaussian")
    ap.add_argument("--n", type=int, default=25000)
    ap.add_argument("--dim", type=int, default=512)
    ap.add_argument("--queries", type=int, default=100)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--clusters", type=int, default=100, help="clustered: number of mixture components")
    ap.add_argument("--spread", type=float, default=0.8, help="clustered: noise norm relative to a centre")
    ap.add_argument("--base", help="npy: (n, dim) float array to index")
    ap.add_argument("--query", help="npy: (q, dim) float array of queries (must not be copies of base rows)")
    ap.add_argument("--normalize", action="store_true", help="npy: scale every vector to unit length")
    ap.add_argument("--methods", default="exact,signlsh,multitable",
                    help="comma list of exact, signlsh, multitable or module:Class")
    ap.add_argument("--bits", type=int, default=2048, help="signlsh: code length")
    ap.add_argument("--pool", type=int, default=250, help="shortlist size reranked exactly")
    ap.add_argument("--tables", type=int, default=8, help="multitable: number of tables")
    ap.add_argument("--table-bits", type=int, default=14, help="multitable: bits per table")
    ap.add_argument("--output", default=None, help="JSON file (default bench/results/open_arena_<dataset>.json)")
    ap.add_argument("--suite", action="store_true",
                    help="run the three configurations quoted in README §8 and write one combined file")
    return ap


# Три конфигурации, числа которых стоят в README §8: изотропные и кластерные 25 000 x 512, кластерные 100 000 x 768
SUITE = [["--dataset", "gaussian"], ["--dataset", "clustered"],
         ["--dataset", "clustered", "--n", "100000", "--dim", "768", "--queries", "200"]]


def run_suite(out):
    runs = []
    for extra in SUITE:
        r = run(parser().parse_args(extra))
        r.pop("provenance")
        runs.append(r)
        d = r["dataset"]
        print(f"{d['kind']} {d['n']:,} x {d['dim']}: " + ", ".join(
            f"{x['method']} {x['recall_at_10_pct']:.2f}% {x['p50_latency_ms']:.2f} ms" for x in r["results"]))
    res = {"benchmark": "AIfa-BioBench open retrieval arena — README §8 suite", "runs": runs,
           "provenance": provenance(["--suite"])}
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:   # LF на любой ОС — хеш файла одинаков везде
        json.dump(res, fh, indent=1)
    print(f"saved: {out}")
    return res


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = parser().parse_args(argv)
    if args.suite:
        return run_suite(args.output or os.path.join(HERE, "results", "open_arena_suite.json"))
    res = run(args)
    out = args.output or os.path.join(HERE, "results", f"open_arena_{args.dataset}.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:   # LF на любой ОС — хеш файла одинаков везде
        json.dump(res, fh, indent=1)
    d = res["dataset"]
    print(f"{d['kind']}: n={d['n']:,} dim={d['dim']} queries={d['queries']} seed={d['seed']}  k={res['k']}")
    print(f"{'method':<34} {'recall':>8} {'ndcg':>7} {'p50 ms':>9} {'p95 ms':>9} {'index MB':>9}")
    rk, nk = "recall_at_%d_pct" % res["k"], "ndcg_at_%d" % res["k"]
    for r in res["results"]:
        print(f"{r['method']:<34} {r[rk]:>7.2f}% {r[nk]:>7.4f} "
              f"{r['p50_latency_ms']:>9.3f} {r['p95_latency_ms']:>9.3f} {r.get('index_mb', float('nan')):>9.2f}")
    print(f"saved: {out}")
    return res


if __name__ == "__main__":
    main()
