
# Docker · Jour 3 — Stack LLM complète — CORRIGÉ FORMATEUR

Projet fil rouge de la formation Docker (3 jours) : déployer **un site web, une API, une base de données et un petit LLM**,
avec **Prometheus, Grafana et Loki** pour la supervision. Tout se lance avec Docker Compose.

![Topologie d'exécution de la stack LLM](docs/architecture.svg)

> Le détail des interactions (réseaux, ports, protocoles) et l'ordre de démarrage sont dans **[docs/architecture.md](docs/architecture.md)**.

## Prérequis
- Docker Engine / Docker Desktop avec **Compose ≥ 2.20** (`docker compose version`) et BuildKit.
- **6 Go de RAM alloués à Docker** (Docker Desktop : Settings → Resources) et ~12 Go de disque libre.
- Pour une lecture d'étiquette en ~3 s : une carte NVIDIA et la surcouche `compose.gpu.yml` (voir plus bas) ;
  sans GPU, la stack fonctionne mais le modèle de vision est beaucoup plus lent.
- Python 3 sur le poste (uniquement pour `scripts/check.py`).

## Démarrage
```bash
sh scripts/init-secrets.sh          # Windows PowerShell : .\scripts\init-secrets.ps1
docker compose up -d --build        # développement (charge compose.override.yml)
docker compose --profile monitoring up -d          # + supervision
docker compose -f compose.yml -f compose.prod.yml up -d --build   # production (APP_VERSION obligatoire)
# avec GPU NVIDIA (image CUDA de llama.cpp, modèle et module de vision sur le GPU) :
docker compose -f compose.yml -f compose.override.yml -f compose.gpu.yml up -d --build
```
Interfaces : site http://localhost:8080 · Grafana http://localhost:3000 (admin, mot de passe dans `secrets/grafana_admin_password.txt`) · Prometheus http://localhost:9090

> Le premier démarrage télécharge ~3,3 Go de modèle (Qwen3-VL-4B-Instruct `Q4_K_M` + module de vision F16) : `llm-init` puis `llm` sont longs à devenir *healthy*. Suivre : `docker compose logs -f llm-init llm`. Le modèle est servi par llama.cpp et non par Ollama : voir [ADR 0002](../adr/0002-llama-cpp-au-lieu-d-ollama.md).

> Le service `ollama` (embeddings `qwen3-embedding:0.6b`, ~0,6 Go, et juge Flow-Judge 3.8B, ~2,4 Go) est rempli au premier démarrage par `ollama-init` : `docker compose logs -f ollama-init`. Test depuis l'hôte : `curl http://localhost:11434/api/embed -d '{"model":"qwen3-embedding-cpu:0.6b","input":"Nutri-Score"}'`. Les embeddings tournent sur le processeur ; le juge ne sert qu'à l'évaluation, lancée après l'arrêt de llama.cpp (`python -m nutriscope.evaluation judge`, voir [ADR 0003](../adr/0003-embeddings-et-juge-sur-ollama.md)).
>
> Le service `chroma` démarre vide : `python -m nutriscope.rag.index --device gpu` le remplit (~11 min la première fois), puis `python -m nutriscope.rag.search "question"` l'interroge. Test depuis l'hôte : `curl http://localhost:8001/api/v2/heartbeat`. Voir [docs/ia/rag.md](../ia/rag.md) et l'[ADR 0004](../adr/0004-index-vectoriel-chroma.md).

## Jalons du TP
| # | Jalon | Fichiers à écrire |
|---|-------|-------------------|
| 1 | Images : Dockerfile multi-stage de l'API + Dockerfile du web + `.dockerignore` | `api/Dockerfile`, `api/.dockerignore`, `web/Dockerfile` |
| 2 | Stack applicative : services, réseaux, volumes, secrets, healthchecks | `compose.yml` |
| 3 | Composition de fichiers : durcissement partagé, surcouches dev et prod | `compose.common.yml`, `compose.override.yml`, `compose.prod.yml` |
| 4 | Monitoring : Prometheus, Grafana, Loki, Alloy, cAdvisor | `monitoring/compose.yml` |
| 5 | Sécurité & performance : tout passe `scripts/check.py` | — |
| 6 | Démonstration : question posée au LLM, dashboard Grafana, logs dans Loki | — |

Bonus : profil `backup` (pg_dump), scan de vulnérabilités (Trivy), règle d'alerte supplémentaire, 2 réplicas de l'API.

## Contraintes (contrôlées automatiquement)
- **Multi-stage** : API ≥ 3 stages, image finale < 250 Mo, cache BuildKit, `.dockerignore`.
- **Sécurité** : utilisateurs non-root, `read_only` + `tmpfs`, `cap_drop: [ALL]`, `no-new-privileges`, aucun mot de passe en clair (secrets fichiers), base sur réseau `internal`, `/metrics` jamais exposé, ports publiés sur `127.0.0.1` uniquement.
- **Performance / fiabilité** : limites CPU/RAM, rotation des logs, healthchecks + `depends_on` conditionnels, job `llm-init` en `service_completed_successfully`.
- **Observabilité** : cibles Prometheus UP, dashboard Grafana provisionné, logs JSON visibles dans Loki.

```bash
python scripts/check.py                 # contrôles statiques (mode prod)
python scripts/check.py --mode dev      # idem avec la surcouche dev
python scripts/check.py --runtime       # + contrôles sur la stack démarrée
```

## Fiche technique des briques
| Service | Image / source | Points clés |
|---------|----------------|-------------|
| db | `postgres:16-alpine` | env `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD_FILE=/run/secrets/db_password` ; données `/var/lib/postgresql/data` ; scripts `./db/init` → `/docker-entrypoint-initdb.d` ; `read_only` : tmpfs `/tmp` et `/run/postgresql` ; démarre en root puis bascule sur `postgres` : `cap_add` CHOWN, DAC_OVERRIDE, FOWNER, SETGID, SETUID ; healthcheck `pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}` |
| llm-init | `curlimages/curl:8.22.0` | `user: root`, `entrypoint: ["/bin/sh","-c"]` ; lit la liste des fichiers du dépôt `$LLM_HF_REPO` (API Hugging Face), télécharge le modèle `$LLM_QUANT` et le module de vision F16 vers `/models/$LLM_MODEL.gguf` et `/models/$LLM_MODEL-mmproj.gguf` s'ils n'existent pas ; volume `llm_models` ; `restart: "no"` |
| llm | `ghcr.io/ggml-org/llama.cpp:server-b11434` (`server-cuda-b11434` avec `compose.gpu.yml`) | arguments `--model /models/<LLM_MODEL>.gguf --mmproj /models/<LLM_MODEL>-mmproj.gguf --alias <LLM_MODEL> --ctx-size 4096 --parallel 1 --n-gpu-layers 99 --threads 4 --jinja --image-min-tokens 1024 --metrics --port 8080` ; volume `llm_models` en `:ro` ; `user: "1000:1000"` ; tmpfs `/tmp` ; healthcheck `curl -f http://localhost:8080/health` ; limite `LLM_MEMORY` (12 Go) ; publié en dev sur `127.0.0.1:8081` |
| ollama-init | `ollama/ollama:0.30.10` | `entrypoint: ["/bin/sh","-c"]` ; lance un `ollama serve` temporaire sur le réseau `egress`, tire `$OLLAMA_EMBED_MODEL` (`qwen3-embedding:0.6b`) et `$OLLAMA_JUDGE_MODEL` (Flow-Judge v0.1 3.8B `Q4_K_M`, GGUF Hugging Face) dans le volume `ollama_models`, crée `$OLLAMA_EMBED_ALIAS` (embeddings avec `num_gpu 0` et `$OLLAMA_EMBED_THREADS` threads : toujours sur le processeur), puis s'arrête ; `restart: "no"` |
| ollama | `ollama/ollama:0.30.10` | embeddings du RAG (`POST /api/embed`, sur le processeur) et juge Flow-Judge (GPU) ; réseau `inference` (interne, sans Internet) ; volume `ollama_models` ; `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=5m` ; healthcheck `ollama list` ; limite `OLLAMA_MEMORY` (10 Go) ; publié en dev sur `127.0.0.1:11434` ; GPU avec `compose.gpu.yml` |
| chroma | `chromadb/chroma:1.5.9` | base vectorielle du RAG, collections `sheets` et `documents` (remplies par `python -m nutriscope.rag.index`) ; réseau `inference` ; volume `chroma_data` (`/data`) ; `ANONYMIZED_TELEMETRY=FALSE` ; healthcheck `/api/v2/heartbeat` par `/dev/tcp` de bash (ni curl ni wget dans l'image) ; limite `CHROMA_MEMORY` (2 Go) ; publié en dev sur `127.0.0.1:8001` (8000 est pris par l'API) |
| api | `./api` (target `runner`) | port 8000 ; env `DB_HOST=db`, `DB_NAME`, `DB_USER`, `DB_PASSWORD_FILE`, `LLM_URL=http://llm:8080`, `LLM_MODEL`, `LOG_LEVEL` ; endpoints `/health/live`, `/health/ready`, `/api/chat`, `/api/history`, `/metrics` ; tmpfs `/tmp` |
| web | `./web` | nginx non-root sur **8080** (publier `127.0.0.1:8080:8080`) ; `/api/` proxifié vers `api:8000` ; `/healthz` ; tmpfs `/tmp` |
| prometheus | `prom/prometheus:v3.13.4` | `/etc/prometheus/prometheus.yml` et `alerts.yml` ← `monitoring/prometheus/` ; `--storage.tsdb.path=/prometheus` ; santé `/-/ready` |
| loki | `grafana/loki:3.7.8` | `-config.file=/etc/loki/loki-config.yml` ; données `/loki` ; santé `/ready` |
| alloy | `grafana/alloy:v1.20.1` | `run --server.http.listen-addr=0.0.0.0:12345 --storage.path=/var/lib/alloy/data /etc/alloy/config.alloy` ; monte `/var/run/docker.sock` en lecture seule |
| cadvisor | `ghcr.io/google/cadvisor:v0.60.6` | `--docker_only=true --housekeeping_interval=15s` ; monte `/`, `/var/run`, `/sys`, `/var/lib/docker` en `:ro` |
| grafana | `grafana/grafana:12.4.12` | `GF_SECURITY_ADMIN_PASSWORD__FILE=/run/secrets/grafana_admin_password` ; `GF_LOG_MODE=console` ; provisioning → `/etc/grafana/provisioning` ; dashboards → `/etc/grafana/dashboards` ; volume `/var/lib/grafana` |

## Structure du dépôt
```
api/            application FastAPI (code, tests et Dockerfile)
docs/           schémas d'architecture (SVG) et sources Mermaid
web/            front statique + nginx.conf (Dockerfile)
db/init/        schéma SQL
monitoring/     configs Prometheus / Loki / Alloy / Grafana + compose.yml
scripts/        init-secrets, pull-images, check.py
compose*.yml    solution complète
```

## Notes formateur
- Les fichiers `api/Dockerfile`, `web/Dockerfile`, `api/.dockerignore`, `compose*.yml` et `monitoring/compose.yml` de ce dépôt sont **la solution**. Le dépôt étudiant (starter) les remplace par des squelettes `TODO`.
- **La veille** : `sh scripts/pull-images.sh` (≈ 3 Go d'images) puis, si le Wi-Fi est limité, `docker save` / `docker load` ou un registre/cache local. Les fichiers GGUF (≈ 3,3 Go) sont téléchargés par chaque poste : les pré-déposer dans le volume `llm_models` sous les noms `<LLM_MODEL>.gguf` et `<LLM_MODEL>-mmproj.gguf`, et `llm-init` ne télécharge plus rien.
- Validé hors conteneurs : `docker compose config` (dev, prod), hadolint, promtool, `loki -verify-config`, `alloy validate`, provisioning Grafana, tests Python, chaîne nginx → API → PostgreSQL. **À faire avant le cours** : un `up` complet sur un poste type (cAdvisor sur Docker Desktop, durcissement de PostgreSQL et de llama.cpp, tailles d'images).
- Repli si cAdvisor ne remonte rien sous Docker Desktop : les panneaux CPU/RAM restent vides, le reste du dashboard fonctionne ; utiliser `docker stats` pour la démonstration.
