# Compte-Rendu d'Entretien - Direction NutriScope

**Objet** : Validation des besoins métiers, priorités fonctionnelles, risques et orientations stratégiques  
**Personas Validés** : Sophie Martin (primary), Marc Leboucher, Nicolas Lapoutre, Claire Bernard, Jean Moreau

---

## 1. Vision du Projet

La direction souhaite développer une application :
- **Intelligente** : Powered by IA (scan, recommandations, assistant)
- **Simple à utiliser** : Temps décision < 30 sec en magasin
- **Personnalisée** : Adaptation aux profils individuels
- **Fiable** : Donnée qualifiée, explicable
- **Accessible** : Grand public, langage clair

**Positionnement** : Outil informatif (pas médical).

---

## 2. Public Cible

### Priorité Confirmée
- **Cœur de Cible** : Familles pressées (Sophie Martin) ✅
- **Focus** : Parents gérant courses du foyer
- **Sans distinction** : Homme / Femme (besoin universel)

### Personas Secondaires (V2+)
Diabétiques, allergiques, sportifs, professionnels santé — moins prioritaires pour MVP.

---

## 3. Différenciation vs Concurrents

Direction demande :
1. **Simplicité** vs Yuka
2. **Meilleure personnalisation** vs Open Food Facts
3. **Aide contextualisée** vs solutions génériques
4. **Assistant conversationnel** (unique) ✅

---

## 4. Fonctionnalités MVP (Essentielles)

### Recherche & Identification
- Scan code-barres ✅
- Recherche manuelle ✅

### Consultation Rapide
- Fiche produit synthétique ✅
- Informations simples ✅
- Présentation non-expert ✅

### Comparaison
- Comparaison multi-produits ✅

### Recommandation
- **Assistant conversationnel** ✅

### Améliorations (Nice-to-have)
- Historique scans
- Favoris
- Recommandations personnalisées

---

## 5. Personnalisation

**Axe majeur du projet** ✅

Fonctionnalités :
- Profil utilisateur
- Historique recherches
- Produits favoris
- Recommandations adaptées

### Point Vigilance DPO
Risque limitation sur :
- Collecte données personnelles
- Exploitation historique
- Pas revente inter-concurrents (anti-concurrence)

---

## 6. Modèle Économique

### Phase Initiale
Focus adoption avant monétisation.

### Évolution Envisagée
- Partenariats marques
- Mise en avant produits (avec risques éthiques identifiés)

### Alerte
**Conflit d'intérêt** à encadrer : financement par produits ≠ compromis indépendance recommandations.

---

## 7. Gestion des Recommandations

### STRICT : Pas Médical
- ❌ Pas de diagnostic
- ❌ Pas de prescription
- ❌ Pas de remplacement professionnel santé
- ✅ Aide à la décision, outil informatif

### Positionnement
- Pas de nouveau Nutri-Score propriétaire
- Respect du Nutri-Score officiel Santé Publique France

---

## 8. Risques Identifiés

### Risque Principal : Perte de Confiance
**Causes** :
- Recommandation erronée
- Information inexacte
- Données incomplètes
- **Erreur allergène CRITIQUE**
- Erreur profil diabétique

### Risque Réputation
**L'asset le plus important** = image de marque.

### Point IA
- Transparence obligatoire
- Explicabilité requise
- Éviter affirmations excessives

### Ton Éditorial
- ❌ Pas culpabilisant
- ❌ Pas moralisateur
- ✅ Pédagogique
- ✅ Bienveillant
- ✅ Factuel

---

## 9. KPI de Succès (Direction)

| Métrique | Cible |
|----------|-------|
| Adoption | 100 000 min (231k M6) |
| Activité MAU | 33 % d'actifs |
| Fidélisation | 40 % réutilisation |
| Note stores | ≥ 4,3/5 |

---

## 10. Conclusions

✅ **Vision commune établie** entre direction et équipe IA  
✅ **Personas validés**, Sophie Martin confirmée comme cœur de cible  
✅ **MVP clairement défini** : scan, fiche, substitution, assistant RAG  
✅ **Risques identifiés** : confiance, éthique, allergènes prioritaires  
✅ **Constraints DPO** : RGPD-first, pas revente nominative inter-concurrents  
✅ **Planning confirmé** : 3 mois pilot, 4 mois v1.0
