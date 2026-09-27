# AIfa Cognitive Runtime — Evaluation Protocols (PROTOCOL.md)

This document establishes the canonical testing and evaluation protocols for the AIfa Cognitive Runtime (ACR) and the AIfa-BioBench suite.

---

## 1. Reference Hardware Environment

- **Workstation Processor:** Intel(R) Core(TM) i7-14700 (20 Physical Cores: 8 Performance Cores + 12 Efficient Cores, 28 Logical Threads)
- **Base Frequency:** 2.10 GHz (Boost up to 5.40 GHz)
- **L3 Cache:** 33 MB Intel Smart Cache (L1/L2 cache resident working set ~128-512 KB)
- **Instruction Sets:** AVX2, FMA3, POPCNT, BMI2
- **RAM:** 64 GB DDR5
- **OS Environment:** Windows 11 Pro 64-bit / Linux x86_64 container
- **Python Runtime:** Python 3.12+ / 3.14 with pure NumPy 2.x

---

## 2. Protocol A: Smoke & Deterministic Vector Search (FlyHash Bionic Index)

### Objective
Measure Approximate Nearest Neighbor (ANN) retrieval quality, indexing throughput, memory footprint, and query latency against Exact Brute-Force L2 Ground Truth under deterministic synthetic conditions.

- **Dataset Size (N):** 50,000 vectors (scalable to 1,000,000)
- **Dimensionality (D):** 1024-d / 512-d unit-normalized float32 embeddings
- **Projection (m):** 2048 Kenyon cell projection units (6-claw random sparse connections)
- **Sparsification (k-WTA):** Top 30% active units (efficiency-tuned, not the biological 5% — decision made 20.09.2026 in favor of retrieval effectiveness over biological fidelity)
- **Query Set:** 200 queries (`independent`: fresh vectors; `smoke`: noisy copies of indexed vectors)
- **Rerank Candidate Pool:** 250 candidates via packed bitwise Hamming XOR + POPCNT
- **Ground Truth:** Exact Brute-Force L2 Euclidean Distance calculation
- **Measured Metrics (independent protocol; files: `results/result.json`, `results/rerun_2026-09-23_independent/`):**
  - Recall@10: 39.55%
  - P50 Latency: 43.9 ms (23.09.2026) · 59.0 ms (21.09.2026) — varies with machine load; recall is deterministic
  - Exact FAISS IndexFlatL2 on the same data: 100% recall, 8.8 ms (23.09.2026)
  - Index size: ~215 MB (50K vectors)
  - 21.09.2026: previously stated targets on this page (Recall@10 98.7%,
    P50 < 1.0 ms) were never achieved and are corrected here — see
    `bench/aifa_biobench.py` output and `results/` for raw artifacts.

---

## 3. Protocol B: Agent Task Loop with Real Engines

### Objective
Run the actual `aifa_sdk` engines (APL, CANN, CX, bilateral verifier) inside a navigation agent and measure task success, not a scripted outcome.

- **Script:** `bench/acr_agent_real_benchmark.py --seeds 30 --distractor-rate 0.35` (also 0.0 and 0.7)
- **Environment:** synthetic websites with menu hints; 35% distractor links
- **Sample Size:** 9 agent configurations × 360 episodes
- **Result (distractors 0.35):** goal pinned 5.8% · ACR as shipped 1.4% · ACR with CX loop-avoidance fixed 94.7% · full ACR + verifier 93.6% · standard + visited-link memory 95.0%
- **Finding:** the gain comes from visited-link memory; `cx_steering.py` keeps `visited_action_hashes` but never uses it.
- **Measured engine latencies (21.09.2026):** APL 35.5 μs (N=512), bilateral verifier 4.3 μs, CX ranking 190 μs P50. No script measures a fused "58 μs" loop; earlier figures (APL 14 μs, CX 8 μs, "58 μs hot path") are withdrawn.
- **Legacy:** `bench/acr_agent_e2e_benchmark.py` (6,000 episodes, 22.47% → 94.58%) sets outcomes by fixed probabilities and is kept only for the record.

### Robustness
- **Script:** `bench/robustness_real.py --seeds 5 --bits 512 --pool 50` — real bit dropout and neuron death.
- **Result:** at 50% dropout FlyHash Recall@10 25.4% vs Sign-LSH 78.2%; CANN idle error 0.13° → 14.6°.
- **Legacy:** `bench/acr_robustness_suite.py` ("3.21× more robust") is formula-generated.

---

## 4. Protocol C: Multi-Baseline Arena & Biological Degree Optimization

### Objective
Provide direct, fair duels against industry-standard binary retrieval algorithms (Sign-LSH / BQ 1-Bit, Multi-Table LSH, FAISS BinaryFlat) and sweep dendritic claw degrees d in [2..16].

- **Claw Sweep Range:** d = 2, 3, 4, 5, 6 (Biological Drosophila), 7, 8, 10, 16
- **Arena Baselines:**
  - AIfa FlyHash: 6-Claw Sparse WTA + Exact Rerank
  - Sign-LSH / BQ 1-Bit: Dense Gaussian Random Projections + Exact Rerank
  - Multi-Table LSH: Multi-table bucket hashing
  - FAISS IndexBinaryFlat: Hardware-accelerated exhaustive Hamming baseline

---

## 5. Cryptographic Provenance

- **FlyWire v783 source files:** md5 checksums from Zenodo 10.5281/zenodo.10676866 (see `bench/data/README.md`).
- **AIfaFocus National Accessibility Registry:** Bitcoin OpenTimestamps, block 965 040 (verified 23.09.2026).
- **Connectome root stamp:** earlier references (block 861 420 here, block 967 238 on the website) could not be verified — the stamp file holds no attestation. A new stamp is being issued; this section will name the block once it is confirmed.
