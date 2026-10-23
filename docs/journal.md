# Journal de Bord - Exploration Data NutriScope

## Justification du Choix du Jeu de Données

Les données utilisées proviennent d'Open Food Facts : https://world.openfoodfacts.org/data

Plusieurs formats proposés :
- Dump MongoDB (> 14 Go) — écartée pour son volume
- Format Parquet — temps de chargement trop importants en phase exploratoire
- **Exports CSV segmentés** — retenus pour rapidité et flexibilité

### Segmentation initiale
Le dataset est divisé en plusieurs catégories :
- Produits alimentaires
- Produits cosmétiques  
- Produits pour animaux
- Autres produits

Choix retenu : **Produits alimentaires** (économie ~5 Go).

---

## Phase 1 : Exploration Initiale

### Objectif
Identifier les colonnes exploitables et vérifier la présence d'informations essentielles.

### Colonnes clés recherchées
- Identifiant produit (code)
- Nom du produit (product_name)
- Pays de commercialisation (countries)
- Marque (brands)
- Informations nutritionnelles :
  - Énergie (energy_100g)
  - Sucres (sugars_100g)
  - Sel (salt_100g)
- Indicateur de disponibilité data (no_nutrition_data)

### Outil utilisé
DuckDB pour manipulation directe de fichiers CSV volumineux sans base intermédiaire.

---

## Phase 2 : Identification des Produits Français

### Approche initiale
Filtrage sur colonne `countries` — résultats disparates et infiables.

### Solution retenue
Utilisation de `countries_tags` avec nomenclature normalisée.

### Principes de sélection
- Produits français : OUI
- Produits étrangers commercialisés en France : OUI
- Territoires DOM-TOM : OUI
- Chaque enregistrement peut contenir plusieurs pays

### Résultat
**1 136 108 produits** vendus en France et DOM-TOM identifiés.

---

## Phase 3 : Statistiques Principales

| Métrique | Valeur |
|----------|--------|
| Produits avec nom valide | ~1.1M |
| Part avec Nutri-Score renseigné | 44,91 % |
| Taux manquant energy_100g | 23,51 % |
| Taux manquant sugars_100g | 24,12 % |
| Taux manquant salt_100g | 28,73 % |

### Top 10 Marques
1. Carrefour (15 121)
2. Auchan (13 569)
3. U (11 856)
4. Leader Price (5 422)
5. Casino (5 071)
6. Cora (3 935)
7. Le Gaulois (3 418)
8. Picard (3 405)
9. Nestlé (3 310)
10. Monoprix (3 260)

---

## Phase 4 : Qualité Observée

### Observations Principales
- **Hétérogénéité** : Plusieurs langues, formats multiples
- **Segmentation complexe** : Régions, DOM-TOM, origines disparates
- **Inconsistances structurelles** : CSV vs Parquet offrent structures différentes

### Défis Identifiés
1. Nomenclature très variable dans Open Food Facts
2. Doublons potentiels sur les codes-barres
3. Valeurs nutritionnelles souvent incomplètes
4. Hétérogénéité des champs de catégorisation

---

## Conclusion

Le dataset Open Food Facts, malgré ses imperfections, constitue une source fiable et exploitable pour le projet NutriScope. Les phases d'exploration ont mis en évidence les nécessités d'un pipeline de nettoyage rigoureux, de normalisation des données et de définition précise des seuils de complétude minimale pour les analyses ultérieures.

Le volume disponible (~1,1M produits français) offre une base solide pour l'entraînement des modèles et la fourniture du service.

---

## TP 13 à 15 : pipeline, package et phase 4

### Décisions

- **Package `nutriscope`** : le code passe de `src/*.py` (imports à plat, `sys.path`
  modifié dans les tests, les scripts et les notebooks) à `src/nutriscope/`, installé par
  `pip install -e .`. Les commandes deviennent `python -m nutriscope.<module>`.
- **Pipeline bout-en-bout** (`python -m nutriscope.pipeline all`) : cinq étapes datées,
  idempotentes, journalisées dans `data/logs/pipeline_runs.jsonl`. Voir
  `docs/data/pipeline.md`.
- **Split figé** : colonne `split` ajoutée à l'export, stratifiée sur le grade, 20 % de
  test, graine 42 (section `[training]` de `database_options.ini`).
- **Base facultative** : sans PostgreSQL configuré, `load_database` est ignorée avec un
  avertissement, pour que le pipeline tourne sur une machine vierge.
- **`src/train.py` supprimé** : il entraînait une régression qui n'a pas sa place au
  TP 13 ; le split vit dans l'export, l'entraînement dans `nutriscope.classification`.
- **Notebook `ml_nutriscore.ipynb`** : validation croisée sur le train seul, test regardé
  une seule fois en fin de notebook, préparation commune (`classification.preparation`).

### Dette

- Durées réelles du pipeline à mesurer (échantillon et extrait complet) et à reporter
  dans `docs/data/pipeline.md`.
- TP 14 : fuite volontaire et importances par permutation (étape 4), trois erreurs
  analysées (étape 5) restent à faire.
- TP 15 : analyse des confusions par rayon et cinq produits diagnostiqués, ADR
  (`docs/decisions/`) et note `docs/ml/limites_nutriscore.md` restent à faire.

### Portage depuis la proposition alternative du TP 13

La branche `origin/tp13-alternative-proposition` (Sébastien, 14/10) avait mesuré sur
l'extrait complet ce que notre pipeline ne gérait pas : la mémoire. Repris dans
`src/nutriscope/pipeline.py` :

- `load` lit la source avec DuckDB, en flux et tout en texte, avec les guillemets
  désactivés pour l'export tabulé (son banc d'essai : 23 s, aucune ligne perdue, au lieu
  d'une saturation de la RAM avec pandas) ;
- `clean_data` nettoie par lots répartis par code-barres au-delà d'un million de lignes
  (son banc d'essai : 2,5 Go de pic au lieu de 14,1 Go, même résultat). Le rapport de
  nettoyage a été découpé (`summarize_before`, `merge_summaries`, `merge_reports`) pour
  s'additionner d'un lot à l'autre ;
- empreinte rapide des sources de plus de 1 Go, et versions des bibliothèques dans le
  manifeste.

Non repris : la structure de son package, ses noms en français, son split en SQL
(équivalent au nôtre). Détail et justification : `docs/data/pipeline.md`, section 2.

### Un dossier de sorties par source

Le 23/10, l'export figé de l'échantillon a bloqué celui de l'extrait complet le même jour
(`FileExistsError`), et les sorties intermédiaires de l'un écrasaient celles de l'autre.
Décision : chaque source écrit dans `data/<source>/`, nommé d'après le fichier source
(`--name` pour le forcer) ; le journal des durées reste commun et indique la source.
`purge` ne vide que la source courante, `purge -a` toutes les sources (et les sorties de
l'ancienne organisation, directement dans `data/`).
