# Synthèse de l'analyse exploratoire de référence — TP 10

> Notebook source : [`notebooks/eda_reference.ipynb`](../../notebooks/eda_reference.ipynb) ·
> figures : [`notebooks/figures/`](../../notebooks/figures/) ·
> registre : [`registre_hypotheses.csv`](registre_hypotheses.csv)

## Contexte

- **Données** : échantillon partagé `data-nutriscope/echantillon_france.csv` (8 689 produits).
- **Nettoyage** : pipeline du TP 9 (`src/cleaning.py`), validé contre `schema.OUTPUT_SCHEMA` ;
  8 689 → 5 316 produits.
- **Périmètre des comparaisons par rayon** : 5 108 produits, hors rayon `unknown`.
- **Rayon `unknown`** : 21,6 % de l'échantillon brut, 3,9 % après nettoyage ; écarté des
  comparaisons par rayon, sa complétude est donnée à part dans le notebook (section 2.1).

## Messages

1. _À rédiger : message et chiffre clé._
2. _À rédiger._
3. _À rédiger._
4. _À rédiger._
5. _À rédiger._
6. _À rédiger._

## Registre des hypothèses

| Hypothèse | Méthode | Résultat | Décision |
|---|---|---|---|
| H1 : les produits A ont moins de sucres que les E, dans tous les rayons | médianes, d de Cohen, Mann-Whitney, stratifié par rayon | _voir notebook_ | _à compléter_ |
| H2 : le sel est plus lié au score dans un rayon que tous rayons confondus | Spearman par rayon vs global | _voir notebook_ | _à compléter_ |
| H3 : _à formuler_ | | | |
| H4 : _à formuler_ | | | |

## Décisions par TP

- **TP 9 (nettoyage)** : _à compléter_
- **TP 11 (récit du marché)** : _à compléter_
- **TP 12 (stockage)** : _à compléter_
- **TP 14 (modèle)** : _à compléter_

## Limites

_À rédiger._

---

Données : © Open Food Facts contributors — [ODbL](https://opendatacommons.org/licenses/odbl/1-0/).
