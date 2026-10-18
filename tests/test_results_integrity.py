# Целостность заверенного: каждый файл results/*.json читается, манифесты сходятся побайтно (на любой ОС,
# без sha256sum), рядом с каждым манифестом лежит метка OpenTimestamps, каждое число README — из своего файла.
import glob
import hashlib
import json
import os

import pytest

from conftest import ROOT, RESULTS

# Файлы, которые после даты манифеста законно сменили текст; их заверенные версии — в истории git:
#  23.09: README.md (текст полного репозитория), LICENSE и заголовки двух скриптов (смена лицензии 05.10, 067f3af);
#  05.10: README.md (12.10.2026 дописаны разделы 8–9, тесты и исправлено NDCG 0.872 -> 0.871; версия 05.10 — 18b7e64).
#  12.10: README.md (18.10.2026 бейдж DOI Zenodo) и CITATION.cff (версия 2026.10.18 для архивного релиза Zenodo);
#         и сам этот тест (дописана строка 12.10); заверенные версии 12.10 — 926629d.
CHANGED_SINCE = {
    "MANIFEST_2026-09-23.sha256": {"README.md", "LICENSE", "bench/olfactory_filter_run.py", "bench/proof_of_connectome.py"},
    "MANIFEST_2026-10-05.sha256": {"README.md"},
    "MANIFEST_2026-10-12.sha256": {"README.md", "CITATION.cff", "tests/test_results_integrity.py", "bench/reproduce.py"},
}
OTS_MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"  # заголовок формата .ots


def manifest_lines(name):
    for line in open(os.path.join(RESULTS, name), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            digest, path = line.split(None, 1)
            yield digest, path.lstrip("*")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def test_every_result_json_parses():
    files = glob.glob(os.path.join(RESULTS, "**", "*.json"), recursive=True)
    assert len(files) >= 45                         # 48 заверенных на 12.10.2026 плюс новые
    for p in files:
        with open(p, encoding="utf-8") as fh:
            json.load(fh)


@pytest.mark.parametrize("name", sorted(os.path.basename(p) for p in glob.glob(os.path.join(RESULTS, "MANIFEST_*.sha256"))))
def test_manifest_matches_files_present(name):
    checked = 0
    for digest, path in manifest_lines(name):
        full = os.path.join(ROOT, path)
        if path in CHANGED_SINCE.get(name, set()) or not os.path.exists(full):
            continue                                    # нет в открытой части (лежит в платной) или законно изменён
        assert sha256(full) == digest, f"{path} differs from {name}"
        checked += 1
    assert checked >= 20, f"{name}: only {checked} files checked"


def test_result_files_use_lf_line_endings():
    # найдено 12.10.2026 перед отправкой: json.dump на Windows пишет CRLF, git отдаёт LF — хеш в манифесте
    # перестаёт сходиться на любой другой машине. Скрипты теперь пишут newline="\n"; этот тест держит весь класс.
    for p in glob.glob(os.path.join(RESULTS, "**", "*"), recursive=True):
        if p.endswith((".json", ".csv", ".log", ".sha256")):
            with open(p, "rb") as fh:
                assert b"\r\n" not in fh.read(), p


def test_latest_manifest_covers_every_tracked_result_file():
    latest = sorted(glob.glob(os.path.join(RESULTS, "MANIFEST_*.sha256")))[-1]
    listed = {p for _, p in manifest_lines(os.path.basename(latest))}
    for p in glob.glob(os.path.join(RESULTS, "**", "*.json"), recursive=True):
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        assert rel in listed, f"{rel} is not in {os.path.basename(latest)}"


def test_every_manifest_has_an_opentimestamps_proof():
    for m in glob.glob(os.path.join(RESULTS, "MANIFEST_*.sha256")):
        with open(m + ".ots", "rb") as fh:
            head = fh.read(len(OTS_MAGIC) + 1 + 1 + 32)
        assert head.startswith(OTS_MAGIC), m
        # после магии: версия (1), тег хеша 0x08 = SHA-256, затем 32 байта — хеш самого манифеста
        assert head[len(OTS_MAGIC) + 1] == 0x08
        assert head[len(OTS_MAGIC) + 2:].hex() == sha256(m), f"{m}.ots stamps a different file"


def test_every_readme_number_matches_its_result_file():
    import check_claims
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    rows = check_claims.check(text)
    bad = [(sec, want, src) for sec, ok, src, want, _ in rows if not ok]
    assert not bad, bad
    assert len(rows) >= 60
