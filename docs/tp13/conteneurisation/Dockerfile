# BROUILLON NON TESTÉ — à relire avant usage.
# Image du pipeline NutriScope. Elle contient le CODE et l'ÉCHANTILLON, jamais les données volumineuses.
FROM python:3.12-slim

# UTF-8 (évite les erreurs d'affichage ✓/✗), sorties non bufferisées, fuseau pour dater les fichiers
ENV PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Paris

WORKDIR /app

# 1) Les dépendances d'abord : cette couche est mise en cache tant que le fichier ne change pas
COPY requirements-pipeline.txt ./
RUN pip install --no-cache-dir -r requirements-pipeline.txt

# 2) Puis le code (change souvent)
COPY nutriscope/ ./nutriscope/
COPY src/ ./src/
COPY schema_nutriscope.sql ./
COPY data-nutriscope/ ./data-nutriscope/

# Pas de .git dans l'image : le commit est transmis à la construction
ARG GIT_COMMIT=unknown
ENV NUTRISCOPE_GIT_COMMIT=${GIT_COMMIT}

# Utilisateur non-root
RUN useradd --create-home app && mkdir -p /app/data && chown -R app:app /app
USER app

ENTRYPOINT ["python", "-m", "nutriscope.pipeline"]
CMD ["all"]
