# FlyWire v783 connectome data

`bench/connectome_real_metrics.py` reads two files from this folder. They are not committed (852 MB).

Source: Zenodo record [10.5281/zenodo.10676866](https://doi.org/10.5281/zenodo.10676866) — "FlyWire Whole-brain Connectome Connectivity Data", license CC BY 4.0. Record metadata: `zenodo_10676866.json`.

| File | md5 |
|---|---|
| `proofread_connections_783.feather` | `f48f972d262323a102aed49af1396b8a` |
| `proofread_root_ids_783.npy` | `e0e6c19732fd8c7a4e39a2d170105421` |

```bash
cd bench/data
curl -L -o proofread_connections_783.feather "https://zenodo.org/api/records/10676866/files/proofread_connections_783.feather/content"
curl -L -o proofread_root_ids_783.npy "https://zenodo.org/api/records/10676866/files/proofread_root_ids_783.npy/content"
```

Please cite: Dorkenwald et al., "Neuronal wiring diagram of an adult brain", Nature 634 (2024), and Schlegel et al., Nature 634 (2024).
