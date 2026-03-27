# ── Base: shared Python + production deps ────────────────────────────────────
FROM python:3.12-slim AS base
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Test: run pytest before allowing a production build ──────────────────────
FROM base AS test
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
# Real API key not needed; all external calls are mocked in the test suite
RUN ANTHROPIC_API_KEY=test-key SECRET_KEY=test pytest -v --tb=short

# ── Production: lean final image ─────────────────────────────────────────────
FROM base AS prod
COPY . .
EXPOSE 5000
CMD ["gunicorn", \
     "--workers", "1", \
     "--threads", "2", \
     "--timeout", "60", \
     "--bind", "0.0.0.0:5000", \
     "app:app"]
