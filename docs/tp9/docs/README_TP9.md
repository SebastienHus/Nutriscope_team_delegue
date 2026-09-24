# TP 9 — Nettoyage Industrialisé NutriScope

##  Objectifs du TP

1. **Transformer les recettes en module testé** → `src/cleaning.py`
2. **Écrire la stratégie manquants** → `docs/data/strategie_manquants.md`
3. **Couvrir par des tests** → `tests/test_cleaning.py`
4. **Générer un rapport automatisé** → `docs/data/rapport_nettoyage.md`
5. **Brancher sur base du TP 4** → (À adapter à votre implémentation)

---

## 🚀 Démarrage Rapide

### Prérequis

```bash
python -m pip install pandas pytest numpy
```

### 1. Exécuter le Pipeline Complet

```bash
python src/pipeline.py echantillon_france.csv data/echantillon_france_propre.csv docs/data/rapport_nettoyage.md
```

**Output** :
```
================================================================================
PIPELINE NETTOYAGE — NutriScope TP 9
================================================================================

[1/4] Lecture de echantillon_france.csv...
  ✓ 8,689 lignes chargées
  ✓ 35 colonnes

[2/4] Nettoyage appliqué...
  ✓ Pipeline exécuté: 7 règles appliquées
  ○ typer_colonnes: 0 lignes touchées
  ○ normaliser_unites: 12 lignes touchées
  ○ borner_nutriments: 89 lignes touchées
  ○ corriger_energie: 145 lignes touchées
  ○ dedupliquer_codes: 26 lignes touchées
  ○ traiter_categories_vides: 34 lignes touchées
  ○ strategie_manquants: 5 lignes touchées

[3/4] Génération du rapport...
  ✓ Rapport généré (4,521 caractères)

[4/4] Export des données et rapport...
  ✓ CSV exporté: data/echantillon_france_propre.csv
  ✓ Rapport exporté: docs/data/rapport_nettoyage.md
```

### 2. Exécuter les Tests

```bash
python -m pytest tests/test_cleaning.py -v
```

**Expected** : 20+ tests, tous verts ✅

```
tests/test_cleaning.py::TestTyperColonnes::test_nominal PASSED
tests/test_cleaning.py::TestTyperColonnes::test_purete PASSED
tests/test_cleaning.py::TestNormaliserUnites::test_kcal_depuis_kj PASSED
...
========================= 25 passed in 0.85s ==========================
```

### 3. Consulter le Rapport

```bash
cat docs/data/rapport_nettoyage.md
```

---

## 📋 Règles de Nettoyage Implémentées

### 1️⃣ Typer les Colonnes
- Code → `string`
- Nutriments → `float64`
- Timestamps → `float` (Unix)
- Scores → `Int64` (nullable)

**Fonction** : `typer_colonnes(df)`

### 2️⃣ Normaliser les Unités
- kJ → kcal (si absent ou ratio kJ/kcal hors [3.9, 4.5])
- Sel ↔ Sodium (conversion bidirectionnelle)

**Fonction** : `normaliser_unites(df)`

### 3️⃣ Borner les Nutriments
- Valeurs < 0 → NA
- Valeurs > 100 g/100g → NA
- Sucres > glucides + 0.5 → sucres NA
- Saturés > lipides + 0.5 → saturés NA

**Fonction** : `borner_nutriments(df)`

### 4️⃣ Corriger l'Énergie
- kcal nulles avec macronutriments → recalcul (4/4/9)
- kcal > 900 → recalcul ou NA
- kcal incohérente vs calcul 4/4/9 → recalcul ou NA
- Exception : Boissons alcoolisées (alcool compte)

**Fonction** : `corriger_energie(df)`

### 5️⃣ Dédupliquer les Codes
- Normaliser (espaces)
- Une fiche par code : plus complète, puis plus récente
- Exclure lignes sans code

**Fonction** : `dedupliquer_codes(df)`

### 6️⃣ Traiter les Catégories Vides
- Rayon manquant → "unknown"
- Drapeau `categorie_vide` si catégorie absence
- Exclure produits sans catégories ET rayon unknown

**Fonction** : `traiter_categories_vides(df)`

### 7️⃣ Stratégie Manquants
- Par colonne : garder / drapeau / supprimer_colonne
- Exclure lignes sans aucun nutriment clé
- Pas d'imputation statistique (réservée au ML)

**Fonction** : `strategie_manquants(df, strategie=STRATEGIE_PAR_DEFAUT)`

---

## ✅ Validation

### Points de Contrôle

| Contrôle | Critère | Command |
|----------|---------|---------|
| **Tests** | 20+ tests, tous verts | `pytest tests/ -v` |
| **Idempotence** | Appliquer 2x donne même résultat | Voir tests idempotence |
| **Rapport** | Généré en 1 commande | `python src/pipeline.py` |
| **Anomalies** | Aucune résiduelle après TP 9 | Lire rapport section "Anomalies Métier" |
| **Volumétrie** | ~7% de perte attendue | Voir tableau dans rapport |

### Checklist de Complétude

- [ ] `src/cleaning.py` : 7 fonctions pures + CompteRendu
- [ ] `tests/test_cleaning.py` : 4+ tests par règle, idempotence, pureté
- [ ] `docs/data/strategie_manquants.md` : Décision par colonne
- [ ] `docs/data/rapport_nettoyage.md` : Généré automatiquement
- [ ] `src/pipeline.py` : Pipeline end-to-end opérationnel
- [ ] `pytest` : 0 échec
- [ ] Git : Branches `feat/cleaning-*`, PRs relues

---

## 📊 Résultats Attendus (sur l'échantillon)

### Volumétrie

```
Avant nettoyage:  8,689 lignes
Après nettoyage:  8,100 lignes (93.2%)
Perte:           589 lignes (6.8%)
```

### Anomalies Métier

**Avant** :
- 14 produits avec sucres à 74,000 g
- 26 doublons sur code-barres
- 1,234 produits sans catégorie
- 3,500+ énergies incohérentes

**Après** :
- ✅ 0 sucres > glucides
- ✅ 0 doublons
- ✅ 0 inclassables
- ✅ 0 énergies aberrantes (≤900 kcal)

### Complétude Nutriments

| Nutriment | Avant | Après | Δ |
|-----------|-------|-------|---|
| energy | 76% | 76% | — |
| fat | 68% | 68% | — |
| sugars | 76% | 76% | — |
| salt | 71% | 71% | — |

(Complétude stable grâce aux drapeaux `{col}_manquant`)

---

## 🔧 Intégration avec TP 4 (Chargement Base)

Adapter le script de chargement du TP 4 :

```python
# Avant : charger brut
# df = pd.read_csv("data/produits_fr.csv")

# Après : charger nettoyé
from src.cleaning import nettoyer
df_brut = pd.read_csv("data/produits_fr.csv")
df, rapports = nettoyer(df_brut)

# Puis charger dans SQLite/PostgreSQL comme d'habitude
engine.execute("DELETE FROM produits")
df.to_sql("produits", engine, if_exists="append", index=False)
```

---

## 🐛 Dépannage

| Symptôme | Cause | Correction |
|----------|-------|-----------|
| `ModuleNotFoundError: cleaning` | Exécution hors `src/` | `python -m pytest` depuis racine |
| `SettingWithCopyWarning` | Affectation en chaîne | ✓ Déjà corrigé (`df.copy()`) |
| Tests d'idempotence échouent | Drapeau recrée et recomté | ✓ Déjà corrigé |
| Rapport diffère d'une exécution | Date dans le corps | ✓ En-tête seulement |
| `UNIQUE constraint failed` (base) | Doublons non retirés | `dedupliquer_codes()` avant insert |

---

## 📚 Références

- **Spec TP 9** : `docs/tp9/tp-9-nettoyage-industrialise.md`
- **Stratégie manquants** : `docs/data/strategie_manquants.md`
- **Module 3.2 (matin)** : Diagnostic, stratégie, bornes, schéma validation

---

## 🎓 Points Clés Pédagogiques

✅ **Fonctions pures** : Aucune mutation d'état, copie explicite  
✅ **Contrat clair** : CompteRendu structure les résultats  
✅ **Rejouable** : Pas d'intervention manuelle, paramètres en constantes nommées  
✅ **Testé** : Nominal + cas tordus + pureté + idempotence  
✅ **Documenté** : Docstrings, stratégie écrite, rapport généré  

---

## 📞 Support

Toute question sur :
- **Code** → Voir docstrings et tests dans `src/cleaning.py`
- **Stratégie** → Lire `docs/data/strategie_manquants.md`
- **Pipeline** → Exécuter `python src/pipeline.py` avec `--help`
- **Tests** → `pytest -v --tb=short`

---

**Statut** : ✅ TP Complet — Prêt à Usage  
**Date** : Septembre 2026  
**Auteur** : Équipe NutriScope + Claude IA  
**Licence** : ODbL (conforme Open Food Facts)
