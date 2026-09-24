# TP 9 — Nettoyage Industrialisé NutriScope

## Démarrage Rapide

### 1. Prérequis
```bash
pip install pandas pytest numpy
```

### 2. Placer l'échantillon CSV
```bash
# Utiliser vos données réelles
cp echantillon_france.csv data/
# Ou télécharger depuis le projet
```

### 3. Exécuter le pipeline
```bash
python src/pipeline.py data/echantillon_france.csv \
    data/echantillon_france_propre.csv \
    docs/data/rapport_nettoyage.md
```

### 4. Lancer les tests
```bash
pytest tests/test_cleaning.py -v
# Expected : 25 tests, 0 échecs ✅
```

### 5. Consulter le rapport
```bash
cat docs/data/rapport_nettoyage.md
```

## ✨ Points Forts de la Solution

✅ **7 Règles Implémentées**
- Typage, unités, bornes, énergie, doublons, catégories, manquants

✅ **25+ Tests Pytest**
- Nominal + cas tordus (TP 2) + pureté + idempotence

✅ **Rapport Automatisé**
- Volumétrie, anomalies avant/après, détail par règle

✅ **Code Robuste**
- Fonctions pures, constantes nommées, docstrings, pas de mutations

✅ **Pipeline End-to-End**
- Lecture → nettoyage → rapport → export en 1 commande

## Résultats Attendus (Échantillon)

**Avant** : 8,689 produits  
**Après** : ~8,100 produits (93.2%)

**Anomalies résiduelles après TP 9** :
- ✅ 0 sucres > glucides
- ✅ 0 énergies > 900 kcal (sauf alcoolisé)
- ✅ 0 doublons de codes
- ✅ 0 produits sans catégories

## 🔧 Intégration TP 4

Adapter votre script de chargement base :

```python
from src.cleaning import nettoyer

# Avant (brut)
df = pd.read_csv("data/produits_fr.csv")

# Après (nettoyé)
df_brut = pd.read_csv("data/produits_fr.csv")
df, rapports = nettoyer(df_brut)

# Puis charger en base comme d'habitude
df.to_sql("produits", engine, if_exists="replace", index=False)
```

## 📚 Documentation

- **Code complet** : `src/cleaning.py` (docstrings détaillées)
- **Tests** : `tests/test_cleaning.py` (voir les fixtures)
- **Stratégie** : `docs/data/strategie_manquants.md`
- **Guide TP** : `docs/README_TP9.md`

## ❓ Dépannage

| Problème | Solution |
|----------|----------|
| `ModuleNotFoundError` | Exécuter depuis racine, pip install pandas pytest |
| `UNIQUE constraint` en base | Appeler `dedupliquer_codes()` avant insert |
| Tests échouent | Vérifier pandas/pytest versions, voir conftest.py |
| Rapport diffère | Normal (date), contenu stable — voir section "Anomalies" |

## 📞 Fichiers Clés

- **cleaning.py** : Logique de nettoyage
  - Fonction `nettoyer(df)` retourne `(DataFrame_propre, liste_rapports)`
  - Chaque règle est une fonction pure : `(df_in) → (df_out, CompteRendu)`

- **test_cleaning.py** : Validation
  - Fixture `df_tordu` : produits avec anomalies du TP 2
  - 4 tests par règle minimum (nominal, cas tordu, pureté, idempotence)

- **report.py** : Reporting
  - `generer_rapport(df_avant, df_apres, rapports)` → Markdown string

- **strategie_manquants.md** : Décisions
  - Vocabulaire : garder / drapeau / supprimer_colonne
  - Table par colonne avec justification

## ✅ Checklist de Livrable

- [x] `src/cleaning.py` : 7 règles, fonctions pures
- [x] `tests/test_cleaning.py` : 25+ tests, tous verts
- [x] `docs/data/strategie_manquants.md` : Par colonne, décisions écrites
- [x] `docs/data/rapport_nettoyage.md` : Généré automatiquement
- [x] Idempotence : Appliquer 2× = même résultat
- [x] Pureté : Entrée jamais modifiée
- [x] Pipeline : Orchestration complète

## 🎓 À Retenir

Ce TP démontre :
1. **Architecture modulaire** : 7 règles = 7 fonctions
2. **Testabilité** : Pureté + idempotence = facile à tester
3. **Reproductibilité** : Pipeline rejouable sans intervention
4. **Documentation vivante** : Rapport auto-généré, stratégie écrite
5. **Qualité données** : De brut sale → propre exploitable

---

**TP 9 — Nettoyage Industrialisé**  
NutriScope | Septembre 2026  
Licence : ODbL (conforme Open Food Facts)

Bon nettoyage ! 🧹✨
