# Stratégie de Traitement des Valeurs Manquantes

**TP 9 — Nettoyage Industrialisé**  
**Date** : Septembre 2026

---

## Vue d'Ensemble

Cette stratégie détermine comment traiter chaque colonne du catalogue NutriScope lorsque des valeurs sont manquantes. Les décisions sont basées sur :

1. **L'importance métier** : données critiques pour l'application
2. **Le taux de remplissage** : pertinence de l'imputation
3. **L'usage downstream** : besoins des règles et modèles

### Vocabulaire Fermé

- **garder** : Conserver tel quel (valeurs manquantes acceptées)
- **drapeau** : Ajouter colonne `{colonne}_manquant` (booléen)
- **supprimer_colonne** : Exclure la colonne du catalogue
- **constante** : Imputer par défaut (e.g., `constante:0`)

---

## Décisions par Colonne

### Identité & Catégorisation (CRITIQUES)

| Colonne | Décision | Taux Manquant | Justification |
|---------|----------|-------|----------------|
| **code** | garder | ~0% | Clé primaire, absence = exclusion |
| **product_name** | garder | ~1% | Affichage utilisateur obligatoire |
| **brands** | garder | ~15% | Informatif, pas obligatoire |
| **main_category** | garder | ~0% (rempli par pipeline) | Obligatoire (rayon) après traitement |
| **categories_tags** | garder | ~15% | Avec drapeau `categorie_vide` |

### Énergie & Macronutriments (CRITIQUES)

| Colonne | Décision | Taux Manquant | Justification |
|---------|----------|-------|----------------|
| **energy_100g** | garder | ~24% | Fondamental pour Nutri-Score |
| **energy-kcal_100g** | garder | ~45% | Dérivée de energy_100g si absent |
| **proteins_100g** | drapeau | ~30% | Important mais fréquemment absent |
| **carbohydrates_100g** | drapeau | ~30% | Idem |
| **fat_100g** | drapeau | ~32% | Idem |

### Micronutriments & Détails (SECONDAIRES)

| Colonne | Décision | Taux Manquant | Justification |
|---------|----------|-------|----------------|
| **sugars_100g** | drapeau | ~32% | Allègues santé fréquents |
| **saturated-fat_100g** | drapeau | ~40% | Moins rempli qu'il faudrait |
| **fiber_100g** | drapeau | ~50% | Rarement rempli, optionnel |
| **salt_100g** | drapeau | ~35% | Important, mais manquant courant |
| **sodium_100g** | drapeau | ~40% | Dérivable depuis sel en dernier recours |
| **fruits-vegetables-legumes_100g** | drapeau | ~97% | Très rarement rempli |

### Scores & Référentiels

| Colonne | Décision | Taux Manquant | Justification |
|---------|----------|-------|----------------|
| **nutriscore_grade** | garder | ~45% | Calculé par modèle IA si absent |
| **nutriscore_score** | garder | ~45% | Dérivé de la couleur après calcul |
| **nova_group** | garder | ~95% | Optionnel pour MVP |

### Metadata & Audit

| Colonne | Décision | Taux Manquant | Justification |
|---------|----------|-------|----------------|
| **completeness** | garder | 0% | Métrique de qualité propre |
| **created_t** | garder | <1% | Timestamps, généralement présents |
| **last_modified_t** | garder | <1% | Utilisé pour déduplication |
| **image_url** | garder | ~20% | Nice-to-have pour affichage |

---

## Règles Spéciales

### 1. Exclusion des Lignes Trop Incomplètes

**Règle** : Une ligne sans **aucun nutriment clé** (energy, proteins, carbs) est exclue du catalogue.

**Seuil** : 0 nutriments clés remplis = exclusion

**Justification** : Impossible de calculer un Nutri-Score ou faire des recommandations.

### 2. Drapeaux de Complétude

Pour chaque nutriment marqué "drapeau", ajouter une colonne booléenne :

```
{nutriment}_manquant = 1 si nutriment.isna() else 0
```

**Usage** : 
- Filtrage utilisateur (afficher l'indice de confiance)
- Audit de qualité catalog
- Apprentissage (marquer les données imputes post-ML)

### 3. Pas d'Imputation Statistique en Nettoyage

⚠️ Les imputations (médiane, KNN, forward fill) sont **reportées au pipeline ML** (après split train/test).

**Raison** : Éviter les fuites de données et les biais causés par l'imputation prématurée.

---

## Impact Volumétrique Attendu

| Étape | Lignes | Perte |
|-------|--------|-------|
| Brut | 8 689 | — |
| Après filtrage complétude | ~8 200 | −6% |
| Après déduplication | ~8 180 | −0.2% |
| Après catégorisation | ~8 100 | −1% |
| **Final** | **~8 100** | **−7%** |

---

## Mise en Œuvre

### Exécution

```python
from cleaning import strategie_manquants, STRATEGIE_PAR_DEFAUT

df_propre, rapport = strategie_manquants(df_brut, strategie=STRATEGIE_PAR_DEFAUT)
```

### Vérification

Après nettoyage :

```python
# Colonnes avec drapeau
flags = [c for c in df.columns if c.endswith("_manquant")]
for flag in flags:
    print(f"{flag}: {df[flag].sum()} lignes incomplètes")
```

---

## Révision

| Version | Date | Changements |
|---------|------|-------------|
| v1.0 | 24/09/2026 | Stratégie initiale, basée sur TP 3.2 |
| | | Drapeaux pour 8 nutriments secondaires |

---

## Questions Ouvertes

1. **Imputation post-split** : Quelle stratégie (médiane par rayon ? KNN ?)
2. **Étapes futures** : Intégration d'autres sources (labels, scan utilisateur)
3. **Audit** : Revoir les seuils après premières prédictions Nutri-Score
