"""
AIfa-BioBench — extra topology of the REAL FlyWire v783 connectome.

Same graph as bench/connectome_real_metrics.py: undirected, pairs with >= 5 synapses.
Adds what the catalogue cards cite but never computed on real data:
  * small-world index sigma = (C/C_rand) / (L/L_rand), where C_rand and L_rand are
    MEASURED on an Erdos-Renyi graph with the same number of nodes and edges
    (same sampling method as for the real graph), not taken from formulas;
  * <k^2>/<k> and the Cohen et al. random-failure threshold f_c = 1 - 1/(<k^2>/<k> - 1);
  * k-core decomposition: k_max and size of the innermost core;
  * robustness: giant-component fraction after removing nodes at random and by
    highest degree (targeted attack).

Data: bench/data/ (see bench/data/README.md), Zenodo 10.5281/zenodo.10676866, CC BY 4.0.
Usage: python bench/connectome_topology_extra.py
"""
import argparse, json, os, platform, sys, time
from collections import deque

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.csgraph import connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def build_graph(threshold):
    root_ids = np.load(os.path.join(DATA, "proofread_root_ids_783.npy"))
    df = pd.read_feather(os.path.join(DATA, "proofread_connections_783.feather"),
                         columns=["pre_pt_root_id", "post_pt_root_id", "syn_count"])
    pairs = df.groupby(["pre_pt_root_id", "post_pt_root_id"], sort=False)["syn_count"].sum()
    strong = pairs[pairs >= threshold]
    index = pd.Series(np.arange(len(root_ids)), index=np.asarray(root_ids))
    r = index.reindex(strong.index.get_level_values(0)).to_numpy()
    c = index.reindex(strong.index.get_level_values(1)).to_numpy()
    ok = ~(np.isnan(r) | np.isnan(c))
    r, c = r[ok].astype(np.int64), c[ok].astype(np.int64)
    n = len(root_ids)
    A = sparse.coo_matrix((np.ones(len(r), dtype=np.int8), (r, c)), shape=(n, n)).tocsr()
    U = ((A + A.T) > 0).astype(np.int8).tocsr()
    U.setdiag(0); U.eliminate_zeros()
    keep = np.flatnonzero(np.diff(U.indptr) > 0)          # drop isolated nodes
    return U[keep][:, keep].tocsr()


def er_graph(n, m, rng):
    """Erdos-Renyi G(n, m): m distinct undirected edges, no self-loops."""
    got = set()
    while len(got) < m:
        k = int((m - len(got)) * 1.1) + 1000
        a = rng.randint(0, n, k); b = rng.randint(0, n, k)
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        key = lo[lo != hi].astype(np.int64) * n + hi[lo != hi]
        got.update(key.tolist())
    key = np.fromiter(got, dtype=np.int64)[:m]
    lo, hi = key // n, key % n
    A = sparse.coo_matrix((np.ones(m, dtype=np.int8), (lo, hi)), shape=(n, n))
    return ((A + A.T) > 0).astype(np.int8).tocsr()


def clustering(U, sample):
    out = []
    for v in sample:
        nb = U.indices[U.indptr[v]:U.indptr[v + 1]]
        k = len(nb)
        if k < 2:
            continue
        out.append(U[nb][:, nb].nnz / (k * (k - 1)))
    return float(np.mean(out))


def path_length(U, sources):
    n = U.shape[0]; s_sum = 0; s_cnt = 0
    for s in sources:
        dist = np.full(n, -1, dtype=np.int32); dist[s] = 0
        q = deque([s])
        while q:
            v = q.popleft()
            for u in U.indices[U.indptr[v]:U.indptr[v + 1]]:
                if dist[u] < 0:
                    dist[u] = dist[v] + 1; q.append(u)
        d = dist[dist > 0]; s_sum += int(d.sum()); s_cnt += len(d)
    return s_sum / s_cnt


def k_core(U):
    """Peeling: returns (k_max, size of the k_max-core)."""
    alive = np.ones(U.shape[0], dtype=bool)
    deg = np.diff(U.indptr).astype(np.int64)
    k, last_size = 0, int(alive.sum())
    while alive.any():
        k += 1
        while True:
            drop = alive & (deg < k)
            if not drop.any():
                break
            alive[drop] = False
            # each dropped node lowers its neighbours' degree
            deg -= np.asarray(U[:, drop].sum(axis=1)).ravel().astype(np.int64)
        if alive.any():
            last_size = int(alive.sum())
        else:
            return k - 1, last_size
    return k, last_size


def giant_fraction(U, removed_mask):
    keep = np.flatnonzero(~removed_mask)
    sub = U[keep][:, keep]
    _, lab = connected_components(sub, directed=False)
    return float(np.bincount(lab).max() / U.shape[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=5)
    ap.add_argument("--clust-sample", type=int, default=3000)
    ap.add_argument("--path-sources", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", default=os.path.join(HERE, "..", "results", "connectome_topology_extra.json")
                    if os.path.isdir(os.path.join(HERE, "..", "results")) else os.path.join(HERE, "results", "connectome_topology_extra.json"))
    a = ap.parse_args()
    t0 = time.time()
    rng = np.random.RandomState(a.seed)

    U = build_graph(a.threshold)
    n = U.shape[0]; m = U.nnz // 2
    deg = np.diff(U.indptr).astype(np.float64)
    k1, k2 = deg.mean(), (deg ** 2).mean()
    kappa = k2 / k1
    f_c = 1 - 1 / (kappa - 1)

    sample = rng.choice(n, size=min(a.clust_sample, n), replace=False)
    sources = rng.choice(n, size=min(a.path_sources, n), replace=False)
    C = clustering(U, sample); L = path_length(U, sources)
    R = er_graph(n, m, rng)
    C_r = clustering(R, sample); L_r = path_length(R, sources)
    sigma = (C / C_r) / (L / L_r)

    kmax, core_size = k_core(U)

    rob = {"random": {}, "targeted_by_degree": {}}
    order = np.argsort(-deg)
    for f in (0.01, 0.05, 0.10, 0.30, 0.50):
        mask = np.zeros(n, dtype=bool); mask[rng.choice(n, int(f * n), replace=False)] = True
        rob["random"][str(f)] = giant_fraction(U, mask)
        mask = np.zeros(n, dtype=bool); mask[order[:int(f * n)]] = True
        rob["targeted_by_degree"][str(f)] = giant_fraction(U, mask)

    res = {
        "benchmark": "AIfa-BioBench — extra topology of the real FlyWire v783 connectome",
        "graph": {"threshold_synapses": a.threshold, "nodes_with_edges": int(n), "undirected_edges": int(m),
                  "mean_degree": float(k1), "max_degree": int(deg.max())},
        "small_world": {"C": C, "L": L, "C_rand_measured": C_r, "L_rand_measured": L_r, "sigma": sigma,
                        "clustering_sample_nodes": int(len(sample)), "path_bfs_sources": int(len(sources)),
                        "random_graph": "Erdos-Renyi G(n, m) with the same n and m, same sampling"},
        "percolation": {"k2_over_k": float(kappa), "f_c_random_failure_cohen2000": float(f_c)},
        "k_core": {"k_max": int(kmax), "innermost_core_size": int(core_size)},
        "robustness_giant_component_fraction": rob,
        "params": vars(a),
        "provenance": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                       "processor": platform.processor(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "runtime_s": round(time.time() - t0, 1)},
    }
    os.makedirs(os.path.dirname(a.output), exist_ok=True)
    with open(a.output, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
