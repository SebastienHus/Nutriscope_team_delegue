#!/usr/bin/env sh
# Formateur : pré-télécharger toutes les images la veille (ou les exporter : docker save ... | gzip > images.tgz).
set -e
for img in \
  postgres:16-alpine \
  ollama/ollama:0.30.10 \
  python:3.11-slim \
  nginxinc/nginx-unprivileged:1.30-alpine \
  prom/prometheus:v3.13.4 \
  grafana/grafana:12.4.12 \
  grafana/loki:3.7.8 \
  grafana/alloy:v1.20.1 \
  ghcr.io/google/cadvisor:v0.60.6 ; do
  docker pull "$img"
done
