# Проверка самих тестов мутациями: в код вносится одна намеренная ошибка (номер в переменной MUTANT),
# и хотя бы один тест обязан упасть. Запуск — через run_mutants.py, не напрямую.
import os
import sys

BENCH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "bench")


def pytest_configure(config):
    sys.path.insert(0, BENCH)
    n = int(os.environ.get("MUTANT", "0"))
    import numpy as np
    if n == 1:
        import open_arena as oa
        orig = oa.hamming_to_all
        def bad(codes, q):
            d = orig(codes, q).copy(); d[0] += 1; return d
        oa.hamming_to_all = bad
    elif n == 2:
        import open_arena as oa
        def bad(retrieved, gt, k):
            rec, ndcg = [], []
            idcg = sum(1.0 / np.log2(r + 2) for r in range(k + 1))
            for r, g in zip(retrieved, gt):
                r = list(r)[:k]; g = set(int(x) for x in g[:k])
                rec.append(len(set(int(x) for x in r) & g) / k)
                ndcg.append(sum(1.0 / np.log2(i + 2) for i, x in enumerate(r) if int(x) in g) / idcg)
            return float(np.mean(rec)), float(np.mean(ndcg))
        oa.recall_ndcg = bad
    elif n == 3:
        import hashlib, merkle_rfc6962 as m
        m.node_hash = lambda l, r: hashlib.sha256(b"\x00" + l + r).digest()
    elif n == 4:
        import merkle_rfc6962 as m
        def init(self, leaf_hashes):
            level = list(leaf_hashes); self.n = len(level); self.levels = [level]
            while len(level) > 1:
                if len(level) % 2: level = level + [level[-1]]
                level = [m.node_hash(level[i], level[i + 1]) for i in range(0, len(level), 2)]
                self.levels.append(level)
        m.MerkleTree.__init__ = init
    elif n == 5:
        import merkle_rfc6962 as m
        def bad(index, tree_size, leaf_h, proof, root):
            if index >= tree_size: return False
            fn, sn, r = index, tree_size - 1, leaf_h
            for p in proof:
                if sn == 0: return False
                if fn & 1:
                    r = m.node_hash(p, r)
                else:
                    r = m.node_hash(r, p)
                fn >>= 1; sn >>= 1
            return sn == 0 and r == root
        m.verify_inclusion = bad
    elif n == 6:
        import connectome_topology_extra as t
        def bad(U, sample):
            out = []
            for v in sample:
                nb = U.indices[U.indptr[v]:U.indptr[v + 1]]; k = len(nb)
                if k < 2: continue
                out.append(U[nb][:, nb].nnz / (k * k))
            return float(np.mean(out))
        t.clustering = bad
    elif n == 7:
        import connectome_topology_extra as t
        orig = t.k_core
        t.k_core = lambda U: (lambda a: (a[0] + 1, a[1]))(orig(U))
    elif n == 8:
        import olfactory_filter_run as o
        def bad(self):
            for v in range(len(self.fail)):
                self.fail[v] = 0
        o.AhoCorasick._build_fail_links = bad
    elif n == 9:
        import check_claims as c
        from decimal import ROUND_HALF_EVEN, Decimal
        def bad(v, dp=1, scale=1, thousands=False):
            d = (Decimal(str(v)) * Decimal(scale)).quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_EVEN)
            return f"{d:,}" if thousands else str(d)
        c.fmt = bad
    elif n == 10:
        import connectome_topology_extra as t
        orig = t.path_length
        t.path_length = lambda U, sources: orig(U, sources[:-1])
