# Analyse des risques - Opportunités & Stratégies de Mitigation

## Objectif
Identifier les principaux risques susceptibles d'affecter la qualité des données, la pertinence des résultats et le bon fonctionnement de NutriScope, avec évaluation probabilité × impact et mesures de mitigation.

---

## Risques Identifiés

### R1 : Données nutritionnelles incohérentes
**Description** : Valeurs aberrantes (sucres/sel > 100g, énergie négative, manquants)  
**Probabilité** : Élevée | **Impact** : Élevé | **Niveau** : 🔴 Critique

**Mitigation** : Contrôles qualité automatiques, filtrage des valeurs aberrantes, exclusion des données incohérentes des modèles.

---

### R2 : Produits incomplets
**Description** : Ingrédients, valeurs nutritionnelles ou Nutri-Score manquants  
**Probabilité** : Élevée | **Impact** : Moyen | **Niveau** : 🟠 Important

**Mitigation** : Définition d'un seuil minimal de complétude, affichage d'indice de fiabilité, exclusion des produits trop incomplets.

---

### R3 : Hétérogénéité des données
**Description** : Nomenclatures multiples pour même information (pays, tags, catégories)  
**Probabilité** : Élevée | **Impact** : Moyen | **Niveau** : 🟠 Important

**Mitigation** : Normalisation automatique lors de l'import, création de référentiels internes, uniformisation avant traitement.

---

### R4 : Dépendance à Open Food Facts
**Description** : Indisponibilité ou changement de structure du service tiers  
**Probabilité** : Moyenne | **Impact** : Élevé | **Niveau** : 🟠 Important

**Mitigation** : Mise en cache locale, sauvegarde régulière, historisation, préparation à l'intégration d'autres sources.

---

### R5 : Non-conformité RGPD
**Description** : Données sensibles (préférences alimentaires, allergies) mal traitées  
**Probabilité** : Faible | **Impact** : Élevé | **Niveau** : 🟠 Important

**Mitigation** : Minimisation des données, consentement explicite, suppression garantie, politique transparente.

---

### R6 : Recommandations peu pertinentes
**Description** : Qualité insuffisante des suggestions proposées à l'utilisateur  
**Probabilité** : Moyenne | **Impact** : Fort | **Niveau** : 🟠 Important

**Mitigation** : Tests utilisateurs réguliers, ajustement des règles métier, amélioration progressive, collecte de feedback.

---

## Matrice Synthétique

| ID | Risque | Prob | Impact | Niveau | Solution Retenue |
|----|---------|------|--------|--------|------------------|
| R1 | Incohérences nutritionnelles | Élev | Élev | 🔴 Crit | Exclusion des données aberrantes des modèles |
| R2 | Produits incomplets | Élev | Moy | 🟠 Imp | Analyse partielle + indice de confiance |
| R3 | Hétérogénéité data | Élev | Moy | 🟠 Imp | Normalisation automatique |
| R4 | Dépendance OFF | Moy | Élev | 🟠 Imp | Cache local + multi-sources progressif |
| R5 | Non-conformité RGPD | Faib | Élev | 🟠 Imp | Minimisation + consentement explicite |
| R6 | Pertinence faible | Moy | Fort | 🟠 Imp | Règles métier d'abord, IA progressive |

---

## Principes Directeurs

| Principe | Application NutriScope |
|-----------|------------------------|
| Qualité avant quantité | Exclusion des données incohérentes des entraînements critiques |
| Transparence maximale | Affichage obligatoire d'indice de confiance |
| Normalisation systématique | Harmonisation avant exploitation |
| Réduction dépendances | Cache local + architecture ouverte à autres sources |
| IA progressive & maîtrisée | Priorité aux règles explicables avant modèles complexes |
| Amélioration continue | Réévaluation régulière des modèles et recommandations |

---

## Conclusion

L'analyse identifie un risque critique et plusieurs risques importants principalement liés à la qualité, la complétude et la disponibilité des données. Les mesures de mitigation identifiées permettent de réduire significativement leur impact en s'appuyant sur des mécanismes de contrôle qualité, normalisation, sécurisation des données et amélioration continue.
