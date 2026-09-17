# Qualification des Données - NutriScope

## Contexte
NutriScope repose sur l'exploitation de données alimentaires pour accompagner le consommateur dans sa prise de décision lors de l'achat. Cette étude inventorie les sources de données, évalue leur pertinence et identifie les risques associés.

---

## 1. Inventaire des Sources de Données

### Source 1 : Open Food Facts
Base collaborative de millions de produits alimentaires.
- Données : Code-barres, nom, marque, catégories, Nutri-Score, valeurs nutritionnelles, ingrédients, allergènes, images
- Usage : Source principale pour identification et analyse des produits

### Source 2 : Étiquetage Industriel
Informations fournies par les fabricants.
- Données : Ingrédients, valeurs nutritionnelles, allergènes, labels, mentions réglementaires
- Usage : Source primaire alimentant indirectement Open Food Facts

### Source 3 : Utilisateur
Informations saisies ou générées lors de l'utilisation.
- Données : Produits scannés, préférences, allergies, questions posées
- Usage : Personnalisation des recommandations

### Source 4 : Historique des Scans
Journal des recherches effectuées.
- Données : Produit consulté, date, fréquence
- Usage : Amélioration de l'expérience utilisateur

### Source 5 : Référentiel Interne NutriScope
Base enrichie par l'application.
- Données : Produits comparables, scores calculés, recommandations, résultats IA
- Usage : Accélération des traitements et enrichissement fonctionnel

---

## 2. Qualification selon les 5 Portes

### Open Food Facts
| Porte | Verdict | Commentaire |
|-------|---------|-------------|
| Disponible ? | ✅ Oui | Base publique facilement accessible |
| Accessible ? | ✅ Oui | Export ou API disponibles |
| Qualité suffisante ? | ⚠️ Partiellement | Données manquantes et incohérences constatées |
| Légale ? | ✅ Oui | Données publiques |
| Utile ? | ✅ Oui | Source centrale du projet |

---

## 3. Principaux Risques Qualité Open Food Facts

### Risque n°1 : Données Manquantes
- energy_100g manquant
- sugars_100g manquant
- salt_100g manquant
- nutriscore_grade absent

**Impact** : Impossible de produire certaines analyses.  
**Mitigation** : Définir seuil minimal de complétude.

### Risque n°2 : Valeurs Incohérentes
- sugars_100g > 100
- salt_100g > 100
- energy_100g < 0 ou = 0

**Impact** : Résultats erronés.  
**Mitigation** : Filtrage et isolation des données aberrantes.

### Risque n°3 : Hétérogénéité des Données
Nomenclatures multiples pour même information (pays, tags, catégories).

**Impact** : Filtrage difficile, résultats incohérents.  
**Mitigation** : Normalisation et référentiels internes.

### Risque n°4 : Dépendance à Open Food Facts
Indisponibilité ou changement de structure.

**Impact** : Recommandations obsolètes, mauvaise qualité de service.  
**Mitigation** : Mise en cache locale, synchronisation régulière.

### Risque n°5 : Données Non Mises à Jour
Changements de formulation, modification d'ingrédients, évolution Nutri-Score.

**Impact** : Recommandations obsolètes.  
**Mitigation** : Rechargement périodique des données.

### Risque n°6 : Conformité RGPD
Données de santé (allergies, restrictions alimentaires) mal traitées.

**Impact** : Risques réglementaires, perte de confiance utilisateurs.  
**Mitigation** : Minimisation des données, consentement explicite, conservation encadrée.

---

## 4. Synthèse des Risques Identifiés

| Risque | Impact | Mesure Envisagée |
|--------|--------|-----------------|
| Données manquantes | Élevé | Filtrages des données manquantes |
| Valeurs incohérentes | Élevé | Contrôles qualité automatisés |
| Hétérogénéité des données | Moyen | Normalisation et référentiels internes |
| Dépendance OFF | Moyen | Mise en cache et diversification des sources |
| Données non mises à jour | Moyen | Synchronisation régulière |
| Conformité RGPD | Élevé | Consentement et minimisation des données |

---

## Conclusion

L'analyse met en évidence plusieurs difficultés liées à la qualité, la complétude et la disponibilité des données. Malgré ces défis, une approche fondée sur l'intelligence artificielle couplée à des contrôles qualité rigoureux permet de transformer les données nutritionnelles complexes en informations claires et directement utiles à la prise de décision.
