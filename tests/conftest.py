# Общие пути для тестов: корень репозитория и папка bench/ в sys.path, чтобы импортировать скрипты как модули.
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, "bench")
RESULTS = os.path.join(ROOT, "results")
if BENCH not in sys.path:
    sys.path.insert(0, BENCH)
