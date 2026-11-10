# What licence covers what

A one-page map of the licences already in this repository. It adds nothing to them; if this page and a licence file
disagree, the licence file wins. Not legal advice.

| Path | Licence | Commercial use |
|---|---|---|
| `bench/open_arena.py`, `bench/check_claims.py`, `bench/merkle_rfc6962.py` | MIT ([LICENSE-MIT-tools.txt](LICENSE-MIT-tools.txt)), in addition to PolyForm Noncommercial, since 13 Oct 2026 | **yes**, under MIT |
| every other file: scripts in `bench/`, `tests/`, `results/`, the README and docs | PolyForm Noncommercial 1.0.0 ([LICENSE](LICENSE)) | only under a written licence: contact@codeofdigitaleternity.com |
| FlyWire v783 connectome data (downloaded by `bench/data/fetch.py`, not committed) | CC BY 4.0, licence of its authors ([10.5281/zenodo.10676866](https://doi.org/10.5281/zenodo.10676866)) | yes, with attribution to the authors |
| The engine and the remaining benchmark scripts (AIfa-BioBench Pro) | commercial, private repository | under a written licence |

Why the three MIT files still name PolyForm in their headers: they are hash-stamped in
`results/MANIFEST_2026-10-12.sha256` (OpenTimestamps on Bitcoin), so their bytes are not edited; the MIT grant is in
`LICENSE-MIT-tools.txt`.

## Can I …?

- **Reproduce the published numbers, study and modify the scripts for research or teaching?** Yes (PolyForm Noncommercial).
- **Use the arena, the claims checker or the Merkle tree in a commercial product?** Yes (MIT).
- **Use the other scripts or the results in a commercial product?** Only with a written licence.
- **Use the FlyWire data commercially?** Yes under CC BY 4.0, citing Dorkenwald et al. and Schlegel et al., Nature 634 (2024).
