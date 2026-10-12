# ==============================================================================
# AIfa-BioBench: Merkle tree with inclusion proofs (RFC 6962 / RFC 9162)
# Copyright (c) 2026 Maksim Galatin & CODE (Code of Digital Eternity) — https://aifa.works
# Licensed under the PolyForm Noncommercial License 1.0.0 — commercial use only under a written licence:
# contact@codeofdigitaleternity.com
#
# 12.10.2026. Заверенный proof_of_connectome.py строит дерево по-старому: нечётный последний узел
# дублируется (класс CVE-2012-2459 — списки [a,b,c] и [a,b,c,c] дают один корень), лист и внутренний
# узел хешируются одинаково (дерево из 4 листьев и дерево из 2 «листьев»-узлов дают один корень), а
# «проверка одного листа» пересчитывает весь подграф нейропиля. Здесь — то же назначение по стандарту
# Certificate Transparency: префикс 0x00 у листа и 0x01 у узла, разбиение по наибольшей степени двойки,
# доказательство включения из log2(n) хешей и его проверка по алгоритму RFC 9162 §2.1.3.2.
# Заверенный скрипт и его результат не меняются: они остаются записью того, что было.
# ==============================================================================
"""RFC 6962 Merkle tree, inclusion proofs and their verification; benchmark on synthetic records and,
when the FlyWire v783 files are present in bench/data/, on every row of the real connectome.

    python bench/merkle_rfc6962.py                    # 139,255 synthetic neuron records (as proof_of_connectome.py)
    python bench/merkle_rfc6962.py --flywire          # every row of proofread_connections_783.feather
"""
import argparse
import hashlib
import json
import os
import platform
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
EMPTY_ROOT = hashlib.sha256(b"").digest()


def leaf_hash(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


class MerkleTree:
    """Bottom-up build; an unpaired last node is promoted unchanged (never duplicated).

    This gives exactly the RFC 6962 Merkle Tree Hash (split at the largest power of two below n);
    tests/test_merkle_rfc6962.py checks it against the recursive definition for every n up to 130.
    """

    def __init__(self, leaf_hashes):
        level = list(leaf_hashes)
        self.n = len(level)
        self.levels = [level]
        while len(level) > 1:
            nxt = [node_hash(level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
            if len(level) % 2:
                nxt.append(level[-1])
            self.levels.append(nxt)
            level = nxt

    @classmethod
    def from_data(cls, items):
        return cls(leaf_hash(x) for x in items)

    @property
    def root(self) -> bytes:
        return self.levels[-1][0] if self.n else EMPTY_ROOT

    def proof(self, index: int) -> list:
        """Audit path for leaf `index` (RFC 6962 §2.1.1 PATH), bottom-up."""
        if not 0 <= index < self.n:
            raise IndexError(index)
        path = []
        for level in self.levels[:-1]:
            sib = index ^ 1
            if sib < len(level):
                path.append(level[sib])
            index >>= 1
        return path


def verify_inclusion(index: int, tree_size: int, leaf_h: bytes, proof: list, root: bytes) -> bool:
    """RFC 9162 §2.1.3.2 — verify that leaf_h is leaf number `index` of the tree with this root and size."""
    if index >= tree_size or index < 0:
        return False
    fn, sn, r = index, tree_size - 1, leaf_h
    for p in proof:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = node_hash(p, r)
            if not fn & 1:
                while not fn & 1 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            r = node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == root


# ------------------------------------------------------------------------------
# Определения из RFC — рекурсивно, как в тексте стандарта; только для тестов и сверки
# ------------------------------------------------------------------------------
def _split(n):
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def mth_reference(hashes):
    """RFC 6962 §2.1: MTH({}) = SHA-256(), MTH({d0}) = leaf hash, MTH(D[n]) = node(MTH(D[0:k]), MTH(D[k:n]))."""
    n = len(hashes)
    if n == 0:
        return EMPTY_ROOT
    if n == 1:
        return hashes[0]
    k = _split(n)
    return node_hash(mth_reference(hashes[:k]), mth_reference(hashes[k:]))


def path_reference(m, hashes):
    """RFC 6962 §2.1.1 PATH(m, D[n])."""
    n = len(hashes)
    if n <= 1:
        return []
    k = _split(n)
    if m < k:
        return path_reference(m, hashes[:k]) + [mth_reference(hashes[k:])]
    return path_reference(m - k, hashes[k:]) + [mth_reference(hashes[:k])]


def legacy_root(hex_hashes):
    """The stamped proof_of_connectome.py scheme, copied verbatim, to show its two known weaknesses."""
    if not hex_hashes:
        return hashlib.sha256(b"").hexdigest()
    level = list(hex_hashes)
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(hashlib.sha256((left + right).encode("utf-8")).hexdigest())
        level = nxt
    return level[0]


# ------------------------------------------------------------------------------
# Данные для листьев
# ------------------------------------------------------------------------------
def synthetic_records(n, seed=42):
    """Same record generator and RNG sequence as proof_of_connectome.py (ID|supervoxel|type|hemisphere|transmitter)."""
    rng = np.random.RandomState(seed)
    transmitters = ["ACh", "GABA", "Glutamate", "Dopamine", "Octopamine", "Serotonin"]
    types = [f"type_{i}" for i in range(50)]
    out = []
    for i in range(n):
        supervoxel = rng.randint(0, 2**31 - 1)
        t = types[rng.randint(0, len(types))]
        hemi = ["L", "R"][rng.randint(0, 2)]
        tr = transmitters[rng.randint(0, len(transmitters))]
        out.append(f"{i}|{supervoxel}|{t}|{hemi}|{tr}".encode("utf-8"))
    return out


FLYWIRE_SERIALIZATION = ("one leaf per row of proofread_connections_783.feather, rows sorted by "
                         "(pre_pt_root_id, post_pt_root_id, neuropil); leaf data = UTF-8 of "
                         "'pre_pt_root_id|post_pt_root_id|neuropil|syn_count' (integers in decimal)")


def flywire_records():
    import pandas as pd  # только для режима --flywire
    sys.path.insert(0, HERE)
    from connectome_real_metrics import md5  # тот же подсчёт md5, что у заверенного скрипта
    p = os.path.join(DATA, "proofread_connections_783.feather")
    rec = json.load(open(os.path.join(DATA, "zenodo_10676866.json"), encoding="utf-8"))
    want = {f["key"]: f["checksum"].split(":")[1] for f in rec["files"]}["proofread_connections_783.feather"]
    if not os.path.exists(p):
        raise SystemExit(f"missing {p} — see bench/data/README.md")
    got = md5(p)
    if got != want:
        raise SystemExit(f"md5 mismatch: {got} != {want}")
    df = pd.read_feather(p, columns=["pre_pt_root_id", "post_pt_root_id", "neuropil", "syn_count"])
    df = df.sort_values(["pre_pt_root_id", "post_pt_root_id", "neuropil"], kind="mergesort").reset_index(drop=True)
    recs = [f"{a}|{b}|{c}|{d}".encode("utf-8") for a, b, c, d in
            zip(df["pre_pt_root_id"].tolist(), df["post_pt_root_id"].tolist(),
                df["neuropil"].astype(str).tolist(), df["syn_count"].tolist())]
    strongest = int(df["syn_count"].to_numpy().argmax())
    return recs, got, strongest


# ------------------------------------------------------------------------------
# Замер
# ------------------------------------------------------------------------------
def benchmark(records, seed=42, n_proofs=10000, n_tamper=1000):
    rng = np.random.RandomState(seed)
    t0 = time.perf_counter()
    leaves = [leaf_hash(r) for r in records]
    tree = MerkleTree(leaves)
    build = time.perf_counter() - t0
    n = tree.n
    idx = rng.randint(0, n, size=min(n_proofs, n))
    lat, sizes, ok = [], [], 0
    for i in idx:
        i = int(i)
        p = tree.proof(i)
        t0 = time.perf_counter_ns()
        good = verify_inclusion(i, n, leaves[i], p, tree.root)
        lat.append((time.perf_counter_ns() - t0) / 1000.0)
        sizes.append(len(p))
        ok += good
    # подделка: изменённая запись, чужой номер, чужой корень — каждая должна быть отвергнута
    rejected = {"modified_record": 0, "wrong_index": 0, "wrong_root": 0}
    other_root = hashlib.sha256(tree.root).digest()
    for i in rng.randint(0, n, size=min(n_tamper, n)):
        i = int(i)
        p = tree.proof(i)
        rejected["modified_record"] += not verify_inclusion(i, n, leaf_hash(records[i] + b"x"), p, tree.root)
        j = (i + 1 + int(rng.randint(0, n - 1))) % n if n > 1 else i
        rejected["wrong_index"] += (j != i) and not verify_inclusion(j, n, leaves[i], p, tree.root)
        rejected["wrong_root"] += not verify_inclusion(i, n, leaves[i], p, other_root)
    lat = np.array(lat)
    trials = min(n_tamper, n)
    return tree, leaves, {
        "leaves": n,
        "root_sha256": tree.root.hex(),
        "tree_height": len(tree.levels) - 1,
        "build_time_sec": round(build, 3),
        "proof_hashes_max": int(max(sizes)),
        "proof_bytes_max": int(max(sizes)) * 32,
        "proofs_checked": int(len(idx)),
        "proofs_verified": int(ok),
        "verify_p50_us": round(float(np.percentile(lat, 50)), 2),
        "verify_p95_us": round(float(np.percentile(lat, 95)), 2),
        "tamper_trials_each": trials,
        "tamper_rejected": {k: int(v) for k, v in rejected.items()},
        "wrong_index_trials": trials if n > 1 else 0,
    }


def legacy_weaknesses(records):
    """Show on the same data that the stamped scheme has both collisions and RFC 6962 has neither."""
    hx = [hashlib.sha256(r).hexdigest() for r in records[:3]]
    dup_legacy = legacy_root(hx) == legacy_root(hx + [hx[-1]])
    lv = [leaf_hash(r) for r in records[:3]]
    dup_rfc = MerkleTree(lv).root == MerkleTree(lv + [lv[-1]]).root
    four = [hashlib.sha256(r).hexdigest() for r in records[:4]]
    inner = [hashlib.sha256((four[0] + four[1]).encode()).hexdigest(),
             hashlib.sha256((four[2] + four[3]).encode()).hexdigest()]
    conf_legacy = legacy_root(four) == legacy_root(inner)
    l4 = [leaf_hash(r) for r in records[:4]]
    conf_rfc = MerkleTree(l4).root == MerkleTree.from_data([node_hash(l4[0], l4[1]), node_hash(l4[2], l4[3])]).root
    return {
        "duplicate_last_leaf_same_root": {"stamped_scheme": dup_legacy, "rfc6962": dup_rfc},
        "inner_nodes_as_leaves_same_root": {"stamped_scheme": conf_legacy, "rfc6962": conf_rfc},
    }


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="RFC 6962 Merkle tree benchmark")
    ap.add_argument("--n", type=int, default=139255, help="synthetic records (ignored with --flywire)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--proofs", type=int, default=10000)
    ap.add_argument("--flywire", action="store_true", help="use every row of the real FlyWire v783 connectome")
    ap.add_argument("--output", default=None)
    a = ap.parse_args(argv)
    t_start = time.time()
    if a.flywire:
        records, src_md5, strongest = flywire_records()
        source = {"kind": "FlyWire v783 proofread_connections_783.feather", "zenodo": "10.5281/zenodo.10676866",
                  "license": "CC BY 4.0", "md5": src_md5, "serialization": FLYWIRE_SERIALIZATION}
    else:
        records, strongest = synthetic_records(a.n, a.seed), None
        source = {"kind": "synthetic neuron records, same generator as proof_of_connectome.py", "n": a.n,
                  "seed": a.seed, "note": "synthetic — not FlyWire data"}
    tree, leaves, m = benchmark(records, a.seed, a.proofs)
    res = {"benchmark": "AIfa-BioBench Merkle tree, RFC 6962 / RFC 9162 inclusion proofs", "source": source,
           "metrics": m, "known_weaknesses_check": legacy_weaknesses(records)}
    if strongest is not None:
        # пример, который любой проверит вручную: строка с наибольшим числом синапсов и её доказательство
        res["example_inclusion_proof"] = {"leaf_index": strongest, "record": records[strongest].decode(),
                                          "leaf_hash": leaves[strongest].hex(),
                                          "audit_path": [h.hex() for h in tree.proof(strongest)]}
    res["provenance"] = {"python": platform.python_version(), "numpy": np.__version__,
                         "platform": platform.platform(), "processor": platform.processor() or platform.machine(),
                         "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "runtime_s": round(time.time() - t_start, 1)}
    name = "merkle_rfc6962_flywire_v783.json" if a.flywire else "merkle_rfc6962_synthetic.json"
    out = a.output or os.path.join(HERE, "results", name)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:   # LF на любой ОС — хеш файла одинаков везде
        json.dump(res, fh, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "example_inclusion_proof"}, indent=1))
    print(f"saved: {out}")
    return res


if __name__ == "__main__":
    main()
