# Mesures du scanner d'étiquettes

Toutes les mesures : `python tools/measure_scanner.py --version <nom>` depuis la racine du dépôt, sur les
22 photos du lot (`results/history.csv`, détail dans `results/<version>.csv`). Réglages par variables
d'environnement, sans toucher au code :

| Version | Réglage | Commande |
|---|---|---|
| `palier1` | une lecture, sans relance (référence) | `SCANNER_RETRIES=0 python tools/measure_scanner.py --version palier1` |
| `validation` | une lecture, contrôles + 1 relance | `python tools/measure_scanner.py --version validation` |
| `vote3` | trois lectures, vote champ par champ | `SCANNER_READS=3 python tools/measure_scanner.py --version vote3` |
| `deux_modeles` | deux modèles, vote | `SCANNER_READS=3 SCANNER_MODELS=qwen3-vl:8b-instruct,qwen2.5vl:7b python tools/measure_scanner.py --version deux_modeles` |

Sous PowerShell : `$env:SCANNER_READS=3; python tools/measure_scanner.py --version vote3`.

## Tableau des versions

Repris de `python tools/measure_scanner.py --history` (à remplir après les passages) :

| Version | Justesse | Inventées | Manquées | Statuts (vérifié / non vérifié / illisible) | Latence par photo | Tokens par photo | Coût par photo (API) |
|---|---|---|---|---|---|---|---|
| palier1 | | | | | | | |
| validation | | | | | | | |
| vote3 | | | | | | | |
| deux_modeles | | | | | | | |

## Version retenue

À compléter en trois lignes : la version gardée, ce qu'elle apporte (justesse, valeurs inventées), et ce
qu'elle coûte (latence, tokens).

Photos : contributeurs Open Food Facts, CC-BY-SA 3.0 (`data/sources_photos.csv`). Données : ODbL.
