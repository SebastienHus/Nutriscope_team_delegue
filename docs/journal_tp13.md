# Journal de bord — TP 13 (Pipeline bout-en-bout, jalon J3)

> Journal dédié au TP 13. `docs/journal.md` (journal historique du projet) reste inchangé.
> On remplit au fil de la journée, une entrée à chaque jalon. Court mais daté.

- Date : mardi 14/10/2026
- Équipe : Team délégué
- Branche : `tp13-alternative-proposition` (créée depuis `develop`, commit `0fd7514`)
- Machine de mesure : _CPU / RAM / OS_ — Python _3.12.x_, pandas _x_, duckdb _x_, pyarrow _x_

## Objectif du jour
Une commande unique, du CSV brut aux exports ML. Split train/test figé (stratifié sur `nutriscore_grade`, graine 42). Tag `v0.3`.

## Chronologie
| Heure | Fait | Décidé | Bloqué / à creuser |
|---|---|---|---|
| 09:00 | | | |
| 10:30 | | | |
| 12:00 | | | |
| 14:30 | _échange des dépôts_ | | |
| 16:00 | | | |

## Décisions techniques (une ligne + pourquoi)
- [x] Point d'entrée : CLI Python `python -m nutriscope.pipeline` ; `Makefile` = façade (réalisé, voir `docs/tp13/JOURNAL_ACTIONS.md`).
- [x] **14/10 — Périmètre géographique : tous les pays.** Écart assumé avec le TP 2 (« commercialisé en France ») ; `perimetre.md` à mettre à jour.
- [x] **14/10 — `charger` par DuckDB** (texte, 41 colonnes, tri par code, plafond 12 Go) : 23 s, 0 perte sur 4 535 553 lignes.
- [x] **14/10 — `nettoyer` : code du TP 9 inchangé, en 8 lots** par hachage du code : 2,5 Go de pic, même résultat qu'en un bloc (996 637).
- [x] **14/10 — `src/` n'est pas modifié** : les corrections exigées par le TP 13 (tri, `_SUCCESS`, mot de passe, split…) sont faites dans `nutriscope/`, chacune tracée dans `docs/tp13/JOURNAL_ACTIONS.md`.
- [x] **14/10 — pas de commit automatique** : l'équipe relit le diff et committe elle-même.
- [x] Format du « nettoyé » : **Parquet** — raison : un CSV perd les types (entiers nullables, dates, booléens).
- [x] Algorithme du split : **rang par md5('42:' || code) dans chaque grade, 20 % de test** — raison : affectation stable produit par produit, indépendante de l'ordre des lignes et des versions de bibliothèques.
- [x] Conteneur : **pas pour le J3** (décision du 14/10) ; code rendu compatible, brouillons dans `docs/tp13/conteneurisation/`.
- [ ] Où est posé le tag `v0.3` : _develop / main_ — raison : …

## Dette technique notée (briques branchées telles quelles, non refaites)
| Brique | Problème connu | Reporté à |
|---|---|---|
| | | |

## Résultats des points de contrôle
| PC | Critère | OK ? | Preuve (commande / sortie) |
|---|---|---|---|
| 1 | `all` enchaîne 5 étapes, comptages base = Parquet | | |
| 2 | `exports` seule retrouve le Parquet ; `parquet` ×2 = mêmes empreintes | | |
| 3 | part de test par grade ≈ 20 % ; `--force` redonne le même SHA-256 | | |
| 4 | une autre équipe a obtenu nos sorties ; corrections committées | | |
| 5 | `docs/data/pipeline.md` lisible en 5 min | | |
| 6 | `pytest` vert, tag `v0.3`, `git status` sans données | | |

## Durées mesurées (copiées du journal JSONL, pas estimées)
| Étape | Échantillon | Extrait complet |
|---|---|---|
| charger | | 23 s (banc d'essai) |
| nettoyer | | 3 min 08 s en 8 lots / 2 min 27 s en 1 bloc (banc d'essai) |
| charger_base | | |
| parquet | | |
| exports | | |
| **Total** | | |

## Test « machine vierge »
**Notre test sur notre dépôt (clone frais, venv neuf / Docker)**
- Ce qui a cassé : …
- Correction (commit) : …

**Notre test sur le dépôt de l'autre équipe**
- Équipe : …
- Endroits où nous avons dû deviner : …
- Liste remise par écrit : oui / non

## Incidents et leçons
- …

## Bilan de fin de journée
- Fait :
- Reste à faire :
- Ce que nous avons appris :
