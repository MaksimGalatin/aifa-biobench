# Copyright (c) 2026 CODE Eternal LLC — https://aifa.works
# Licensed under the PolyForm Noncommercial License 1.0.0 — commercial use only under a written licence:
# contact@codeofdigitaleternity.com
"""Prove that a file differs from a stamped manifest only by its Copyright line.

On 24 Nov 2026 (commit 24db721) the copyright holder became "CODE Eternal LLC" in LICENSE and in the
header of seven scripts. The manifests are timestamped with OpenTimestamps and are never rewritten, so
instead of dropping these files from the check, this script puts the old Copyright line back and requires
the SHA-256 to equal the stamped value. Any other change in the file still fails.

Usage: python bench/check_header_only.py results/MANIFEST_2026-10-12.sha256 LICENSE bench/open_arena.py ...
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# New line (24 Nov 2026) -> line as stamped in the manifests. Whole-line matches only.
OLD_LINE = {
    "# Copyright (c) 2026 CODE Eternal LLC — https://aifa.works":
        "# Copyright (c) 2026 Maksim Galatin & CODE (Code of Digital Eternity) — https://aifa.works",
    "# Copyright (c) 2026 CODE Eternal LLC":
        "# Copyright (c) 2026 CODE Eternal Ecosystem & Maksim Galatin",
    "Copyright (c) 2026 CODE Eternal LLC — https://aifa.works":
        "Copyright (c) 2026 Maksim Valentinovich Galatin & CODE (Code of Digital Eternity) — https://aifa.works",
    "Required Notice: Copyright (c) 2026 CODE Eternal LLC — https://aifa.works":
        "Required Notice: Copyright (c) 2026 Maksim Valentinovich Galatin & CODE (Code of Digital Eternity) — https://aifa.works",
}


def stamped(manifest: Path) -> dict[str, str]:
    out = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            out[name.lstrip("*")] = digest
    return out


def restored_digest(path: Path) -> tuple[str, int]:
    lines = path.read_bytes().decode("utf-8").split("\n")
    swapped = 0
    for i, line in enumerate(lines):
        if line in OLD_LINE:
            lines[i] = OLD_LINE[line]
            swapped += 1
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(), swapped


def main(argv: list[str]) -> int:
    manifest, files = Path(argv[0]), argv[1:]
    want = stamped(manifest)
    bad = 0
    for name in files:
        digest, swapped = restored_digest(Path(name))
        ok = name in want and digest == want[name] and swapped == 1
        print(f"{name}: {'OK' if ok else 'FAILED'} (copyright lines restored: {swapped})")
        bad += not ok
    print(f"{len(files) - bad} of {len(files)} differ from {manifest.name} only by the Copyright line")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
