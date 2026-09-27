# AIfa-BioBench — open results

Open, timestamped results of the benchmarks for the bio-inspired algorithms behind AIfa ACR (sparse
"fly hash" projection, APL novelty gate, CANN ring attractor, CX steering, bilateral verifier) — and an
honest record of what they do and do not achieve, including where standard methods win.

- **Licence:** Apache 2.0 (this repository). Connectome data: FlyWire v783, CC BY 4.0.
- **Pages that cite these numbers:** <https://aifa.works/acr> · <https://www.codeofdigitaleternity.com/acr>
- **Every number below comes from a file in `results/`.** If a number on a page is not here, treat it as
  unverified and tell us: contact@codeofdigitaleternity.com.

## Free and paid parts

| This repository (free, Apache 2.0) | AIfa-BioBench Pro (paid, private) |
|---|---|
| all result files of the real measurements (`results/`) | everything in the free part |
| OpenTimestamps proofs and the stamped manifest | the engine code (`aifa_sdk/`) |
| methodology (`bench/PROTOCOL.md`) | every benchmark script that uses or implements the engine |
| scripts that run on public data only: connectome statistics on FlyWire v783, the Merkle-tree proof, the Aho–Corasick string filter | the browser search file measured in section 7 |
| | full history since 20 September 2026 |

The engine and the scripts that exercise it are kept closed: the methods are the subject of patent
applications in preparation, and publishing their code would disclose them. The **numbers** they produced
are all here, with the files and the timestamps that fix them. Access to the paid repository —
`github.com/MaksimGalatin/aifa-biobench-pro` — is granted under a written licence agreement:
contact@codeofdigitaleternity.com.

## Results (measured 21.09 and 23.09.2026, Intel Core i7-14700, Python 3.14, NumPy 2.5)

### 1. Vector retrieval — 50,000 vectors × 1024, top-10, independent queries

| Method | Recall@10 | P50 latency | Source |
|---|---:|---:|---|
| AIfa FlyHash (30% k-WTA, pool 250) | 39.55% | 43.9 ms (23.09) · 59.0 ms (21.09) | `results/rerun_2026-09-23_independent/result.json`, `results/run_2026-09-21_independent/result.json` |
| FAISS IndexFlatL2 (exact) | 100% | 8.8 ms (23.09) · 16.9 ms (21.09) | same files, `baseline_duel` |

Recall reproduced exactly on re-run (0.3955); latency varied from 44 to 59 ms with machine load. **On this
test exact FAISS is both faster and more accurate.** The `smoke` protocol (query = noisy copy of an indexed
vector) gives 46.70% — it measures near-duplicate detection, not open search.

The files at the top of `results/` (`result.json`, `metrics.json`, `result.csv`, `benchmark_manifest.json`)
are an earlier, smaller run of 20.09 (5,000 × 256, 50 queries, pool 100: Recall@10 36.2%, P50 8.3 ms) —
not the configuration in the table.

### 2. Binary retrieval duel — 25,000 × 512, 100 queries, seed 42

| Method | Recall@10 | NDCG@10 | P50 | Non-zero projection weights |
|---|---:|---:|---:|---:|
| AIfa FlyHash | 18.9% | 0.319 | 35.5 ms | 12,288 |
| Sign-LSH (1-bit BQ) | 80.5% | 0.872 | 36.8 ms | 1,048,576 |
| Multi-table LSH | 0.1% | 0.002 | 0.05 ms | — |

FlyHash is 85× sparser but much less accurate. Source: `results/binary_arena_results.json`,
`results/binary_arena_comparison.csv`.

### 3. "Claw" count sweep — is the fly's d = 6 optimal?

Recall@10: d=2 13.8% · d=6 19.8% · d=7 23.3% · d=8 22.5% · d=10 22.3% · d=16 24.9%.
On this task d = 6 is not the optimum. Source: `results/dendritic_sweep.json`.

### 4. Agent benchmark — real engines

9 agents × 360 episodes on synthetic websites with menu hints, 35% distractor links.

| Agent | Task success | Wrong clicks |
|---|---:|---:|
| Standard, goal pinned | 5.8% ± 3.8 | 97.9% |
| ACR as shipped (APL + CANN + CX) | 1.4% ± 3.1 | 99.2% |
| ACR with CX loop-avoidance fixed | 94.7% ± 5.5 | 54.5% |
| Full ACR + bilateral verifier | 93.6% ± 4.1 | 54.1% |
| Standard + visited-link memory | 95.0% ± 5.5 | 53.8% |

Finding: the gain comes from remembering visited links; APL, CANN and the verifier add no measurable
benefit here. Files: `results/acr_agent_real_benchmark_distr_{0.0,0.35,0.7}.json`.

### 5. Robustness — real dropout (5 seeds, 512-bit codes, shortlist 50)

| Dropped | FlyHash R@10 | Sign-LSH R@10 | CANN idle error |
|---:|---:|---:|---:|
| 0% | 58.9% | 86.1% | 0.13° |
| 10% | 52.3% | 84.5% | 7.0° |
| 30% | 39.6% | 82.2% | 15.2° |
| 50% | 25.4% | 78.2% | 14.6° |

FlyHash loses accuracy faster than Sign-LSH. After a distractor pulse (strength 0.25) the CANN ring drifts
~73–94° towards the distractor. File: `results/robustness_real.json`.

### 6. Real connectome statistics — reproducible from this repository

FlyWire v783 from Zenodo [10.5281/zenodo.10676866](https://doi.org/10.5281/zenodo.10676866); download the
two files into `bench/data/` as described in [`bench/data/README.md`](bench/data/README.md) (852 MB, not
committed; md5 sums are checked before anything is computed).

139,255 neurons · 54,492,922 synapses · 15,091,983 connected pairs · 2,700,513 pairs with ≥5 synapses ·
clustering C = 0.160 · path length L = 4.03 · KS distance to lognormal 0.282.
Files: `results/connectome_real_metrics.json`, `results/connectome_topology_extra.json` (small-world index
against a measured Erdős–Rényi graph, k-core, percolation, robustness), `results/connectome_transmitters.json`
(neurotransmitter shares). The ACR algorithms use random connections, not FlyWire weights; the connectome is
used for graph statistics only.

### 7. Module micro-benchmarks (21.09.2026)

| Module | Measured | Note |
|---|---|---|
| Energy model (06) | 369.1× fewer operations than dense FP16 | operation-count model, **not** a wattmeter |
| BioMatch (07) | 38.9% on a synthetic graph | not yet computed on the real connectome |
| Browser search (08) | P50 2,756 μs | plain JavaScript, 7,121 bytes; no WASM, no SIMD |
| Graph compiler (09) | cyclic core dependencies in 1,000 / 1,000 runs | sequential block partitioning; no Metis |
| Symbiosis index (10) | Φ mean 0.155, P50 0.097; 49.7 μs/turn | the code uses a different 4-factor formula than the published one |

Sections 1–5 were re-run from a clean clone of the full repository on 25.09.2026 with identical recall and
success rates; latencies depend on machine load.

## Run what is in this repository

```bash
git clone https://github.com/MaksimGalatin/aifa-biobench.git
cd aifa-biobench
pip install -r requirements.txt                    # numpy, scipy; pandas + pyarrow for FlyWire
python bench/proof_of_connectome.py --n-neurons 5000
python bench/olfactory_filter_run.py
# after downloading FlyWire v783 into bench/data/ (see bench/data/README.md):
python bench/connectome_real_metrics.py
python bench/connectome_topology_extra.py
python bench/connectome_transmitters.py
```

`proof_of_connectome.py` builds the Merkle tree from **synthetic** neuron records (it says so in its output)
and measures build and verification time. `olfactory_filter_run.py` measures an Aho–Corasick string filter;
the 150 ms language-model latency it compares against is the figure from the website card, not a
measurement — the script labels it that way.

## Timestamps — how to check that the numbers were not changed later

The result files are timestamped with OpenTimestamps in Bitcoin blocks 968268–968274 (`results/*.ots`).
Verify with `ots verify results/MANIFEST_2026-09-23.sha256.ots` (needs a Bitcoin node) or by dropping the
`.ots` file and the file it stamps onto <https://opentimestamps.org>.

Then check the files against the stamped manifest **before** running anything:

```bash
sha256sum -c --ignore-missing results/MANIFEST_2026-09-23.sha256
```

In this repository **56 of the manifest's files are present, and all 56 match** (checked on 27.09.2026).
The other 53 lines are files that live in the paid repository — the engine (13), the benchmark scripts (33)
and the browser search file (1) — plus two withdrawn legacy results, the original README and three
note lines about the FlyWire source files. The scripts write fresh runs to `bench/results/` (ignored by git)
or over their file in `results/`; `git restore results/` brings back the stamped version.

## Not measured / withdrawn

- No script measures a fused "58 μs" control loop or "~122 ms on a live DOM".
- L1/L2/LLC cache hit rates, wattmeter energy, GPU comparisons: not measured.
- Two legacy benchmarks set their outcomes by fixed probabilities or a formula (22.47% → 94.58%, "3.21×
  more robust"). Their result files are **not** published here; they remain in the paid repository only as a
  record, marked legacy.
- A self-retrieval check (search for an exact copy of an indexed text, Recall@10 = 1.0 by construction) is
  not a measure of search quality and is not reported as one.
- The earlier "connectome root" Bitcoin timestamp (block 967238) holds no attestation and is being re-issued.

## Layout

```
bench/PROTOCOL.md           methodology and reference hardware
bench/data/README.md        how to download FlyWire v783 (not committed)
bench/*.py                  scripts that run on public data only
results/                    machine-readable outputs, manifest and .ots proofs
```

## Author

Maksim Galatin — CODE Eternal / AIfa Works. Contact: contact@codeofdigitaleternity.com

Licensed under the Apache License 2.0 — see [LICENSE](LICENSE).
