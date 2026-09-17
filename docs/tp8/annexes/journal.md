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
