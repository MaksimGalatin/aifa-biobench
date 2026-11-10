# -*- coding: utf-8 -*-
"""Download the two FlyWire v783 files the connectome scripts read, and verify them.

The file names, sizes and md5 sums are taken from the Zenodo record metadata committed next to this script
(`zenodo_10676866.json`, record 10.5281/zenodo.10676866, CC BY 4.0) — not typed by hand. A file that is already
here with the right md5 is kept; a download with a wrong md5 is kept aside as `<name>.bad` and the script exits 1.

Run:  python -I -X utf8 bench/data/fetch.py            # download what is missing (≈ 853 MB), verify everything
      python -I -X utf8 bench/data/fetch.py --check    # verify only, download nothing
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORD = HERE / "zenodo_10676866.json"
NEEDED = ("proofread_connections_783.feather", "proofread_root_ids_783.npy")
URL = "https://zenodo.org/api/records/10676866/files/{name}/content"


def expected() -> dict:
    meta = json.loads(RECORD.read_text(encoding="utf-8"))
    files = meta.get("files") or []
    if isinstance(files, dict):
        files = files.get("entries", files)
        files = files.values() if isinstance(files, dict) else files
    out = {}
    for f in files:
        name = f.get("key") or f.get("filename")
        if name in NEEDED:
            algo, _, digest = str(f.get("checksum", "")).partition(":")
            out[name] = {"md5": digest if algo == "md5" else None, "size": int(f.get("size") or 0)}
    missing = set(NEEDED) - set(out)
    if missing:
        sys.exit(f"the Zenodo metadata has no entry for {sorted(missing)}")
    return out


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(name: str, target: Path) -> None:
    part = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(URL.format(name=name), timeout=120) as r, open(part, "wb") as out:
        done = 0
        for block in iter(lambda: r.read(1 << 20), b""):
            out.write(block)
            done += len(block)
            if done % (50 << 20) < (1 << 20):
                print(f"  {name}: {done >> 20} MB", flush=True)
    part.replace(target)


def main() -> int:
    check_only = "--check" in sys.argv
    ok = True
    for name, want in expected().items():
        target = HERE / name
        if not target.exists():
            if check_only:
                print(f"MISSING {name}")
                ok = False
                continue
            print(f"downloading {name} ({want['size'] >> 20} MB)")
            download(name, target)
        got = md5(target)
        if got == want["md5"] and target.stat().st_size == want["size"]:
            print(f"OK      {name}  md5 {got}")
        else:
            ok = False
            print(f"BAD     {name}  md5 {got}, expected {want['md5']}; size {target.stat().st_size}, expected {want['size']}")
            if not check_only:
                target.replace(target.with_suffix(target.suffix + ".bad"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
