# Reproduce the open part of AIfa-BioBench in a fixed environment (10.11.2026).
#   docker build -t aifa-biobench .
#   docker run --rm aifa-biobench                                   # tests + quick re-run (no connectome data, ~1 min)
#   docker run --rm -v "$PWD/bench/data:/app/bench/data" aifa-biobench \
#       sh -c "python bench/data/fetch.py && python bench/reproduce.py"   # full re-run with FlyWire v783 (≈ 853 MB)
# The CI runs the same on Linux, Windows and macOS with Python 3.10–3.13; this image uses 3.13.
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
CMD ["sh", "-c", "python -m pytest -q && python bench/check_claims.py && python bench/reproduce.py --skip-connectome"]
