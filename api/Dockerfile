# syntax=docker/dockerfile:1.7

# ---------- base : socle commun (utilisateur non-root, variables Python) ----------
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

# ---------- builder : installe les dépendances (jeté après le build) ----------
FROM base AS builder
COPY requirements.txt .
# Cache BuildKit : pip ne retélécharge pas les paquets entre deux builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt

# ---------- dev : rechargement automatique + tests (cible du compose.override.yml) ----------
FROM base AS dev
COPY --from=builder /install /usr/local
COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser tests ./tests
COPY --chown=appuser:appuser pytest.ini ./
USER 1000:1000
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- test : fait échouer le build si les tests échouent (docker build --target test) ----------
FROM dev AS test
RUN pytest -q

# ---------- runner : image de production, minimale ----------
FROM base AS runner
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser app ./app
USER 1000:1000
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
