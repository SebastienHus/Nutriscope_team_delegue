# Définition du Périmètre NutriScope (TP2)

## Contexte

Le projet NutriScope utilise les données OpenFoodFacts pour construire un outil d'aide à l'analyse et comparaison de produits alimentaires. Cette définition du périmètre garantit la faisabilité des développements et la qualité des recommandations.

---

## 1. Profiling du Jeu de Données

### Taille et volumétrie
- **Nombre total de produits France** : ~1 136 108
- **Nombre de colonnes exploitées** : 20-30 (selon traitement)
- **Taux de doublons EAN** : ~0,002 %
- **Date d'export** : Septembre 2026

---

## 2. Qualité des Données

### Taux de Remplissage

| Colonne | Taux |
|---------|------|
| product_name | ~99 % |
| brands | ~85 % |
| nutriscore_grade | 44,91 % |
| energy_100g | 76,49 % |
| sugars_100g | 75,88 % |
| salt_100g | 71,27 % |

### Cardinalités

| Colonne | Distinct |
|---------|----------|
| code (EAN) | 1 136 083 |
| product_name | 736 670 |
| brands | 113 242 |
| categories_tags | Variables |
| nutriscore_grade | 8 (A-E + NA) |

---

## 3. Valeurs Incohérentes

| Contrôle | Nombre de cas |
|-----------|----|
| sugars_100g > 100 | 49 |
| salt_100g > 100 | 48 |
| energy_100g < 0 | 8 |
| energy_100g = 0 | 17 489 |

**Décision** : Exclusion des produits avec valeurs aberrantes des modèles prédictifs.

---

## 4. Critères de Sélection

Un produit est conservé si :
- ✅ Possède un nom valide
- ✅ Possède un code-barres unique
- ✅ Est commercialisé en France
- ✅ Appartient à une catégorie retenue
- ✅ Respecte un seuil minimal de complétude nutritionnelle

### Seuils Retenus
- **Taux de complétude minimal** : 50 % sur nutriments clés (energy_100g, sugars_100g, salt_100g)
- **Nutri-Score obligatoire** : Non (prédit par IA si absent)
- **Image obligatoire** : Non (optionnelle pour affichage)

---

## 5. Catégories Couvertes (Mois 1-2)

Restrictions initiales à 5-8 rayons majeurs :
1. Petit déjeuner (céréales, lait, yaourt)
2. Boissons (jus, sodas, eau)
3. Snacks (biscuits, chips, chocolat)
4. Produits laitiers (fromage, crème)
5. Fruits & Légumes transformés (conserves, surgelés)
6. Viandes & Substituts (charcuterie, alternatives protéine)
7. Plats préparés (surgelés, boîtes)
8. Condiments & Huiles

**Justification** : Garantir pertinence et précision du moteur de substitution.

---

## 6. Hors Périmètre

- ❌ Produits non alimentaires
- ❌ Produits sans identification valide
- ❌ Données nutritionnelles < 50 % complétude
- ❌ Catégories non retenues
- ❌ Doublons d'EAN

---

## 7. Risques Mitigés

| Risque | Mitigation |
|--------|------------|
| Données manquantes | Filtrage sur seuil complétude |
| Valeurs incohérentes | Exclusion automatique des aberrantes |
| Doublons | Déduplication sur EAN |
| Catégories aberrantes | Whitelist de catégories validées |
| Produits incomplets | Affichage indice de confiance |

---

## Conclusion

Le périmètre retenu concentre les efforts sur les catégories les plus pertinentes tout en garantissant une qualité minimale (non "mauvaise qualité") des données exploitées. Cette approche permet de :
- Prioriser les rayons à fort potentiel commercial
- Assurer la qualité des recommandations
- Faciliter la validation du modèle
- Préparer l'extension future à d'autres catégories
