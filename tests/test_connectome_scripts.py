# Три заверенных скрипта коннектома на маленьком синтетическом коннектоме в той же схеме, что FlyWire v783.
# Каждое число сверяется с независимым расчётом: networkx для графа, простые циклы Python для долей медиаторов.
# Скрипты пишут в tmp_path — заверенные файлы results/ тесты не трогают.
import json
import random
import sys

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
nx = pytest.importorskip("networkx")
pytest.importorskip("pyarrow")

import connectome_real_metrics as real
import connectome_topology_extra as topo
import connectome_transmitters as trans

NT = ["gaba_avg", "ach_avg", "glut_avg", "oct_avg", "ser_avg", "da_avg"]


def make_fixture(folder, seed=0, n=60, n_pairs=500):
    rng = random.Random(seed)
    ids = sorted(rng.sample(range(720575940600000000, 720575940700000000), n))
    rows = []
    for _ in range(n_pairs):
        a, b = rng.choice(ids), rng.choice(ids)
        for neuropil in rng.sample(["AL_L", "AL_R", "MB_CA_L", "LH_R", "FB"], rng.randint(1, 3)):
            p = [rng.random() for _ in NT]
            s = sum(p)
            rows.append([a, b, neuropil, rng.randint(1, 9)] + [x / s for x in p])
    rows.append([ids[0], 999, "FB", 50] + [1 / 6] * 6)               # нейрон вне списка root_ids
    rows.append([ids[1], ids[2], "AL_L", 3] + [float("nan")] * 6)    # строка без предсказания медиатора
    df = pd.DataFrame(rows, columns=["pre_pt_root_id", "post_pt_root_id", "neuropil", "syn_count"] + NT)
    df["syn_count"] = df["syn_count"].astype("int32")
    df.to_feather(folder / "proofread_connections_783.feather")
    np.save(folder / "proofread_root_ids_783.npy", np.array(ids, dtype=np.int64))
    return df, ids


def reference_graph(df, ids, threshold=5):
    pairs = df.groupby(["pre_pt_root_id", "post_pt_root_id"])["syn_count"].sum()
    strong = pairs[pairs >= threshold]
    pos = {v: i for i, v in enumerate(ids)}
    G = nx.Graph()
    G.add_nodes_from(range(len(ids)))
    for (a, b) in strong.index:
        if a in pos and b in pos and a != b:
            G.add_edge(pos[a], pos[b])
    return pairs, strong, G


def mean_clustering(G):
    nodes = [v for v in G if G.degree(v) >= 2]
    return float(np.mean([nx.clustering(G, v) for v in nodes]))


def mean_path(G):
    tot = cnt = 0
    for s in G:
        if G.degree(s) == 0:
            continue
        for t, d in nx.single_source_shortest_path_length(G, s).items():
            if t != s:
                tot += d
                cnt += 1
    return tot / cnt


@pytest.fixture(params=[0, 1, 2])
def fixture_dir(tmp_path, request):
    df, ids = make_fixture(tmp_path, seed=request.param)
    return tmp_path, df, ids


def test_real_metrics_against_networkx(fixture_dir, monkeypatch):
    folder, df, ids = fixture_dir
    monkeypatch.setattr(real, "DATA", str(folder))
    monkeypatch.setattr(real, "check_files", lambda: {"fixture": "md5 not checked"})
    out = folder / "real.json"
    monkeypatch.setattr(sys, "argv", ["x", "--clust-sample", "100000", "--path-sources", "100000", "--output", str(out)])
    real.main()
    r = json.load(open(out, encoding="utf-8"))
    pairs, strong, G = reference_graph(df, ids)
    c = r["counts"]
    assert c["proofread_neurons"] == len(ids)
    assert c["edge_rows_by_neuropil"] == len(df)
    assert c["unique_directed_pairs"] == len(pairs)
    assert c["total_synapses"] == int(df["syn_count"].sum())
    assert c["directed_pairs_ge_5_synapses"] == len(strong)
    assert c["undirected_edges_ge_5_synapses"] == G.number_of_edges()
    t = r["topology_thresholded_undirected"]
    assert t["avg_local_clustering"] == pytest.approx(mean_clustering(G), rel=1e-12)
    assert t["characteristic_path_length"] == pytest.approx(mean_path(G), rel=1e-12)
    assert t["max_degree"] == max(d for _, d in G.degree())
    assert t["mean_degree"] == pytest.approx(2 * G.number_of_edges() / len(ids))
    assert r["weights"]["max_synapses_per_pair"] == int(pairs.max())
    assert r["weights"]["median_synapses_per_pair"] == float(np.median(pairs.to_numpy()))


def test_topology_extra_against_networkx(fixture_dir, monkeypatch):
    folder, df, ids = fixture_dir
    monkeypatch.setattr(topo, "DATA", str(folder))
    out = folder / "topo.json"
    monkeypatch.setattr(sys, "argv", ["x", "--clust-sample", "100000", "--path-sources", "100000", "--output", str(out)])
    topo.main()
    r = json.load(open(out, encoding="utf-8"))
    _, _, G = reference_graph(df, ids)
    G.remove_nodes_from([v for v in list(G) if G.degree(v) == 0])
    assert r["graph"]["nodes_with_edges"] == G.number_of_nodes()
    assert r["graph"]["undirected_edges"] == G.number_of_edges()
    assert r["small_world"]["C"] == pytest.approx(mean_clustering(G), rel=1e-12)
    assert r["small_world"]["L"] == pytest.approx(mean_path(G), rel=1e-12)
    core = nx.core_number(G)
    kmax = max(core.values())
    assert r["k_core"]["k_max"] == kmax
    assert r["k_core"]["innermost_core_size"] == sum(1 for v in core.values() if v == kmax)
    for kind in ("random", "targeted_by_degree"):
        fr = list(r["robustness_giant_component_fraction"][kind].values())
        assert all(0 < x <= 1 for x in fr)


def test_k_core_and_giant_component_on_random_graphs():
    for seed in range(20):
        G = nx.gnp_random_graph(80, 0.08, seed=seed)
        U = nx.to_scipy_sparse_array(G, format="csr", dtype=np.int8)
        from scipy import sparse
        U = sparse.csr_matrix(U)
        core = nx.core_number(G)
        kmax = max(core.values())
        if kmax == 0:
            continue
        assert topo.k_core(U) == (kmax, sum(1 for v in core.values() if v == kmax)), seed
        mask = np.zeros(80, dtype=bool)
        mask[::3] = True
        H = G.copy()
        H.remove_nodes_from(np.flatnonzero(mask).tolist())
        biggest = max((len(c) for c in nx.connected_components(H)), default=0)
        assert topo.giant_fraction(U, mask) == pytest.approx(biggest / 80), seed


def test_erdos_renyi_graph_has_exactly_m_edges():
    rng = np.random.RandomState(0)
    for n, m in ((50, 10), (200, 1500), (1000, 20000)):
        R = topo.er_graph(n, m, rng)
        assert R.nnz == 2 * m                         # симметрична, без повторов
        assert R.diagonal().sum() == 0                # без петель
        assert (R != R.T).nnz == 0


def test_transmitter_shares_against_plain_loops(fixture_dir, monkeypatch):
    folder, df, _ = fixture_dir
    (folder / "results").mkdir()
    monkeypatch.setattr(trans, "DATA", str(folder))
    monkeypatch.setattr(trans, "HERE", str(folder))   # результат — в tmp_path/results, не в results/ репозитория
    trans.main()
    r = json.load(open(folder / "results" / "connectome_transmitters.json", encoding="utf-8"))
    cols = list(trans.COLS)
    exp = dict.fromkeys(cols, 0.0)
    top = dict.fromkeys(cols, 0.0)
    w_ok = 0.0
    excluded = 0
    for _, row in df.iterrows():
        p = [row[c] for c in cols]
        if any(x != x for x in p):
            excluded += 1
            continue
        w = float(row["syn_count"])
        w_ok += w
        for c, x in zip(cols, p):
            exp[c] += w * x
        top[cols[int(np.argmax(p))]] += w
    s = sum(exp.values())
    assert r["rows_excluded_no_prediction"] == excluded
    assert r["synapses_total"] == int(df["syn_count"].sum())
    assert r["synapses_with_prediction"] == int(w_ok)
    for c in cols:
        name = trans.COLS[c]
        assert r["expected_share_by_synapses"][name] == pytest.approx(round(exp[c] / s, 4), abs=1e-12)
        assert r["argmax_share_by_synapses"][name] == pytest.approx(round(top[c] / w_ok, 4), abs=1e-12)
