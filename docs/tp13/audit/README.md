# Audit et kit TP 13 — Pipeline NutriScope

> Copie dans le dépôt (branche `tp13-alternative-proposition`) du kit fourni le 14/10.
> Ce qui a été réalisé à partir de cet audit : `docs/tp13/JOURNAL_ACTIONS.md`.

> **Version du 14/10/2026, après le banc d'essai « gros fichier ».** Les documents tiennent compte des mesures
> réelles sur le fichier Open Food Facts complet (4 535 553 produits). Le détail de ces mesures est dans le
> fichier `docs/tp13/banc_essai/JOURNAL_DEMARCHE.md`. Les passages mis à jour sont signalés par
> **[MAJ 14/10]**.

Ce zip contient des documents et des fichiers **proposés**. Rien n'a été modifié dans ton dépôt :
tu relis, tu choisis, tu copies toi-même ce que tu gardes (c'est aussi comme ça qu'on apprend).

## Contenu

| Fichier | À quoi il sert | Le lire quand |
|---|---|---|
| `01_plan_tp13.md` | Le plan de la journée, étape par étape, avec **à quoi sert chaque étape** | d'abord |
| `02_conception_module_nutriscope.md` | Comment construire le module `nutriscope/` (structure, fonctions, formats, split) | avant de coder |
| `03_problemes_identifies.md` | Les problèmes trouvés dans le projet (toutes branches) et ceux à anticiper | avant de coder, puis en cas de panne |
| `../conteneurisation/README.md` | Docker / Compose expliqués (préparé, non activé) | plus tard |
| `05_recommandations.md` | Conseils pour apprenants (Git, tests, équipe, test machine vierge) | quand tu veux |
| `../../journal_tp13.md` | Journal **dédié au TP 13** (l'ancien `docs/journal.md` n'est pas touché) | à remplir pendant la journée |
| `../conteneurisation/` | Brouillons `Dockerfile`, `compose.yml`, `.dockerignore`, `.gitattributes` | phase conteneur |

## Limites à connaître (honnêteté)

- Je n'ai pas pu **exécuter** ton code : l'installation des dépendances Python était bloquée dans mon environnement.
  Mon analyse vient de la lecture du code, des tests, de l'historique Git et des énoncés.
  Tout ce qui est marqué *« à vérifier »* est une hypothèse à confirmer en lançant la commande.
- Les fichiers de `propose/` n'ont pas été testés (pas de Docker disponible ici). Traite-les comme un brouillon relu, pas comme une solution.
- L'énoncé du formateur (`tp-13-pipeline-bout-en-bout.md`) fait foi. Le guide `TP13_Guide_Comprehension` diverge sur deux points (voir `03_problemes_identifies.md`, section D (divergences)).

Données : © Open Food Facts contributors — ODbL.

## [MAJ 14/10] Ce qui a changé depuis la première version

| Sujet | Avant | Maintenant (mesuré) |
|---|---|---|
| Étape `charger` | lecture pandas (`reader.read_products`) | **DuckDB** : 12,1 Go → Parquet 382 Mo en 23 s, 0 ligne perdue |
| Étape `nettoyer` | `clean()` en un bloc | `clean()` inchangé, **en lots** par hachage du code (2,5 Go de pic au lieu de 14,1 Go, même résultat) |
| Périmètre géographique | « commercialisé en France » (TP 2) | **tous les pays** (décision d'équipe du 14/10) |
| Python | 3.12 recommandé | 3.12 installé et validé (`py install 3.12`), venv hors du dossier projet |
| Volumes de référence | inconnus | brut 4 535 553 → nettoyé 996 637 |
| Points ouverts | — | `filter_codes` (446 494 lignes écartées), écart France vs TP 2 ; doublons 60/50 **résolu** (script 05) |
