"""
AIfa-BioBench — neurotransmitter shares in the REAL FlyWire v783 connectome.

For each connection row the release gives the average predicted probability of each
transmitter (gaba_avg, ach_avg, glut_avg, oct_avg, ser_avg, da_avg). Weighting these
by syn_count gives the expected share of synapses per transmitter; the arg-max per row,
weighted by syn_count, gives the share of synapses whose most likely transmitter is X.

Data: bench/data/ (Zenodo 10.5281/zenodo.10676866, CC BY 4.0).
Usage: python bench/connectome_transmitters.py
"""
import json, os, platform, time
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
COLS = {"ach_avg": "acetylcholine", "gaba_avg": "GABA", "glut_avg": "glutamate",
        "da_avg": "dopamine", "ser_avg": "serotonin", "oct_avg": "octopamine"}


def main():
    t0 = time.time()
    df = pd.read_feather(os.path.join(DATA, "proofread_connections_783.feather"),
                         columns=["syn_count"] + list(COLS))
    w_all = df["syn_count"].to_numpy(np.float64)
    P_all = df[list(COLS)].to_numpy(np.float64)
    ok = ~np.isnan(P_all).any(axis=1)          # rows without a transmitter prediction are excluded
    w, P = w_all[ok], P_all[ok]
    expected = (P * w[:, None]).sum(axis=0)
    expected = expected / expected.sum()
    top = P.argmax(axis=1)
    argmax_share = np.bincount(top, weights=w, minlength=len(COLS)) / w.sum()
    res = {
        "benchmark": "AIfa-BioBench — transmitter shares, real FlyWire v783",
        "synapses_total": int(w_all.sum()),
        "synapses_with_prediction": int(w.sum()),
        "rows_excluded_no_prediction": int((~ok).sum()),
        "expected_share_by_synapses": {COLS[c]: round(float(v), 4) for c, v in zip(COLS, expected)},
        "argmax_share_by_synapses": {COLS[c]: round(float(v), 4) for c, v in zip(COLS, argmax_share)},
        "provenance": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runtime_s": round(time.time() - t0, 1)},
    }
    out = os.path.join(HERE, "results", "connectome_transmitters.json")
    if os.path.isdir(os.path.join(HERE, "..", "results")) and not os.path.isdir(os.path.join(HERE, "results")):
        out = os.path.join(HERE, "..", "results", "connectome_transmitters.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
