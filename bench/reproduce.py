# ==============================================================================
# AIfa-BioBench: reproduce the stamped results with one command
# Copyright (c) 2026 Maksim Galatin & CODE (Code of Digital Eternity) — https://aifa.works
# Licensed under the PolyForm Noncommercial License 1.0.0 — commercial use only under a written licence:
# contact@codeofdigitaleternity.com
#
# 12.10.2026. Одна команда перезапускает всё, что можно перезапустить из открытой части, и сравнивает
# детерминированные поля свежего прогона с заверенными файлами results/: хеши — побайтно, целые — точно,
# дроби — с относительным допуском 1e-9. Время (мс, мкс) зависит от машины и только печатается рядом.
# Свежие файлы пишутся в bench/results/ (папка в .gitignore); заверенные results/ не трогаются.
# ==============================================================================
"""Re-run every open script and compare it with the stamped files in results/.

    python bench/reproduce.py                    # everything; FlyWire parts only if bench/data/ has the files
    python bench/reproduce.py --skip-connectome  # ~15 s: Merkle, Aho-Corasick, open arena
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FRESH = os.path.join(HERE, "results")
sys.path.insert(0, HERE)

rows = []


def stamped(name):
    with open(os.path.join(ROOT, "results", name), encoding="utf-8") as fh:
        return json.load(fh)


def record(check, want, got, kind="exact"):
    if kind == "info":
        ok = None
    elif isinstance(want, float) or isinstance(got, float):
        ok = want == got or (isinstance(want, (int, float)) and isinstance(got, (int, float))
                             and math.isclose(want, got, rel_tol=1e-9, abs_tol=1e-12))
    else:
        ok = want == got
    rows.append({"check": check, "stamped": want, "fresh": got, "verdict": "INFO" if ok is None else "PASS" if ok else "FAIL"})


def flatten(d, prefix=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flatten(v, f"{prefix}{k}.")
        else:
            yield f"{prefix}{k}", v


def compare_json(label, want, got, skip=("provenance", "params.output")):
    fw, fg = dict(flatten(want)), dict(flatten(got))
    for k, v in fw.items():
        if k.startswith(skip):
            continue
        record(f"{label}: {k}", v, fg.get(k, "<missing>"))


def run_script(args, timeout=3600):
    t0 = time.time()
    p = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    if p.returncode != 0:
        raise SystemExit(f"{' '.join(args)} failed with code {p.returncode}:\n{p.stderr[-2000:]}")
    return time.time() - t0


def flywire_present():
    return all(os.path.exists(os.path.join(HERE, "data", f))
               for f in ("proofread_connections_783.feather", "proofread_root_ids_783.npy"))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-connectome", action="store_true", help="skip the FlyWire v783 scripts (852 MB data)")
    a = ap.parse_args(argv)
    os.makedirs(FRESH, exist_ok=True)
    t_start = time.time()

    # 1. Дерево Меркла заверенного скрипта: корень на 139 255 синтетических нейронах
    from proof_of_connectome import run_benchmark as poc
    s = stamped("proof_of_connectome_result.json")
    c = s["configuration"]
    f = poc(n_neurons=c["n_neurons"], n_neuropils=c["n_neuropils"], seed=c["seed"])
    record("proof_of_connectome: final_root_sha256", s["metrics"]["final_root_sha256"], f["metrics"]["final_root_sha256"])
    record("proof_of_connectome: tampering_detection_rate", s["metrics"]["tampering_detection_rate"],
           f["metrics"]["tampering_detection_rate"])
    record("proof_of_connectome: build_time_sec", s["metrics"]["build_time_sec"], f["metrics"]["build_time_sec"], "info")

    # 2. Автомат Ахо — Корасик: доля помеченных строк
    from olfactory_filter_run import run_benchmark as aho
    s = stamped("olfactory_filter_result.json")
    f = aho(n_samples=s["configuration"]["n_samples"], seed=s["configuration"]["seed"])
    record("olfactory_filter: danger_flagged_pct", s["honest_measurement"]["danger_flagged_pct"],
           f["honest_measurement"]["danger_flagged_pct"])
    record("olfactory_filter: latency_p50_us", s["honest_measurement"]["latency_p50_us"],
           f["honest_measurement"]["latency_p50_us"], "info")

    # 3. Открытая арена против заверенной строки Sign-LSH и многотабличного LSH (README §2)
    import open_arena as oa
    arena = {r["method"]: r for r in stamped("binary_arena_results.json")}
    res = oa.run(oa.parser().parse_args(["--methods", "signlsh,multitable"]))
    for mine, theirs in zip(res["results"], ("Sign-LSH / BQ 1-Bit", "MultiHash Table LSH")):
        record(f"arena {theirs}: recall_at_10_pct", arena[theirs]["recall_at_10_pct"], round(mine["recall_at_10_pct"], 2))
        record(f"arena {theirs}: ndcg_at_10", arena[theirs]["ndcg_at_10"], round(mine["ndcg_at_10"], 4))
        record(f"arena {theirs}: p50_latency_ms", arena[theirs]["p50_latency_ms"], mine["p50_latency_ms"], "info")

    # 4. Дерево Меркла по RFC 6962 на синтетике
    import merkle_rfc6962 as mk
    p = os.path.join(ROOT, "results", "merkle_rfc6962_synthetic.json")
    if os.path.exists(p):
        s = stamped("merkle_rfc6962_synthetic.json")
        tree = mk.MerkleTree.from_data(mk.synthetic_records(s["source"]["n"], s["source"]["seed"]))
        record("merkle_rfc6962 synthetic: root_sha256", s["metrics"]["root_sha256"], tree.root.hex())

    # 5. Реальный коннектом FlyWire v783 — если файлы скачаны
    if a.skip_connectome:
        rows.append({"check": "FlyWire v783 scripts", "verdict": "SKIPPED", "stamped": None, "fresh": "--skip-connectome"})
    elif not flywire_present():
        rows.append({"check": "FlyWire v783 scripts", "verdict": "SKIPPED", "stamped": None,
                     "fresh": "bench/data/ has no FlyWire files — see bench/data/README.md"})
    else:
        out = os.path.join(FRESH, "connectome_real_metrics.json")
        t = run_script(["bench/connectome_real_metrics.py", "--output", out])
        compare_json("connectome_real_metrics", stamped("connectome_real_metrics.json"), json.load(open(out, encoding="utf-8")))
        record("connectome_real_metrics: runtime_s", None, round(t, 1), "info")
        out = os.path.join(FRESH, "connectome_topology_extra.json")
        t = run_script(["bench/connectome_topology_extra.py", "--output", out])
        compare_json("connectome_topology_extra", stamped("connectome_topology_extra.json"), json.load(open(out, encoding="utf-8")))
        record("connectome_topology_extra: runtime_s", None, round(t, 1), "info")
        t = run_script(["bench/connectome_transmitters.py"])        # пишет в bench/results/, она уже создана
        compare_json("connectome_transmitters", stamped("connectome_transmitters.json"),
                     json.load(open(os.path.join(FRESH, "connectome_transmitters.json"), encoding="utf-8")))
        if os.path.exists(os.path.join(ROOT, "results", "merkle_rfc6962_flywire_v783.json")):
            out = os.path.join(FRESH, "merkle_rfc6962_flywire_v783.json")
            t = run_script(["bench/merkle_rfc6962.py", "--flywire", "--output", out])
            s, f = stamped("merkle_rfc6962_flywire_v783.json"), json.load(open(out, encoding="utf-8"))
            for k in ("leaves", "root_sha256", "tree_height", "proof_hashes_max", "proofs_verified"):
                record(f"merkle_rfc6962 FlyWire: {k}", s["metrics"][k], f["metrics"][k])
            record("merkle_rfc6962 FlyWire: example_inclusion_proof", s["example_inclusion_proof"], f["example_inclusion_proof"])

    fails = [r for r in rows if r["verdict"] == "FAIL"]
    passes = [r for r in rows if r["verdict"] == "PASS"]
    for r in rows:
        print(f"{r['verdict']:<7} {r['check']:<62} stamped={r['stamped']!r:<30.30} fresh={r['fresh']!r:.40}")
    print(f"\n{len(passes)} PASS, {len(fails)} FAIL, "
          f"{sum(r['verdict'] == 'INFO' for r in rows)} INFO (timings, machine-dependent), "
          f"{sum(r['verdict'] == 'SKIPPED' for r in rows)} SKIPPED — {time.time() - t_start:.0f} s")
    with open(os.path.join(FRESH, "reproduce_report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"rows": rows, "pass": len(passes), "fail": len(fails), "provenance": res["provenance"]}, fh, indent=1)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
