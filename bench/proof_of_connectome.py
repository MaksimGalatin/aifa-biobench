# ==============================================================================
# AIfa-BioBench: Proof of Connectome (Карточка #4)
# Copyright (c) 2026 CODE Eternal Ecosystem & Maksim Galatin
# Chief Architect, Lead Engineer & Creator: Maxim Valentinovich Galatin
# Licensed under the Apache License, Version 2.0
#
# Реализация Merkle Tree, заявленного на карточке #4 страницы /digital и /acr:
#
#   L_i = SHA256(ID_i || SupervoxelID || Type || Hemisphere || Transmitter)
#   H(E_ij) = SHA256(PreID || PostID || SynCount || NT_Score)
#   Root_FlyWire_v783 = SHA256(Subtrees_1..78)  (агрегация по 78 нейропилям)
#
# 21.09.2026: до этого скрипта карточка #4 не имела ни одной строки кода.
# Этот скрипт строит Merkle Tree честно из СИНТЕТИЧЕСКИХ записей нейронов
# (не реальные данные FlyWire v783, которые не входят в этот open-source
# репозиторий) и замеряет РЕАЛЬНОЕ время построения дерева и верификации
# одного листа. Заявление о фиксации в блокчейне Bitcoin (OpenTimestamps
# Block 967238) — это внешний сетевой факт, который НЕ проверяется этим
# скриптом: он требует запроса к реальной ноде Bitcoin и не входит в
# зону ответственности локального криптографического бенчмарка.
# ==============================================================================

import os
import json
import time
import hashlib
import platform
import argparse
import numpy as np


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_neuron_leaves(n_neurons: int, seed: int, n_neuropils: int = 78):
    """
    Строит листья Merkle Tree для n_neurons синтетических нейронов,
    распределённых по n_neuropils нейропилям, по формуле карточки:
    L_i = SHA256(ID_i || SupervoxelID || Type || Hemisphere || Transmitter)
    """
    rng = np.random.RandomState(seed)
    transmitters = ["ACh", "GABA", "Glutamate", "Dopamine", "Octopamine", "Serotonin"]
    hemispheres = ["L", "R"]
    types = [f"type_{i}" for i in range(50)]  # 50 типов проекционных нейронов, как в карточке #19

    leaves_by_neuropil = [[] for _ in range(n_neuropils)]
    for i in range(n_neurons):
        neuropil_idx = i % n_neuropils
        supervoxel_id = rng.randint(0, 2**31 - 1)
        neuron_type = types[rng.randint(0, len(types))]
        hemisphere = hemispheres[rng.randint(0, 2)]
        transmitter = transmitters[rng.randint(0, len(transmitters))]
        leaf_data = f"{i}|{supervoxel_id}|{neuron_type}|{hemisphere}|{transmitter}".encode("utf-8")
        leaves_by_neuropil[neuropil_idx].append(sha256_hex(leaf_data))
    return leaves_by_neuropil


def merkle_root_of_list(hashes: list) -> str:
    """Стандартное попарное агрегирование листьев в один корневой хеш."""
    if not hashes:
        return sha256_hex(b"")
    level = list(hashes)
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            combined = (left + right).encode("utf-8")
            next_level.append(sha256_hex(combined))
        level = next_level
    return level[0]


def build_full_tree(n_neurons: int, seed: int, n_neuropils: int = 78):
    """
    Строит полное дерево: листья -> корень каждого нейропиля (subtree) ->
    финальный корень Root_FlyWire = SHA256(Subtrees_1..78), как заявлено
    на карточке.
    """
    t0 = time.perf_counter()
    leaves_by_neuropil = build_neuron_leaves(n_neurons, seed, n_neuropils)
    subtree_roots = [merkle_root_of_list(leaves) for leaves in leaves_by_neuropil]
    final_root = sha256_hex("".join(subtree_roots).encode("utf-8"))
    build_time = time.perf_counter() - t0

    return {
        "final_root": final_root,
        "subtree_roots": subtree_roots,
        "leaves_by_neuropil": leaves_by_neuropil,
        "build_time_sec": build_time,
    }


def verify_tampering_detection(tree_data: dict, n_neuropils: int, seed: int, n_neurons: int, n_trials: int = 20):
    """
    Проверяет заявление карточки: "Любая модификация хотя бы одного синапса
    приводит к полному изменению корневого хеша (Zero-Tampering Proof)".
    Меняет один случайный лист и убеждается, что final_root меняется.
    """
    rng = np.random.RandomState(seed + 999)
    original_root = tree_data["final_root"]
    detections = 0

    for trial in range(n_trials):
        tampered_leaves = [list(nl) for nl in tree_data["leaves_by_neuropil"]]
        neuropil_idx = rng.randint(0, n_neuropils)
        if not tampered_leaves[neuropil_idx]:
            continue
        leaf_idx = rng.randint(0, len(tampered_leaves[neuropil_idx]))
        # Подделываем один лист — меняем его хеш на случайный
        tampered_leaves[neuropil_idx][leaf_idx] = sha256_hex(os.urandom(16))

        subtree_roots = [merkle_root_of_list(leaves) for leaves in tampered_leaves]
        tampered_root = sha256_hex("".join(subtree_roots).encode("utf-8"))

        if tampered_root != original_root:
            detections += 1

    return detections, n_trials


def run_benchmark(n_neurons=139255, n_neuropils=78, seed=42, n_verify_trials=20):
    tree_result = build_full_tree(n_neurons, seed, n_neuropils)

    # Верификация одного случайного листа: находим его нейропиль и пересчитываем subtree
    t0 = time.perf_counter()
    rng = np.random.RandomState(seed + 1)
    check_neuropil = rng.randint(0, n_neuropils)
    recomputed_subtree = merkle_root_of_list(tree_result["leaves_by_neuropil"][check_neuropil])
    matches = recomputed_subtree == tree_result["subtree_roots"][check_neuropil]
    verify_one_leaf_time = time.perf_counter() - t0

    detections, n_trials = verify_tampering_detection(tree_result, n_neuropils, seed, n_neurons, n_verify_trials)

    result = {
        "configuration": {
            "n_neurons": n_neurons,
            "n_neuropils": n_neuropils,
            "seed": seed,
            "note": "синтетические ID/тип/полушарие/медиатор — не реальные данные FlyWire v783",
            "platform": platform.processor() or platform.machine(),
        },
        "metrics": {
            "build_time_sec": round(tree_result["build_time_sec"], 4),
            "final_root_sha256": tree_result["final_root"],
            "single_subtree_verify_time_sec": round(verify_one_leaf_time, 6),
            "single_subtree_verify_correct": bool(matches),
            "tampering_detection_rate": round(detections / n_trials, 4) if n_trials else None,
            "tampering_trials": n_trials,
        },
        "external_claim_not_verified_by_this_script": (
            "Заявление о фиксации корня в блокчейне Bitcoin (OpenTimestamps) "
            "требует внешнего сетевого запроса к ноде Bitcoin и не проверяется "
            "локальным криптографическим бенчмарком."
        ),
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="AIfa Proof of Connectome (Merkle Tree) benchmark")
    parser.add_argument("--n-neurons", type=int, default=139255)
    parser.add_argument("--n-neuropils", type=int, default=78)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-verify-trials", type=int, default=20)
    args = parser.parse_args()

    result = run_benchmark(n_neurons=args.n_neurons, n_neuropils=args.n_neuropils,
                            seed=args.seed, n_verify_trials=args.n_verify_trials)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "proof_of_connectome_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nСохранено: {out_path}")


if __name__ == "__main__":
    main()
