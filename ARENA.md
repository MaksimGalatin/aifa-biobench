# Open arena — rules

The open retrieval arena (`bench/open_arena.py`, README §8) is where anyone can put a retrieval method next to the
open baselines on the same data, the same seeds and the same metrics. These rules exist so that a result posted here
means the same thing as every other result here — including the results where our methods lose.

There are no prizes and no money involved. The only thing the arena gives is a published, timestamped comparison.

## 1. What a method is

Any Python class with

```python
class MyIndex:
    def build(self, X):            # X: (n, dim) float32
        ...
    def search(self, q, k):        # q: (dim,) float32 -> k row indices of X
        ...
    def index_bytes(self):         # optional: memory of the index, for the index_mb column
        ...
```

plugged in as `module.path:ClassName`:

```bash
python bench/open_arena.py --methods exact,signlsh,multitable,my_package.my_module:MyIndex
```

The arena gives your method the vectors and one query at a time; it measures recall@k and NDCG@k against exact
L2 ground truth (float32, full sort per query) and the latency of each `search` call. Your class must not read the
queries or the ground truth in `build`.

## 2. Fixed configurations and seeds

A result counts as an arena result only on one of the fixed configurations, run with the default seed:

| Name | Command | Data |
|---|---|---|
| isotropic | `--dataset gaussian` | 25,000 × 512, 100 independent queries, seed 42 |
| clustered | `--dataset clustered` | 25,000 × 512, 100 Gaussian clusters, noise 0.8, 100 queries, seed 42 |
| clustered, large | `--dataset clustered --n 100000 --dim 768 --queries 200` | 100,000 × 768, 200 queries, seed 42 |

`python bench/open_arena.py --suite --methods ...` runs all three and writes one file. k = 10 throughout.

Your own embeddings (`--dataset npy --base ... --query ... --normalize`) are welcome as a separate category. The
queries must not be copies of indexed rows — search for an exact copy measures nothing.

**Hyperparameters are fixed before the run.** If you tried several settings or several seeds, report every one of
them, not the best. A result picked from many runs is not comparable with a single run.

## 3. The report must show both outcomes

- Run your method **in the same invocation** as the baselines `exact`, `signlsh` and `multitable`, so that all rows
  come from the same machine, the same load and the same data.
- Report every row of the output against every baseline: where your method wins and where it loses, for recall,
  NDCG, latency and, if your class reports it, index size. A report that leaves out the rows where a baseline wins
  is not accepted.
- Attach the JSON file the script saves, unchanged. It records the Python and NumPy versions, the platform, the
  processor, the git commit of the arena and the exact command line, so you do not need to retype them.
- Say what hardware it ran on. Latency depends on machine load; recall on a given machine does not.

## 4. How to submit

Open an issue with the **Arena result** template (`.github/ISSUE_TEMPLATE/arena-result.md`) and attach the JSON.
You do not have to publish your method's code: the command, the numbers and the file are enough to compare. If the
code is public, link it.

## 5. What we publish and how it is fixed

- When the method's code is public, we re-run it on the reference machine of `bench/PROTOCOL.md` and publish both
  runs side by side. When it is not, the result is published as submitted and marked **not re-run**.
- The submitted JSON is copied into `results/arena/` byte for byte; nothing in it is edited, rounded or recomputed.
- Its SHA-256 goes into a new manifest `results/MANIFEST_<date>.sha256`, and that manifest is stamped with
  OpenTimestamps in Bitcoin, exactly like every other manifest in this repository (README, "Timestamps"). Anyone can
  check later that the published file is the one that was submitted.
- A stamped file is never changed. A correction is a new file with a new manifest; the old one stays checkable.

## 6. What the arena does not include

- FlyHash and the rest of the AIfa engine are not in the open arena — the engine is in the paid part of the
  repository. Their numbers are in README §1–§5, fixed by the timestamps there.
- The arena measures retrieval on these data only. A win on isotropic data does not transfer to real embeddings
  (README §8 explains why); the clustered and `npy` categories are there for that.

## 7. Rights

Your method stays yours. The numbers and the JSON you submit are published in this repository under its licence
(PolyForm Noncommercial 1.0.0). Questions: contact@codeofdigitaleternity.com
