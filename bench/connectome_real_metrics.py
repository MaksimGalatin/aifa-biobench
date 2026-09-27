# -*- coding: utf-8 -*-
"""
Real FlyWire v783 connectome metrics (AIfa-BioBench).

Unlike the earlier suite scripts, this one reads the REAL connectome:
  proofread_connections_783.feather  (Zenodo 10.5281/zenodo.10676866, CC BY 4.0)
  proofread_root_ids_783.npy
Download both into bench/data/ (see bench/data/README.md). md5 sums are
checked against the Zenodo record before anything is computed.

Measures (everything that the /acr and /digital pages state about the graph):
  * neurons, edge rows, unique directed pairs, total synapses
  * edges surviving the standard >=5-synapse threshold
  * synapse-weight distribution (lognormal fit + KS distance)
  * average local clustering (undirected, thresholded) on a random node sample
  * characteristic path length (undirected, thresholded) by BFS from a sample
Samples use a fixed seed; sample sizes are written to the result file.
"""
import argparse, hashlib, json, os, sys, time, platform
from collections import deque

import numpy as np
import pandas as pd
from scipy import sparse, stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
ZENODO_MD5 = {
    "proofread_connections_783.feather": None,  # filled from data/zenodo_10676866.json
    "proofread_root_ids_783.npy": None,
}


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def check_files():
    rec = json.load(open(os.path.join(DATA, "zenodo_10676866.json"), encoding="utf-8"))
    sums = {f["key"]: f["checksum"].split(":")[1] for f in rec["files"]}
    out = {}
    for name in ZENODO_MD5:
        p = os.path.join(DATA, name)
        if not os.path.exists(p):
            sys.exit(f"missing {p} — download it from Zenodo 10676866 first")
        got = md5(p)
        if got != sums[name]:
            sys.exit(f"md5 mismatch for {name}: {got} != {sums[name]}")
        out[name] = got
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=5)
    ap.add_argument("--clust-sample", type=int, default=3000)
    ap.add_argument("--path-sources", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", default=os.path.join(HERE, "results", "connectome_real_metrics.json"))
    a = ap.parse_args()
    t_start = time.time()
    sums = check_files()

    root_ids = np.load(os.path.join(DATA, "proofread_root_ids_783.npy"))
    df = pd.read_feather(os.path.join(DATA, "proofread_connections_783.feather"))
    cols = list(df.columns)
    pre, post = df["pre_pt_root_id"].to_numpy(), df["post_pt_root_id"].to_numpy()
    syn = df["syn_count"].to_numpy()

    # collapse rows that differ only by neuropil into one directed pair
    pairs = pd.DataFrame({"pre": pre, "post": post, "syn": syn}).groupby(["pre", "post"], sort=False)["syn"].sum()
    n_pairs = int(len(pairs))
    total_syn = int(syn.sum())
    strong = pairs[pairs >= a.threshold]

    # weight distribution of directed pairs
    w = pairs.to_numpy().astype(float)
    shape, loc, scale = stats.lognorm.fit(w, floc=0)
    ks = stats.kstest(w, "lognorm", args=(shape, loc, scale)).statistic

    # undirected thresholded graph as CSR
    ids = np.asarray(root_ids)
    index = pd.Series(np.arange(len(ids)), index=ids)
    s_pre = index.reindex(strong.index.get_level_values(0)).to_numpy()
    s_post = index.reindex(strong.index.get_level_values(1)).to_numpy()
    ok = ~(np.isnan(s_pre) | np.isnan(s_post))
    r, c = s_pre[ok].astype(np.int64), s_post[ok].astype(np.int64)
    n = len(ids)
    A = sparse.coo_matrix((np.ones(len(r), dtype=np.int8), (r, c)), shape=(n, n)).tocsr()
    U = ((A + A.T) > 0).astype(np.int8).tocsr()
    U.setdiag(0); U.eliminate_zeros()
    deg = np.diff(U.indptr)
    n_undirected_edges = int(U.nnz // 2)

    rng = np.random.RandomState(a.seed)
    nodes = np.flatnonzero(deg >= 2)
    sample = rng.choice(nodes, size=min(a.clust_sample, len(nodes)), replace=False)
    cl = []
    for v in sample:
        nb = U.indices[U.indptr[v]:U.indptr[v + 1]]
        k = len(nb)
        sub = U[nb][:, nb]
        cl.append(sub.nnz / (k * (k - 1)))
    avg_clust = float(np.mean(cl))

    connected = np.flatnonzero(deg > 0)
    sources = rng.choice(connected, size=min(a.path_sources, len(connected)), replace=False)
    dist_sum, dist_cnt, reach = 0, 0, []
    for s in sources:
        dist = np.full(n, -1, dtype=np.int32); dist[s] = 0
        q = deque([s])
        while q:
            v = q.popleft()
            for u in U.indices[U.indptr[v]:U.indptr[v + 1]]:
                if dist[u] < 0:
                    dist[u] = dist[v] + 1; q.append(u)
        d = dist[dist > 0]
        dist_sum += int(d.sum()); dist_cnt += len(d); reach.append(len(d))
    char_path = dist_sum / dist_cnt

    res = {
        "benchmark": "AIfa-BioBench — real FlyWire v783 connectome metrics",
        "source": {"zenodo_record": "10.5281/zenodo.10676866", "license": "CC BY 4.0", "md5": sums, "columns": cols},
        "counts": {
            "proofread_neurons": int(len(root_ids)),
            "edge_rows_by_neuropil": int(len(df)),
            "unique_directed_pairs": n_pairs,
            "total_synapses": total_syn,
            f"directed_pairs_ge_{a.threshold}_synapses": int(len(strong)),
            f"undirected_edges_ge_{a.threshold}_synapses": n_undirected_edges,
        },
        "weights": {"lognormal_shape": float(shape), "lognormal_scale": float(scale), "ks_distance_vs_lognormal": float(ks),
                    "median_synapses_per_pair": float(np.median(w)), "max_synapses_per_pair": int(w.max())},
        "topology_thresholded_undirected": {
            "avg_local_clustering": avg_clust, "clustering_sample_nodes": int(len(sample)),
            "characteristic_path_length": float(char_path), "path_bfs_sources": int(len(sources)),
            "mean_reachable_nodes_per_source": float(np.mean(reach)),
            "mean_degree": float(deg.mean()), "max_degree": int(deg.max()),
        },
        "params": vars(a),
        "provenance": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                       "platform": platform.platform(), "processor": platform.processor(),
                       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runtime_s": round(time.time() - t_start, 1)},
    }
    os.makedirs(os.path.dirname(a.output), exist_ok=True)
    json.dump(res, open(a.output, "w", encoding="utf-8"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
