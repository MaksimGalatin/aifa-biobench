"""bench/data/fetch.py берёт имена, размеры и md5 из метаданных Zenodo; таблица в bench/data/README.md должна им
совпадать (10.11.2026)."""
import importlib.util
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "bench" / "data"


def _fetch():
    spec = importlib.util.spec_from_file_location("fetch", DATA / "fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_expected_comes_from_zenodo_metadata():
    exp = _fetch().expected()
    assert set(exp) == {"proofread_connections_783.feather", "proofread_root_ids_783.npy"}
    assert all(re.fullmatch(r"[0-9a-f]{32}", v["md5"]) and v["size"] > 0 for v in exp.values())


def test_readme_table_matches_metadata():
    readme = (DATA / "README.md").read_text(encoding="utf-8")
    for name, v in _fetch().expected().items():
        assert re.search(rf"`{re.escape(name)}`\s*\|\s*`{v['md5']}`", readme), name


def test_md5_of_a_file(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"flywire")
    import hashlib
    assert _fetch().md5(f) == hashlib.md5(b"flywire").hexdigest()
