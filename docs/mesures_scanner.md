# Mesures du scanner d'étiquettes

Toutes les mesures : `python scan_tools/measure_scanner.py --version <nom>` depuis la racine du dépôt, sur les
22 photos du lot (`results/history.csv`, détail dans `results/<version>.csv`). Réglages par variables
d'environnement, sans toucher au code :

| Version | Réglage | Commande |
|---|---|---|
| `palier1` | une lecture, sans relance (référence) | `SCANNER_RETRIES=0 python scan_tools/measure_scanner.py --version palier1` |
| `validation` | une lecture, contrôles + 1 relance | `python scan_tools/measure_scanner.py --version validation` |
| `vote3` | trois lectures, vote champ par champ | `SCANNER_READS=3 python scan_tools/measure_scanner.py --version vote3` |
| `deux_modeles` | deux modèles, vote | `SCANNER_READS=3 SCANNER_MODELS=qwen3-vl:4b-instruct,qwen2.5vl:7b python scan_tools/measure_scanner.py --version deux_modeles` |

Sous PowerShell : `$env:SCANNER_READS=3; python scan_tools/measure_scanner.py --version vote3`.

Le modèle est servi par **llama.cpp** (service `llm`, avec `compose.gpu.yml` pour le GPU) : un seul modèle,
celui de `LLM_MODEL`. Pourquoi pas Ollama : [ADR 0002](adr/0002-llama-cpp-au-lieu-d-ollama.md). La version
`deux_modeles` demande donc un second serveur llama.cpp ; les noms de modèles ci-dessus sont ceux d'Ollama.

Bonus face avant : `python scan_tools/measure_scanner.py --version face_avant --with-face` envoie l'étiquette
**et** la face avant dans la même lecture (`scan_label(etiquette, face=face_avant)`), pour lire le nom, la
marque et le code-barres ; à comparer à `llamacpp_4b` (noms trouvés, `verifie`, latence).

## Tableau des versions

Repris de `python scan_tools/measure_scanner.py --history` (à remplir après les passages) :

| Version | Justesse | Inventées | Manquées | Statuts (vérifié / non vérifié / illisible) | Latence par photo | Tokens par photo | Coût par photo (API) |
|---|---|---|---|---|---|---|---|
| palier1 (Ollama, `qwen3-vl:8b-instruct`) | 100 % | 0 | 0 | 2 / 20 / 0 | 54,8 s (max 79,2 s) | 1 455 / 161 | 0 (local) |
| llamacpp_4b (llama.cpp, Qwen3-VL-4B Q4_K_M) | 100 % | 0 | 0 | 2 / 20 / 0 | 3,6 s (max 8,8 s) | 1 450 / 156 | 0 (local) |
| face_avant (+ face avant, `--with-face`) | 95 % | 0 | 9 | 2 / 20 / 0 | 4,9 s (max 10,1 s) | 2 543 / 160 | 0 (local) |
| face_valeurs (+ consigne corrigée, fiches départagées par les valeurs, **8 fiches fausses sur 12**) | 99 % | 0 | 0 | 12 / 10 / 0 | 7,8 s (max 14,7 s) | 2 597 / 162 | 0 (local) |
| face_strict (+ départage seulement si toutes les fiches sont rendues ; 2 fiches justes, 0 fausse) | 99 % | 0 | 0 | 2 / 20 / 0 | 5,5 s | ~2 600 / ~160 | 0 (local) |
| validation | | | | | | | |
| vote3 | | | | | | | |
| deux_modeles | | | | | | | |

Le nom n'est juste sur aucune photo (0 / 22) : c'est attendu. La photo d'étiquette ne montre que le tableau
nutritionnel, sans nom ni marque ; seules les photos 16 et 21 montrent un code-barres, d'où les deux
`verifie`. Pour identifier les autres produits, il faut envoyer aussi la face avant (bonus du brief, `--with-face`).

Avec la face avant (`face_valeurs`) : 19 noms justes sur 22 et 12 produits `verifie`, mais le contrôle des
fiches (`face_valeurs2`, colonne `sheet_correct`) a montré que **8 des 12 fiches étaient fausses** : un autre
format ou un autre pays du même produit, aux mêmes valeurs. Le scanner départageait par les valeurs parmi les
5 fiches rendues par `chercher_produit`, alors qu'un nom comme « PRINCE » en vise des dizaines. Correction
(`scanner/routing.py`) : le départage par la marque ou par les valeurs n'est accepté que si la recherche a
rendu toutes les fiches trouvées ; sinon `non_verifie`, la fiche aux mêmes valeurs citée dans l'alerte.
Sans code-barres lisible, un produit n'est donc presque jamais identifié avec certitude : mieux vaut un vrai
« non vérifié » qu'un faux « vérifié ». Coût de la face avant : ~4 s de plus par photo.

## Version retenue

**`llamacpp_4b`** : photo d'étiquette seule (sans `--with-face`), Qwen3-VL-4B Q4_K_M servi par llama.cpp sur le
GPU, une lecture, contrôles et relance, règle stricte d'identification (`face_strict`).
Elle apporte 100 % de nutriments justes, 0 valeur inventée, et 2 produits `verifie` (par code-barres), tous sur la
bonne fiche : aucune fausse vérification.
Elle coûte 3,6 s par photo (8,8 s au pire), ~1 450 tokens en entrée et ~156 en sortie, 0 € (modèle local).

Non retenu : la face avant (`--with-face`). Elle lit 19 noms sur 22, mais n'ajoute aucune vérification sûre (le
catalogue a plusieurs fiches aux mêmes valeurs pour un même produit), fait perdre une valeur (fibres du Gazpacho)
et ajoute ~2 s par photo. L'identification sûre passe par le code-barres, que l'application fera scanner.

Photos : contributeurs Open Food Facts, CC-BY-SA 3.0 (`data/sources_photos.csv`). Données : ODbL.
