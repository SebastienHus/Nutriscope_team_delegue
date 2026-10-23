# Architecture des données NutriScope

La base relationnelle sert l'application, les Parquet servent l'analyse et le ML. Les deux
sont produits à partir du **même** catalogue nettoyé : c'est la source de vérité unique,
et le pipeline vérifie qu'ils comptent le même nombre de produits.

```text
export Open Food Facts ──► nettoyé (data/clean/) ──┬──► PostgreSQL ──────────► application
                                                   │
                                                   └──► Parquet par rayon ──┬──► analyse (DuckDB, notebooks)
                                                        (data/parquet/)     │
                                                                            └──► export figé + split ──► ML
                                                                                 (data/exports/)
```

## Qui lit quoi

| Stockage                         | Format                      | Lecteur                        | Pourquoi ce format                                        |
| -------------------------------- | --------------------------- | ------------------------------ | --------------------------------------------------------- |
| Base `nutriscope`                | PostgreSQL, tables normalisées | application (fiches, comparaison) | lectures par code-barres, contraintes d'intégrité, mises à jour |
| `data/parquet/products_<date>/`  | Parquet ZSTD, partitionné par rayon | notebooks d'analyse, export ML | lectures en colonnes, filtres par rayon sans tout lire     |
| `data/exports/features_*`        | Parquet + `schema.json`     | modèles de la phase 4          | jeu figé, daté, avec split : comparaisons reproductibles   |

Le détail du flux, des commandes et des durées est dans
[`docs/data/pipeline.md`](data/pipeline.md).
