# Дерево Меркла по RFC 6962 / RFC 9162 (bench/merkle_rfc6962.py): эталонные векторы Certificate Transparency,
# совпадение с рекурсивным определением стандарта, доказательства включения и отказ на подделке.
import hashlib
import json
import os
import random

import pytest

from conftest import RESULTS
import merkle_rfc6962 as m

# Входы и корни для размеров 1..8 — тестовые векторы Certificate Transparency (merkle_tree_test, Trillian / RFC 6962)
CT_LEAVES = ["", "00", "10", "2021", "3031", "40414243", "5051525354555657", "606162636465666768696a6b6c6d6e6f"]
CT_ROOTS = [
    "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d",
    "fac54203e7cc696cf0dfcb42c92a1d9dbaf70ad9e621f4bd8d98662f00e3c125",
    "aeb6bcfe274b70a14fb067a5e5578264db0fa9b51af5e0ba159158f329e06e77",
    "d37ee418976dd95753c1c73862b9398fa2a2cf9b4ff0fdfe8b30cd95209614b7",
    "4e3bbb1f7b478dcfe71fb631631519a3bca12c9aefca1612bfce4c13a86264d4",
    "76e67dadbcdf1e10e1b74ddc608abd2f98dfb16fbce75277b5232a127f2087ef",
    "ddb89be403809e325750d3d263cd78929c2942b7942a34b77e122c9594a74c8c",
    "5dc9da79a70659a9ad559cb701ded9a2ab9d823aad2f4960cfe370eff4604328",
]


def rand_leaves(n, seed):
    rng = random.Random(seed)
    return [m.leaf_hash(bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 40)))) for _ in range(n)]


def test_empty_tree_root():
    assert m.MerkleTree([]).root == hashlib.sha256(b"").digest()


def test_certificate_transparency_vectors_sizes_1_to_8():
    for size in range(1, 9):
        tree = m.MerkleTree.from_data([bytes.fromhex(x) for x in CT_LEAVES[:size]])
        assert tree.root.hex() == CT_ROOTS[size - 1], size


def test_root_equals_recursive_definition_for_every_size_up_to_130():
    for n in range(0, 131):
        leaves = rand_leaves(n, n)
        assert m.MerkleTree(leaves).root == m.mth_reference(leaves), n


def test_every_proof_equals_rfc_path_and_verifies_up_to_70():
    for n in range(1, 71):
        leaves = rand_leaves(n, 1000 + n)
        tree = m.MerkleTree(leaves)
        for i in range(n):
            p = tree.proof(i)
            assert p == m.path_reference(i, leaves), (n, i)
            assert m.verify_inclusion(i, n, leaves[i], p, tree.root), (n, i)


def test_forgeries_are_rejected_for_every_leaf_up_to_40():
    for n in range(1, 41):
        leaves = rand_leaves(n, 2000 + n)
        tree = m.MerkleTree(leaves)
        root = tree.root
        for i in range(n):
            p = tree.proof(i)
            assert not m.verify_inclusion(i, n, m.leaf_hash(b"forged"), p, root)               # чужая запись
            assert not m.verify_inclusion(i, n, leaves[i], p, hashlib.sha256(root).digest())  # чужой корень
            for j in range(n):                                                                 # чужой номер
                if j != i:
                    assert not m.verify_inclusion(j, n, leaves[i], p, root), (n, i, j)
            # Размер дерева здесь не проверяется намеренно: по RFC 9162 пара (корень, размер) заверяется вместе
            # (подписанная голова журнала), и путь листа 0 дерева из 3 листьев проходит и как путь в дереве из 4
            # при том же корне — найдено этим тестом 12.10.2026, это свойство стандарта, а не ошибка кода.
            if p:
                assert not m.verify_inclusion(i, n, leaves[i], p[:-1], root)                  # укороченный путь
                bad = list(p)
                bad[0] = hashlib.sha256(bad[0]).digest()
                assert not m.verify_inclusion(i, n, leaves[i], bad, root)                     # подменённый узел
            assert not m.verify_inclusion(i, n, leaves[i], p + [root], root)                  # удлинённый путь
        assert not m.verify_inclusion(n, n, leaves[0], tree.proof(0), root)                    # номер за пределом


def test_proof_length_is_logarithmic():
    for n in (1, 2, 3, 1000, 139255):
        tree = m.MerkleTree([m.leaf_hash(str(i).encode()) for i in range(n)])
        longest = max(len(tree.proof(i)) for i in {0, n // 2, n - 1})
        assert longest <= max(0, (n - 1).bit_length()), n


def test_stamped_scheme_has_both_known_weaknesses_and_rfc6962_has_neither():
    w = m.legacy_weaknesses(m.synthetic_records(10))
    assert w["duplicate_last_leaf_same_root"] == {"stamped_scheme": True, "rfc6962": False}
    assert w["inner_nodes_as_leaves_same_root"] == {"stamped_scheme": True, "rfc6962": False}


def test_legacy_root_is_the_stamped_function():
    from proof_of_connectome import merkle_root_of_list
    for n in range(0, 40):
        hx = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(n)]
        assert m.legacy_root(hx) == merkle_root_of_list(hx), n


def test_synthetic_records_follow_the_stamped_generator():
    # тот же генератор, что в proof_of_connectome.py: хеши записей совпадают с его листьями
    from proof_of_connectome import build_neuron_leaves
    recs = m.synthetic_records(500, 42)
    by_neuropil = build_neuron_leaves(500, 42, 78)
    flat = {i: by_neuropil[i % 78][i // 78] for i in range(500)}
    assert all(hashlib.sha256(r).hexdigest() == flat[i] for i, r in enumerate(recs))


def test_committed_synthetic_result_is_reproduced():
    path = os.path.join(RESULTS, "merkle_rfc6962_synthetic.json")
    if not os.path.exists(path):
        pytest.skip("results/merkle_rfc6962_synthetic.json not committed yet")
    stamped = json.load(open(path, encoding="utf-8"))
    n, seed = stamped["source"]["n"], stamped["source"]["seed"]
    tree = m.MerkleTree.from_data(m.synthetic_records(n, seed))
    assert tree.root.hex() == stamped["metrics"]["root_sha256"]
    assert stamped["metrics"]["proofs_verified"] == stamped["metrics"]["proofs_checked"]
    assert all(v == stamped["metrics"]["tamper_trials_each"] for v in stamped["metrics"]["tamper_rejected"].values())


def test_committed_flywire_example_proof_verifies_without_the_dataset():
    # пример из результата проверяется без скачивания 852 МБ: запись -> лист -> путь -> корень
    path = os.path.join(RESULTS, "merkle_rfc6962_flywire_v783.json")
    if not os.path.exists(path):
        pytest.skip("results/merkle_rfc6962_flywire_v783.json not committed yet")
    r = json.load(open(path, encoding="utf-8"))
    ex = r["example_inclusion_proof"]
    leaf = m.leaf_hash(ex["record"].encode("utf-8"))
    assert leaf.hex() == ex["leaf_hash"]
    root = bytes.fromhex(r["metrics"]["root_sha256"])
    proof = [bytes.fromhex(h) for h in ex["audit_path"]]
    assert m.verify_inclusion(ex["leaf_index"], r["metrics"]["leaves"], leaf, proof, root)
    assert not m.verify_inclusion(ex["leaf_index"], r["metrics"]["leaves"], m.leaf_hash(b"x"), proof, root)
