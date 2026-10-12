# ==============================================================================
# AIfa-BioBench: README claims checker
# Copyright (c) 2026 Maksim Galatin & CODE (Code of Digital Eternity) — https://aifa.works
# Licensed under the PolyForm Noncommercial License 1.0.0 — commercial use only under a written licence:
# contact@codeofdigitaleternity.com
#
# 12.10.2026. README обещает: «каждое число ниже взято из файла в results/». Здесь это обещание
# проверяется машиной: у каждого числа README записан файл и поле, откуда оно взято, и правило
# округления. Округление — половина вверх от записанного в файле значения (Decimal), как округляет
# человек; первая же проверка нашла в README NDCG 0.872 там, где точное значение 0.871492.
# ==============================================================================
"""Check that every number quoted in README.md equals the value in the result file it comes from.

    python bench/check_claims.py            # prints every claim, exits 1 if any differs
"""
import json
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def get(rel, *path):
    v = load(rel)
    for p in path:
        v = v[p]
    return v


def fmt(v, dp=1, scale=1, thousands=False):
    d = (Decimal(str(v)) * Decimal(scale)).quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)
    return f"{d:,}" if thousands else str(d)


def arena(method, key):
    rows = load("results/binary_arena_results.json")
    return next(r[key] for r in rows if r["method"] == method)


def sweep(d):
    return next(r["recall_at_10_pct"] for r in load("results/dendritic_sweep.json") if r["dendritic_degree_d"] == d)


def agent(name, key):
    return get("results/acr_agent_real_benchmark_distr_0.35.json", "agents", name, key)


def robust(dropout, key):
    return next(r[key] for r in get("results/robustness_real.json", "rows") if r["dropout"] == dropout)


R1 = "results/rerun_2026-09-23_independent/result.json"
R0 = "results/run_2026-09-21_independent/result.json"
SM = "results/rerun_2026-09-23_smoke/result.json"
OLD = "results/result.json"
CM = "results/connectome_real_metrics.json"


# Каждое утверждение: (раздел, точный фрагмент README, [(откуда, как вычислить строку)]).
# Строка, полученная из файла, обязана стоять внутри фрагмента, а фрагмент — внутри README.
def claims():
    yield ("§1", "| AIfa FlyHash (30% k-WTA, pool 250) | 39.55% | 43.9 ms (23.09) · 59.0 ms (21.09) |", [
        (R1, lambda: fmt(get(R1, "metrics", "recall_10"), 2, 100) + "%"),
        (R1, lambda: fmt(get(R1, "metrics", "latency_p50_ms"), 1) + " ms (23.09)"),
        (R0, lambda: fmt(get(R0, "metrics", "latency_p50_ms"), 1) + " ms (21.09)"),
        (R1, lambda: "pool " + str(get(R1, "configuration", "pool")))])
    yield ("§1", "| FAISS IndexFlatL2 (exact) | 100% | 8.8 ms (23.09) · 16.9 ms (21.09) |", [
        (R1, lambda: fmt(get(R1, "baseline_duel", "recall10"), 0, 100) + "%"),
        (R1, lambda: fmt(get(R1, "baseline_duel", "p50_ms"), 1) + " ms (23.09)"),
        (R0, lambda: fmt(get(R0, "baseline_duel", "p50_ms"), 1) + " ms (21.09)")])
    yield ("§1", "### 1. Vector retrieval — 50,000 vectors × 1024, top-10, independent queries", [
        (R1, lambda: f"{get(R1, 'configuration', 'n_vectors'):,} vectors × {get(R1, 'configuration', 'dim')}"),
        (R1, lambda: f"top-{get(R1, 'configuration', 'top_k')}, {get(R1, 'configuration', 'protocol')} queries")])
    yield ("§1", "Recall reproduced exactly on re-run (0.3955)", [
        (R1, lambda: str(get(R1, "metrics", "recall_10"))), (R0, lambda: str(get(R0, "metrics", "recall_10")))])
    yield ("§1", "vector) gives 46.70%", [(SM, lambda: fmt(get(SM, "metrics", "recall_10"), 2, 100) + "%")])
    yield ("§1", "(5,000 × 256, 50 queries, pool 100: Recall@10 36.2%, P50 8.3 ms)", [
        (OLD, lambda: f"{get(OLD, 'configuration', 'n_vectors'):,} × {get(OLD, 'configuration', 'dim')}"),
        (OLD, lambda: f"{get(OLD, 'configuration', 'n_queries')} queries, pool {get(OLD, 'configuration', 'pool')}"),
        (OLD, lambda: "Recall@10 " + fmt(get(OLD, "metrics", "recall_10"), 1, 100) + "%"),
        (OLD, lambda: "P50 " + fmt(get(OLD, "metrics", "latency_p50_ms"), 1) + " ms")])

    A = "results/binary_arena_results.json"
    yield ("§2", "| AIfa FlyHash | 18.9% | 0.319 | 35.5 ms | 12,288 |", [
        (A, lambda: fmt(arena("AIfa FlyHash (Binary-Flat)", "recall_at_10_pct"), 1) + "%"),
        (A, lambda: fmt(arena("AIfa FlyHash (Binary-Flat)", "ndcg_at_10"), 3)),
        (A, lambda: fmt(arena("AIfa FlyHash (Binary-Flat)", "p50_latency_ms"), 1) + " ms"),
        ("derived: 2048 Kenyon cells × 6 claws", lambda: f"{2048 * 6:,}")])
    yield ("§2", "| Sign-LSH (1-bit BQ) | 80.5% | 0.871 | 36.8 ms | 1,048,576 |", [
        (A, lambda: fmt(arena("Sign-LSH / BQ 1-Bit", "recall_at_10_pct"), 1) + "%"),
        # в заверенном файле NDCG округлён до 0.8715; точное значение даёт открытая арена (0.871492)
        ("results/open_arena_2026-10-12.json", lambda: fmt(open_arena_row("gaussian", "Sign-LSH", "ndcg_at_10"), 3)),
        (A, lambda: fmt(arena("Sign-LSH / BQ 1-Bit", "p50_latency_ms"), 1) + " ms"),
        ("derived: 2048 hyperplanes × 512 dims", lambda: f"{2048 * 512:,}")])
    yield ("§2", "| Multi-table LSH | 0.1% | 0.002 | 0.05 ms | — |", [
        (A, lambda: fmt(arena("MultiHash Table LSH", "recall_at_10_pct"), 1) + "%"),
        (A, lambda: fmt(arena("MultiHash Table LSH", "ndcg_at_10"), 3)),
        (A, lambda: fmt(arena("MultiHash Table LSH", "p50_latency_ms"), 2) + " ms")])
    yield ("§2", "FlyHash is 85× sparser", [("derived: 1,048,576 / 12,288", lambda: f"{(2048 * 512) // (2048 * 6)}×")])

    yield ("§3", "Recall@10: d=2 13.8% · d=6 19.8% · d=7 23.3% · d=8 22.5% · d=10 22.3% · d=16 24.9%.", [
        ("results/dendritic_sweep.json", (lambda d: lambda: f"d={d} " + fmt(sweep(d), 1) + "%")(d))
        for d in (2, 6, 7, 8, 10, 16)])

    G = "results/acr_agent_real_benchmark_distr_0.35.json"
    yield ("§4", "9 agents × 360 episodes on synthetic websites with menu hints, 35% distractor links.", [
        (G, lambda: f"{len(get(G, 'agents'))} agents × {get(G, 'episodes_per_agent')} episodes"),
        (G, lambda: fmt(get(G, "environment", "distractor_rate"), 0, 100) + "% distractor")])
    for label, name in (("| Standard, goal pinned |", "pinned_greedy"),
                        ("| ACR as shipped (APL + CANN + CX) |", "acr_apl_cann_cx_as_shipped"),
                        ("| ACR with CX loop-avoidance fixed |", "acr_apl_cann_cx_fixed"),
                        ("| Full ACR + bilateral verifier |", "acr_full_fixed"),
                        ("| Standard + visited-link memory |", "pinned_greedy_plus_repulsion")):
        row = (f"{label} {fmt(agent(name, 'success_rate_mean'), 1, 100)}% ± {fmt(agent(name, 'success_rate_std'), 1, 100)}"
               f" | {fmt(agent(name, 'wrong_click_rate'), 1, 100)}% |")
        yield ("§4", row, [(G, (lambda r: lambda: r)(row))])

    RB = "results/robustness_real.json"
    yield ("§5", "### 5. Robustness — real dropout (5 seeds, 512-bit codes, shortlist 50)", [
        (RB, lambda: f"{get(RB, 'params', 'seeds')} seeds, {get(RB, 'params', 'bits')}-bit codes, "
                     f"shortlist {get(RB, 'params', 'pool')}")])
    for dr, cann_dp in ((0.0, 2), (0.1, 1), (0.3, 1), (0.5, 1)):
        row = (f"| {fmt(dr, 0, 100)}% | {fmt(robust(dr, 'flyhash_recall10'), 1, 100)}% | "
               f"{fmt(robust(dr, 'signlsh_recall10'), 1, 100)}% | {fmt(robust(dr, 'cann_idle_error_deg'), cann_dp)}° |")
        yield ("§5", row, [(RB, (lambda r: lambda: r)(row))])
    yield ("§5", "drifts\n~73–94° towards the distractor", [
        (RB, lambda: "~" + fmt(min(r["cann_after_distractor_error_deg"] for r in get(RB, "rows")), 0) + "–"
                     + fmt(max(r["cann_after_distractor_error_deg"] for r in get(RB, "rows")), 0) + "°")])

    yield ("§6", "139,255 neurons · 54,492,922 synapses · 15,091,983 connected pairs · 2,700,513 pairs with ≥5 synapses ·", [
        (CM, lambda: f"{get(CM, 'counts', 'proofread_neurons'):,} neurons"),
        (CM, lambda: f"{get(CM, 'counts', 'total_synapses'):,} synapses"),
        (CM, lambda: f"{get(CM, 'counts', 'unique_directed_pairs'):,} connected pairs"),
        (CM, lambda: f"{get(CM, 'counts', 'directed_pairs_ge_5_synapses'):,} pairs with ≥{get(CM, 'params', 'threshold')}")])
    yield ("§6", "clustering C = 0.160 · path length L = 4.03 · KS distance to lognormal 0.282.", [
        (CM, lambda: "C = " + fmt(get(CM, "topology_thresholded_undirected", "avg_local_clustering"), 3)),
        (CM, lambda: "L = " + fmt(get(CM, "topology_thresholded_undirected", "characteristic_path_length"), 2)),
        (CM, lambda: "lognormal " + fmt(get(CM, "weights", "ks_distance_vs_lognormal"), 3))])

    yield ("§7", "| Energy model (06) | 369.1× fewer operations", [
        ("results/neuromorphic_energy_result.json",
         lambda: fmt(get("results/neuromorphic_energy_result.json", "metrics", "energy_efficiency_multiplier"), 1) + "×")])
    yield ("§7", "| BioMatch (07) | 38.9% on a synthetic graph", [
        ("results/biomatch_score_result.json",
         lambda: fmt(get("results/biomatch_score_result.json", "report", "composite_biomatch_score_pct"), 1) + "%")])
    W = "results/wasm_search_result.json"
    yield ("§7", "| Browser search (08) | P50 2,756 μs | plain JavaScript, 7,121 bytes", [
        (W, lambda: "P50 " + fmt(get(W, "honest_measurement", "latency_p50_us"), 0, thousands=True) + " μs"),
        (W, lambda: f"{get(W, 'file_reality_check', 'actual_size_bytes'):,} bytes")])
    NC = "results/neuromorphic_compiler_result.json"
    yield ("§7", "| Graph compiler (09) | cyclic core dependencies in 1,000 / 1,000 runs", [
        (NC, lambda: f"{get(NC, 'honest_deadlock_check', 'runs_with_cyclic_core_dependency'):,} / "
                     f"{get(NC, 'honest_deadlock_check', 'runs_total'):,} runs")])
    S = "results/symbiosis_index_result.json"
    yield ("§7", "| Symbiosis index (10) | Φ mean 0.155, P50 0.097; 49.7 μs/turn", [
        (S, lambda: "mean " + fmt(get(S, "honest_session_result", "mean_phi"), 3)),
        (S, lambda: "P50 " + fmt(get(S, "honest_session_result", "p50_phi"), 3)),
        (S, lambda: fmt(get(S, "honest_session_result", "turn_eval_latency_us"), 1) + " μs/turn")])

    yield from new_claims()


# ------------------------------------------------------------------------------
# Числа разделов, добавленных 12.10.2026 (открытая арена, дерево Меркла по RFC 6962)
# ------------------------------------------------------------------------------
OA = "results/open_arena_2026-10-12.json"
MS = "results/merkle_rfc6962_synthetic.json"
MF = "results/merkle_rfc6962_flywire_v783.json"


def open_arena_row(dataset, prefix, key):
    for run in load(OA)["runs"]:
        if run["dataset"]["kind"] == dataset and run["dataset"]["n"] == 25000:
            return next(r[key] for r in run["results"] if r["method"].startswith(prefix))
    raise KeyError(dataset)


def open_arena_big(prefix, key):
    run = next(r for r in load(OA)["runs"] if r["dataset"]["n"] == 100000)
    return next(r[key] for r in run["results"] if r["method"].startswith(prefix))


def new_claims():
    if not os.path.exists(os.path.join(ROOT, OA)):
        return
    for ds, label in (("gaussian", "isotropic"), ("clustered", "clustered")):
        for prefix in ("Exact", "Sign-LSH", "Multi-table"):
            r = lambda k, ds=ds, p=prefix: open_arena_row(ds, p, k)
            row = (f"| {label} | {prefix} | {fmt(r('recall_at_10_pct'), 1)}% | {fmt(r('ndcg_at_10'), 3)} | "
                   f"{fmt(r('p50_latency_ms'), 2)} ms |")
            yield ("§8", row, [(OA, (lambda x: lambda: x)(row))])
    for prefix in ("Exact", "Sign-LSH", "Multi-table"):
        row = (f"| clustered, 100,000 × 768 | {prefix} | {fmt(open_arena_big(prefix, 'recall_at_10_pct'), 1)}% | "
               f"{fmt(open_arena_big(prefix, 'ndcg_at_10'), 3)} | {fmt(open_arena_big(prefix, 'p50_latency_ms'), 2)} ms |")
        yield ("§8", row, [(OA, (lambda x: lambda: x)(row))])
    # воспроизведение заверенных строк §2: открытая арена и заверенный файл обязаны дать одно и то же
    A = "results/binary_arena_results.json"
    yield ("§8", "(Recall@10 80.50% and 0.10%, NDCG@10 0.8715 and 0.0022 at four digits)", [
        (OA, lambda: "Recall@10 " + fmt(open_arena_row("gaussian", "Sign-LSH", "recall_at_10_pct"), 2) + "% and "
                     + fmt(open_arena_row("gaussian", "Multi-table", "recall_at_10_pct"), 2) + "%"),
        (A, lambda: "Recall@10 " + fmt(arena("Sign-LSH / BQ 1-Bit", "recall_at_10_pct"), 2) + "% and "
                    + fmt(arena("MultiHash Table LSH", "recall_at_10_pct"), 2) + "%"),
        (OA, lambda: "NDCG@10 " + fmt(open_arena_row("gaussian", "Sign-LSH", "ndcg_at_10"), 4) + " and "
                     + fmt(open_arena_row("gaussian", "Multi-table", "ndcg_at_10"), 4)),
        (A, lambda: "NDCG@10 " + fmt(arena("Sign-LSH / BQ 1-Bit", "ndcg_at_10"), 4) + " and "
                    + fmt(arena("MultiHash Table LSH", "ndcg_at_10"), 4))])
    def cfg(dataset, key, n=25000):
        return next(r["dataset"][key] for r in load(OA)["runs"] if r["dataset"]["kind"] == dataset and r["dataset"]["n"] == n)
    yield ("§8", "Isotropic and clustered: 25,000 × 512, 100 independent queries, seed 42.", [
        (OA, (lambda ds: lambda: f"{cfg(ds, 'n'):,} × {cfg(ds, 'dim')}, {cfg(ds, 'queries')} independent queries, "
                                 f"seed {cfg(ds, 'seed')}")(ds)) for ds in ("gaussian", "clustered")])
    yield ("§8", "Clustered: a mixture of 100 Gaussian\nclusters on the unit sphere (noise norm 0.8 of a centre)", [
        (OA, lambda: f"a mixture of {cfg('clustered', 'clusters')} Gaussian"),
        (OA, lambda: f"(noise norm {cfg('clustered', 'spread')} of a centre)")])
    yield ("§8", "Sign-LSH: 2,048 bits, shortlist 250, exact rerank; multi-table LSH: 8 tables × 14 bits.", [
        (OA, lambda: "2,048 bits, shortlist 250" if any(r["method"] == "Sign-LSH (2048 bits, pool 250)"
                                                        for r in load(OA)["runs"][0]["results"]) else "CONFIG DIFFERS"),
        (OA, lambda: "8 tables × 14 bits" if any(r["method"] == "Multi-table LSH (8 x 14 bits)"
                                                 for r in load(OA)["runs"][0]["results"]) else "CONFIG DIFFERS")])
    pv = load(OA)["provenance"]
    yield ("§8", f"Measured {pv['utc'][:10]} on an Intel Core i7-14700, Python {pv['python']}, NumPy {pv['numpy']}", [
        (OA, lambda: f"Python {pv['python']}, NumPy {pv['numpy']}"), (OA, lambda: pv["utc"][:10])])
    sp = fmt(open_arena_row("gaussian", "Sign-LSH", "p50_latency_ms"), 2)
    ep = fmt(open_arena_row("gaussian", "Exact", "p50_latency_ms"), 2)
    yield ("§8", f"gives the same distances and the same recall at {sp} ms.", [(OA, lambda: sp)])
    yield ("§8", f"Exact float32 brute force through BLAS answers in {ep} ms", [(OA, lambda: ep)])
    yield ("§8", "so the Sign-LSH index takes " + fmt(open_arena_row("gaussian", "Sign-LSH", "index_mb"), 1) + " MB against "
                 + fmt(open_arena_row("gaussian", "Exact", "index_mb"), 1) + " MB for exact search", [
        (OA, lambda: fmt(open_arena_row("gaussian", "Sign-LSH", "index_mb"), 1) + " MB against "
                     + fmt(open_arena_row("gaussian", "Exact", "index_mb"), 1) + " MB")])
    yield ("§2", "again gave 0.872. The open arena (§8) recomputes the unrounded value, ", [
        (A, lambda: "0.872" if fmt(fmt(arena("Sign-LSH / BQ 1-Bit", "ndcg_at_10"), 4), 3) == "0.872" else "double rounding gone")])
    yield ("§2", f"recomputes the unrounded value, {open_arena_row('gaussian', 'Sign-LSH', 'ndcg_at_10'):.6f}, which rounds to 0.871.", [
        (OA, lambda: f"{open_arena_row('gaussian', 'Sign-LSH', 'ndcg_at_10'):.6f}, which rounds to "
                     + fmt(open_arena_row("gaussian", "Sign-LSH", "ndcg_at_10"), 3))])
    if os.path.exists(os.path.join(ROOT, MS)):
        m = get(MS, "metrics")
        yield ("§9", f"| synthetic records (as `proof_of_connectome.py`) | {m['leaves']:,} | `{m['root_sha256'][:16]}…` | "
                     f"{m['proof_hashes_max']} hashes ({m['proof_bytes_max']} bytes) | {fmt(m['verify_p50_us'], 1)} μs |",
               [(MS, lambda: "")])
    if os.path.exists(os.path.join(ROOT, MF)):
        m = get(MF, "metrics")
        yield ("§9", f"| FlyWire v783, every row of `proofread_connections_783.feather` | {m['leaves']:,} | "
                     f"`{m['root_sha256'][:16]}…` | {m['proof_hashes_max']} hashes ({m['proof_bytes_max']} bytes) | "
                     f"{fmt(m['verify_p50_us'], 1)} μs |", [(MF, lambda: "")])
        yield ("§9", f"Full root: `{m['root_sha256']}`", [(MF, lambda: "")])
        s = get(MS, "metrics") if os.path.exists(os.path.join(ROOT, MS)) else m
        yield ("§9", f"{m['proofs_verified']:,} of {m['proofs_checked']:,} random proofs verified, and all "
                     f"{m['tamper_trials_each']:,} forgeries of each kind", [
            (MF, lambda: "" if all(v == m["tamper_trials_each"] for v in m["tamper_rejected"].values()) else "FORGERY ACCEPTED"),
            (MS, lambda: f"{s['proofs_verified']:,} of {s['proofs_checked']:,} random proofs verified, and all "
                         f"{s['tamper_trials_each']:,}"),
            (MS, lambda: "" if all(v == s["tamper_trials_each"] for v in s["tamper_rejected"].values()) else "FORGERY ACCEPTED")])
        ex = get(MF, "example_inclusion_proof")["record"].split("|")
        yield ("§9", f"strongest connection in the brain ({ex[3]} synapses, neuropil {ex[2]})", [
            # второй источник: максимум синапсов на пару из заверенной статистики коннектома
            (CM, lambda: f"({get(CM, 'weights', 'max_synapses_per_pair')} synapses")])
        w = get(MF, "known_weaknesses_check")
        yield ("§9", "the result files record that the\nstamped scheme has both collisions on the same data and this one has neither.", [
            (MF, lambda: "" if w["duplicate_last_leaf_same_root"] == w["inner_nodes_as_leaves_same_root"]
             == {"stamped_scheme": True, "rfc6962": False} else "MISMATCH")])


def check(readme_text):
    rows = []
    for section, snippet, parts in claims():
        in_readme = snippet in readme_text
        for source, compute in parts:
            try:
                want = compute()
                ok = in_readme and want in snippet
                rows.append((section, ok, source, want, snippet))
            except Exception as e:  # отсутствующий файл или поле — тоже провал
                rows.append((section, False, source, f"ERROR {type(e).__name__}: {e}", snippet))
    return rows


def uncovered_numbers(readme_text, rows):
    """Numbers in README sections 1-9 that no claim covers — printed for information, not a failure."""
    body = readme_text.split("## Results", 1)[-1].split("## Run what is in this repository", 1)[0]
    covered = " ".join(s for *_, s in rows)
    found = set(re.findall(r"\d[\d,]*\.?\d*", body))
    return sorted(n for n in found if n not in covered)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    rows = check(text)
    bad = [r for r in rows if not r[1]]
    for section, ok, source, want, snippet in rows:
        print(f"{'OK  ' if ok else 'FAIL'} {section} {want!r:<40} <- {source}")
        if not ok:
            print(f"       README fragment: {snippet!r}" + ("" if snippet in text else "  (fragment NOT in README)"))
    print(f"\n{len(rows) - len(bad)} of {len(rows)} numbers match their result files"
          f" ({sum(1 for r in rows if not r[2].startswith('derived'))} from files, "
          f"{sum(1 for r in rows if r[2].startswith('derived'))} derived from configuration).")
    rest = uncovered_numbers(text, rows)
    if rest:
        print("Numbers in the results sections not covered by a claim (dates, hardware, versions, ranges): "
              + ", ".join(rest))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
