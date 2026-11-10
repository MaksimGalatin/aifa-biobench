# 10.11.2026. Таблица побед и поражений на первой странице README строится из results/ скриптом
# bench/scoreboard.py. Эти тесты держат три вещи: таблица в README совпадает с генерацией байт в байт;
# правило победителя работает в обе стороны и даёт ничью в пределах разброса; в таблице есть строки,
# где выигрывает базовая линия (принцип репозитория — показывать и проигрыши).
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))

import scoreboard  # noqa: E402


def readme():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


def test_readme_table_matches_generation():
    assert scoreboard.readme_block(readme()) == scoreboard.block(), \
        "README wins-and-losses table differs from the result files: run python bench/scoreboard.py --write"


def test_winner_rule():
    w = scoreboard.winner
    assert w(0.9, 0.5, "higher") == scoreboard.OURS
    assert w(0.4, 0.5, "higher") == scoreboard.BASE
    assert w(3.0, 9.0, "lower") == scoreboard.OURS
    assert w(9.0, 3.0, "lower") == scoreboard.BASE
    assert w(0.936, 0.950, "higher", spread=0.055) == scoreboard.TIE
    assert w(0.014, 0.058, "higher", spread=0.038) == scoreboard.BASE
    assert w(0.5, 0.5, "higher") == scoreboard.TIE


def test_table_publishes_losses_and_is_complete():
    rows = list(scoreboard.rows())
    winners = [r[6] for r in rows]
    assert len(rows) >= 9
    assert winners.count(scoreboard.BASE) >= 1, "a table with no losses would break the rule of this repository"
    assert all(r[1].startswith("§") and r[4] and r[5] for r in rows)
    # каждое значение таблицы стоит и в README, и в сгенерированном блоке
    text = readme()
    assert all(r[4] in text and r[5] in text for r in rows)


def test_check_mode_fails_on_a_changed_table(tmp_path, monkeypatch):
    broken = readme().replace("| 39.55% |", "| 99.99% |", 1)
    (tmp_path / "README.md").write_text(broken, encoding="utf-8")
    monkeypatch.setattr(scoreboard, "ROOT", str(tmp_path))
    assert scoreboard.main(["--check"]) == 1
