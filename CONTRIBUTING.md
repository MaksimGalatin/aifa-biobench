# Contributing to AIfa-BioBench

This repository exists to be checked. The most useful contributions are the ones that try to prove us wrong.

## 1. Run the arena with your own method

`bench/open_arena.py` accepts any class with `build(X)` and `search(q, k)`:

```bash
python bench/open_arena.py --methods exact,signlsh,my_package.my_module:MyIndex
python bench/open_arena.py --suite                                   # the three configurations from README §8
python bench/open_arena.py --dataset npy --base base.npy --query query.npy --normalize   # your own embeddings
```

Then open an issue with the **Arena result** template and attach the JSON the script saves. Please include your
hardware, Python and NumPy versions and the exact command. You do not have to share your method's code — the
numbers and the command are enough for others to compare.

## 2. Report a number that does not reproduce

If `python bench/check_claims.py`, `python bench/reproduce.py` or the test suite (`python -m pytest -q`) disagrees
with anything in the README, open an issue with the **Reproduction problem** template and paste the full output.
A number we cannot defend is withdrawn and listed under "Not measured / withdrawn" — that has happened before.

## 3. Pull requests

Bug fixes, new baselines for the arena and new tests are welcome. Please run `python -m pytest -q` and
`python bench/check_claims.py` before opening the pull request.

The stamped files in `results/` (the manifests and their `.ots` proofs) are never edited — a changed result gets
a new file and a new manifest, so the old one stays checkable.

Licence: this repository is under PolyForm Noncommercial 1.0.0 (three tool files are MIT, see
`LICENSE-MIT-tools.txt`). By opening a pull request you agree that your contribution is licensed the same way.

Questions: contact@codeofdigitaleternity.com · https://aifa.works/acr
