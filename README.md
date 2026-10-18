# AIfa-BioBench — open results

[![Open benchmark scripts](https://github.com/MaksimGalatin/aifa-biobench/actions/workflows/bench.yml/badge.svg)](https://github.com/MaksimGalatin/aifa-biobench/actions/workflows/bench.yml) [![DOI](https://zenodo.org/badge/1391059995.svg)](https://zenodo.org/badge/latestdoi/1391059995)

Open, timestamped results of the benchmarks for the bio-inspired algorithms behind AIfa ACR (sparse
"fly hash" projection, APL novelty gate, CANN ring attractor, CX steering, bilateral verifier) — and an
honest record of what they do and do not achieve, including where standard methods win.

- **Licence:** PolyForm Noncommercial 1.0.0 (this repository) — free for non-commercial use; commercial use only under a written licence (contact@codeofdigitaleternity.com). Connectome data: FlyWire v783, CC BY 4.0 (licence of its authors).
- **Pages that cite these numbers:** <https://aifa.works/acr> · <https://www.codeofdigitaleternity.com/acr>
- **Every number below comes from a file in `results/`.** If a number on a page is not here, treat it as
  unverified and tell us: contact@codeofdigitaleternity.com.
- **Checked by a machine, not by trust:** `python bench/check_claims.py` compares every number in the results
  sections with the field of the file it comes from; `python bench/reproduce.py` re-runs everything that can be
  re-run from this repository and compares it with the stamped files; CI does both and runs the test suite on
  Linux, Windows and macOS with Python 3.10–3.13 at every push.
- **Cite:** GitHub's "Cite this repository" button uses [`CITATION.cff`](CITATION.cff).

## Quick start — check us yourself

Don't trust the tables below — check them. Three commands on any machine with Python 3.10+:

```bash
git clone https://github.com/MaksimGalatin/aifa-biobench.git && cd aifa-biobench
pip install -r requirements.txt
python bench/check_claims.py      # every number in this README against the result file it comes from
python bench/open_arena.py        # re-run the open retrieval arena (§8) on your machine
```

Have a retrieval method of your own? Any class with `build(X)` and `search(q, k)` plugs into the same arena:

```bash
python bench/open_arena.py --methods exact,signlsh,my_package.my_module:MyIndex
```

Post your numbers as an issue ("Arena result" template) — results where our methods lose are as welcome as
results where they win. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Free and paid parts

| This repository (free for non-commercial use, PolyForm Noncommercial 1.0.0) | AIfa-BioBench Pro (paid, private) |
|---|---|
| all result files of the real measurements (`results/`) | everything in the free part |
| OpenTimestamps proofs and the stamped manifest | the engine code (`aifa_sdk/`) |
| methodology (`bench/PROTOCOL.md`) | every benchmark script that uses or implements the engine |
| scripts that run on public data only: connectome statistics on FlyWire v783, the Merkle-tree proof, the Aho–Corasick string filter | the browser search file measured in section 7 |
| open retrieval arena: exact ground truth, metrics, open baselines (exact, Sign-LSH, multi-table LSH) and a plug-in API for your own method (§8) | |
| RFC 6962 Merkle tree with inclusion proofs, including a root over every row of the real FlyWire v783 connectome (§9) | |
| tests, the README claims checker and one-command reproduction of the stamped results | |
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
| Sign-LSH (1-bit BQ) | 80.5% | 0.871 | 36.8 ms | 1,048,576 |
| Multi-table LSH | 0.1% | 0.002 | 0.05 ms | — |

FlyHash is 85× sparser but much less accurate. Source: `results/binary_arena_results.json`,
`results/binary_arena_comparison.csv`.
Until 12.10.2026 this table said 0.872 for Sign-LSH: the stamped file rounds the NDCG to 0.8715, and rounding that
again gave 0.872. The open arena (§8) recomputes the unrounded value, 0.871492, which rounds to 0.871.
Most of the latency in this table is the Hamming kernel of the stamped script, not the method — see §8.

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

### 8. Open retrieval arena — reproduce §2, test your own method (12.10.2026)

`bench/open_arena.py` is an independent, open implementation of the duel's ground truth, metrics and baselines:
exact float32 brute force, Sign-LSH (Charikar's SimHash, "1-bit binary quantisation") and multi-table LSH. FlyHash is
not in it — the engine is in the paid part. With the same data generator and seed it reproduces the stamped Sign-LSH
and multi-table rows of §2 exactly (Recall@10 80.50% and 0.10%, NDCG@10 0.8715 and 0.0022 at four digits).

| Data | Method | Recall@10 | NDCG@10 | P50 |
|---|---|---:|---:|---:|
| isotropic | Exact | 100.0% | 1.000 | 0.59 ms |
| isotropic | Sign-LSH | 80.5% | 0.871 | 5.52 ms |
| isotropic | Multi-table | 0.1% | 0.002 | 0.04 ms |
| clustered | Exact | 100.0% | 1.000 | 0.76 ms |
| clustered | Sign-LSH | 100.0% | 1.000 | 5.61 ms |
| clustered | Multi-table | 8.1% | 0.152 | 0.05 ms |
| clustered, 100,000 × 768 | Exact | 100.0% | 1.000 | 5.56 ms |
| clustered, 100,000 × 768 | Sign-LSH | 89.6% | 0.933 | 19.86 ms |
| clustered, 100,000 × 768 | Multi-table | 8.6% | 0.163 | 0.31 ms |

Isotropic and clustered: 25,000 × 512, 100 independent queries, seed 42. Clustered: a mixture of 100 Gaussian
clusters on the unit sphere (noise norm 0.8 of a centre), queries drawn fresh from the same mixture; with about 250
vectors per cluster a shortlist of 250 covers the query's whole cluster, which is why Sign-LSH reaches 100% there and
not at 100,000 vectors. Sign-LSH: 2,048 bits, shortlist 250, exact rerank; multi-table LSH: 8 tables × 14 bits.
Measured 2026-10-12 on an Intel Core i7-14700, Python 3.14.4, NumPy 2.5.2, one query at a time;
file `results/open_arena_2026-10-12.json`. Recall is deterministic on a given machine; latency changes with machine load. Across processors the Sign-LSH
row can move by a few tenths of a point: on some GitHub servers the same code gives Recall@10 80.7% / NDCG@10 0.8728
instead of the stamped 80.5% / 0.8715, on others exactly the stamped values. The codes are signs of float32
projections, so a different order of floating-point additions on another CPU can flip a projection close to zero.
Pinning the OpenBLAS kernel (`OPENBLAS_CORETYPE=Haswell`) did not remove the difference, so the exact source is
still being traced; until then treat the third digit of that row as machine-dependent.
`bench/reproduce.py` reports such a run as NEAR — within the same tolerance the test suite uses (one point of
recall, 0.01 NDCG) — instead of FAIL; an exact match is still reported as PASS.

What this shows that the stamped run did not:

- **Most of the 36.8 ms in §2 was the Hamming kernel.** The stamped script expands every bit into a byte with
  `np.unpackbits` (51 MB per query at 25,000 × 2,048 bits). Counting bits per 64-bit word with `np.bitwise_count`
  gives the same distances and the same recall at 5.52 ms.
- **At this scale exact search wins.** Exact float32 brute force through BLAS answers in 0.59 ms
  with 100% recall — faster than every binary method here. Nor do the codes save memory in this setup: the exact
  rerank keeps the float vectors, so the Sign-LSH index takes 58.9 MB against 48.9 MB for exact search.
  Where binary codes can pay off — codes alone without rerank, or far larger collections — is not measured here.
- **Isotropic data is the worst case for any ANN method.** True neighbours are barely closer than random points, so
  results on it do not transfer to real embeddings; the clustered rows and `--dataset npy` are there for that.

Plug in your own method — any class with `build(X)` and `search(q, k)`:

```bash
python bench/open_arena.py --methods exact,signlsh,my_package.my_module:MyIndex
python bench/open_arena.py --dataset npy --base base.npy --query query.npy --normalize
python bench/open_arena.py --suite        # the three configurations of the table above
```

### 9. Merkle proofs on the real connectome — RFC 6962 (12.10.2026)

The stamped `bench/proof_of_connectome.py` (kept unchanged as the record of what was measured) builds its tree with
two known weaknesses: an odd last node is duplicated, so `[a, b, c]` and `[a, b, c, c]` have the same root (the
CVE-2012-2459 class), and leaves and inner nodes are hashed the same way, so a four-leaf tree and the two-"leaf" tree
of its inner nodes have the same root. Its "verification of one leaf" recomputes a whole neuropil subtree.
`bench/merkle_rfc6962.py` does the same job the Certificate Transparency way: 0x00 / 0x01 domain separation, split at
the largest power of two, inclusion proofs of at most ⌈log₂ n⌉ hashes checked with the algorithm of RFC 9162
§2.1.3.2. It passes the Certificate Transparency test vectors for tree sizes 1–8, and the result files record that the
stamped scheme has both collisions on the same data and this one has neither.

| Leaves | Count | Root (SHA-256) | Longest proof | Verify P50 |
|---|---:|---|---|---:|
| synthetic records (as `proof_of_connectome.py`) | 139,255 | `57e8d00707c57d0b…` | 18 hashes (576 bytes) | 13.2 μs |
| FlyWire v783, every row of `proofread_connections_783.feather` | 16,847,997 | `d8a3400b4c26b06c…` | 25 hashes (800 bytes) | 34.4 μs |

Full root: `d8a3400b4c26b06c977306c45147657b1700bdb9baa2ee54406b92763c4b5077`

FlyWire leaves: one per row, rows sorted by (pre, post, neuropil), leaf data `pre|post|neuropil|syn_count`. Anyone with
the Zenodo file computes the same root (`python bench/merkle_rfc6962.py --flywire`). In both trees
10,000 of 10,000 random proofs verified, and all 1,000 forgeries of each kind — changed record,
wrong position, wrong root — were rejected. `results/merkle_rfc6962_flywire_v783.json` includes the proof for the
strongest connection in the brain (2405 synapses, neuropil LO_L); the tests verify it without the 852 MB download.

## Run what is in this repository

```bash
git clone https://github.com/MaksimGalatin/aifa-biobench.git
cd aifa-biobench
pip install -r requirements.txt                    # numpy, scipy; pandas + pyarrow for FlyWire
python bench/proof_of_connectome.py --n-neurons 5000
python bench/olfactory_filter_run.py
python bench/open_arena.py                        # §8: exact, Sign-LSH, multi-table LSH
python bench/merkle_rfc6962.py                    # §9: RFC 6962 tree on synthetic records
# after downloading FlyWire v783 into bench/data/ (see bench/data/README.md):
python bench/connectome_real_metrics.py
python bench/connectome_topology_extra.py
python bench/connectome_transmitters.py
python bench/merkle_rfc6962.py --flywire           # §9: root over every connectome row
```

`proof_of_connectome.py` builds the Merkle tree from **synthetic** neuron records (it says so in its output)
and measures build and verification time. `olfactory_filter_run.py` measures an Aho–Corasick string filter;
the 150 ms language-model latency it compares against is the figure from the website card, not a
measurement — the script labels it that way.

## Tests and machine checks

```bash
pip install -r requirements-dev.txt                # adds pytest and networkx
python -m pytest -q                                # the test suite (tests/)
python bench/check_claims.py                       # every number in the results sections against its file
python bench/reproduce.py                          # re-run everything, compare with results/ (FlyWire parts if downloaded)
```

The tests compare each script with an independent reference: the Aho–Corasick automaton with brute-force search on
300 random inputs; the three connectome scripts, on small synthetic connectomes in the FlyWire schema, with networkx
(clustering, path length, k-core, giant component) and with plain loops (transmitter shares); the RFC 6962 tree with
the Certificate Transparency vectors, with the recursive definition of the standard for every size up to 130 and with
every leaf's proof up to 70 leaves; the open arena with hand-computed metrics and `np.unpackbits`. They also check
that the stamped Merkle root, flag rate and Sign-LSH row are reproduced, that the manifests match byte for byte and
that every `.ots` proof stamps its manifest. The suite itself was checked by breaking the code on purpose
(`python tests/mutation/run_mutants.py`: ten deliberate bugs, each one caught by at least one test).

## Timestamps — how to check that the numbers were not changed later

The result files are timestamped with OpenTimestamps in Bitcoin blocks 968268–968274 (`results/*.ots`).
Verify with `ots verify results/MANIFEST_2026-09-23.sha256.ots` (needs a Bitcoin node) or by dropping the
`.ots` file and the file it stamps onto <https://opentimestamps.org>.

The state of 12 October 2026 — every script, test and result file, including §8 and §9 — is in
`results/MANIFEST_2026-10-12.sha256` with its OpenTimestamps proof next to it; a fresh proof is pending until a
Bitcoin block confirms it (usually a few hours) and is then completed with `ots upgrade`.

Then check the files against the stamped manifest **before** running anything:

```bash
sha256sum -c --ignore-missing results/MANIFEST_2026-09-23.sha256
```

Checked on a fresh clone on 27.09.2026: **56 OK and 1 FAILED — `README.md`.** The manifest stamps the
README of the full repository as it was on 23.09; this README is a new text written for the open part,
so it cannot match. All 56 result, methodology and script files that are present match. The other 52
lines refer to files that live in the paid repository — the engine (13), the benchmark scripts (33) and the
browser search file (1) — plus two withdrawn legacy results and three note lines about the FlyWire
source files; `--ignore-missing` skips them. The scripts write fresh runs to `bench/results/` (ignored by git)
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
bench/open_arena.py         §8 open retrieval arena with a plug-in API
bench/merkle_rfc6962.py     §9 RFC 6962 Merkle tree and inclusion proofs
bench/check_claims.py       every README number against its result file
bench/reproduce.py          re-run everything and compare with results/
tests/                      test suite (pytest)
results/                    machine-readable outputs, manifests and .ots proofs
CITATION.cff                how to cite this repository and the FlyWire data
```

## Author

Maksim Galatin — CODE Eternal / AIfa Works. Contact: contact@codeofdigitaleternity.com

Licensed under the PolyForm Noncommercial License 1.0.0 — see [LICENSE](LICENSE). Commercial use requires a written licence with payment to the licensor: contact@codeofdigitaleternity.com.
