# Traiter le fichier Open Food Facts complet sans saturer la RAM — journal de démarche

> Banc d'essai `nutriscope_bigdata_test`, équipe NutriScope (Team délégué), mardi 14/10/2026, préparation du TP 13.
> Objectif de ce document : pouvoir **refaire** la démarche de zéro, **comprendre** chaque résultat et **la présenter**
> (jury, formateur, autre équipe) sans avoir assisté à la séance. Tous les chiffres sont des mesures
> (`out/journal.jsonl`), pas des estimations, sauf mention contraire.
>
> Données : © Open Food Facts contributors — ODbL.

## Sommaire

1. Résumé en 30 secondes
2. Le problème de départ
3. Les notions à connaître
4. La méthode testée et pourquoi
5. Machine, versions, installation de zéro
6. Déroulé des mesures et résultats
7. Questions que nous nous sommes posées (et réponses)
8. Incidents techniques et corrections
9. Décisions prises
10. Conclusions pour le TP 13
11. Points ouverts et limites
12. Refaire la démonstration en 10 minutes

---

## 1. Résumé en 30 secondes

- Le CSV complet (12,1 Go, 211 colonnes, **4 535 553 produits**) saturait la RAM avec notre pipeline pandas.
- La cause n'était pas le nombre de colonnes mais la façon de lire : pandas reconstruit tout le tableau en mémoire,
  puis le nettoyage en fait plusieurs copies.
- **Chargement avec DuckDB** : CSV → Parquet en **23 s**, **0 ligne perdue**, fichier **32 fois plus petit** (382 Mo).
- **Nettoyage du TP 9, code inchangé** : 4 535 553 → **996 637** produits.
  - en un seul bloc : 2 min 27 s, **14,1 Go** de pic (passe sur 32 Go, de justesse) ;
  - en 8 lots : 3 min 08 s, **2,5 Go** de pic (5,5 fois moins), **même nombre de lignes**.
- Décision d'équipe : on garde **tous les pays**.
- Écart de doublons (60 bruts / 50 supprimés) **expliqué et vérifié** : 10 codes en double ne sont pas des codes officiels.

## 2. Le problème de départ

Le pipeline du TP 9 enchaîne :

```
CSV 12 Go ──► pandas read_csv par blocs (chunksize) ──► pd.concat (tout le tableau en RAM) ──► clean() pandas ──► CSV nettoyé
```

Sur le fichier complet, la machine (32 Go) saturait. Nous avions déjà réduit le périmètre de colonnes
(41 retenues dans `src/database_options.ini`), sans que cela suffise.

Contraintes de l'énoncé du TP 13 à respecter : « le TP 13 assemble, il ne refait pas » (on ne réécrit pas
le nettoyage), et la piste suggérée en dépannage : « lire par DuckDB, ou seulement les colonnes utiles ».

## 3. Les notions à connaître

| Notion | Explication simple | Où elle intervient ici |
|---|---|---|
| **Format en lignes (CSV)** | chaque ligne contient toutes les colonnes ; pour lire 41 colonnes il faut parcourir les 211 | la source |
| **Format en colonnes (Parquet)** | chaque colonne est stockée à part et compressée ; on ne lit que celles dont on a besoin | la sortie du chargement |
| **DuckDB** | moteur SQL qui tourne dans le processus Python, lit CSV/Parquet en flux et en parallèle | le chargement |
| **Lecture en flux** | on traite le fichier morceau par morceau sans jamais tout garder en mémoire | DuckDB, pas `pd.concat` |
| **Limite mémoire / débordement disque** | DuckDB respecte un plafond (`memory_limit`) et écrit sur disque (`temp_directory`) au-delà, au lieu de planter | `--memory-limit 12GB` |
| **Pic mémoire (RSS)** | mémoire maximale réellement occupée par le processus, mesurée toutes les 0,5 s | toutes les mesures |
| **Tri par code** | trier avant d'écrire pour que deux exécutions produisent le même fichier (idempotence, TP 13) | `ORDER BY code` |
| **Hachage** | fonction qui transforme un texte en nombre ; le même code donne toujours le même nombre | répartition en lots |
| **Lot (batch)** | une partie des lignes traitée séparément, l'une après l'autre | nettoyage par lots |

## 4. La méthode testée et pourquoi

```
                                   ┌──────────── étape 01 ────────────┐       ┌──────────── étape 04 ────────────┐
CSV OFF 12,1 Go, 211 colonnes ──►  │ DuckDB : lit en flux 41 colonnes │ ──►   │ pandas : cleaning.clean() du TP 9 │ ──► 996 637 produits
4 535 553 lignes                   │ tout en texte, trie par code     │       │ en 1 bloc, ou en N lots           │
                                   │ plafond 12 Go, débord. disque    │       │ (lot = hash(code) modulo N)       │
                                   └──► Parquet brut 382 Mo ──────────┘       └───────────────────────────────────┘
```

- **DuckDB pour la grosse réduction** : il ne matérialise que les 41 colonnes, ne garde pas tout en mémoire
  et respecte un plafond. C'est la partie que pandas faisait mal.
- **Tout en texte (`all_varchar`)** : le « brut figé » ne devine aucun type, le code-barres garde ses zéros
  de tête ; le typage reste la première règle du nettoyage (`type_columns`), donc rien n'est réécrit.
- **Guillemets désactivés (`quote=''`)** : le fichier OFF est tabulé sans guillemets, mais quelques fiches
  contiennent un `"` isolé (ex. `15" format`) qui casserait le découpage si on les interprétait.
- **pandas seulement après** : sur un Parquet déjà réduit, on peut mesurer jusqu'où le nettoyage existant tient.
- **Projet de test séparé** : on ne touche pas au dépôt ; les scripts 03 et 04 importent `reader.py` et
  `cleaning.py` en lecture seule.

## 5. Machine, versions, installation de zéro

| Élément | Valeur |
|---|---|
| OS / CPU / RAM | Windows 11 (10.0.22631) / 16 cœurs logiques / 31,7 Go (≈ 17-19 Go libres, applications fermées) |
| Python | 3.12.10 |
| duckdb / pyarrow / pandas / numpy / pandera / psutil | 1.5.6 / 26.0.0 / 2.3.3 / 2.5.4 / 0.34.1 / 7.2.2 |
| Source | `en.openfoodfacts.org.products.csv`, 12,1 Go (13,04 Go décimaux), 211 colonnes, tabulations |
| Disque | 748 Go libres |

Installation qui fonctionne (PowerShell, **VS Code fermé**) :

```powershell
cd C:\Users\Administrateur\Desktop\cours\exo\nutriscope_bigdata_test
py install 3.12                                          # si absent (py list)
py -3.12 -m venv $env:USERPROFILE\venvs\nutriscope312   # venv HORS du dossier projet
$PY = "$env:USERPROFILE\venvs\nutriscope312\Scripts\python.exe"
& $PY -c "import sys; print(sys.version); print(sys.executable)"   # 3.12 et ...\venvs\nutriscope312\...
& $PY -m pip install -r requirements.txt
& $PY -m pip install -r requirements-repo.txt
& $PY -m pytest -q                                       # attendu : 8 passed

# À redéfinir dans CHAQUE nouveau terminal
$PY   = "$env:USERPROFILE\venvs\nutriscope312\Scripts\python.exe"
$SRC  = "C:\Users\Administrateur\Desktop\cours\exo\Nutriscope_team_delegue\data\en.openfoodfacts.org.products.csv"
$REPO = "C:\Users\Administrateur\Desktop\cours\exo\Nutriscope_team_delegue"
```

## 6. Déroulé des mesures et résultats

### 6.1 Étape 00 — vérifier avant de lancer

`& $PY scripts/00_check_env.py --source $SRC` → 211 colonnes dans l'en-tête, les 41 retenues présentes,
versions et RAM relevées. **But :** ne pas découvrir un mauvais séparateur ou une dépendance manquante après 10 minutes de calcul.

### 6.2 Tranche de 500 Mo — DuckDB contre pandas (étapes 1a, 2a, 3)

| Mesure | DuckDB (01) | pandas, reader du dépôt (03) |
|---|---|---|
| Lignes | 187 283 | 187 283 |
| Durée | 1,06 s | 3,16 s |
| Pic mémoire | 618 Mo | 310 Mo |
| Sortie | Parquet 15,4 Mo | DataFrame 288,5 Mo en mémoire |

Vérification : 0 code vide, 0 doublon, zéros de tête conservés.
**À retenir :** les deux lectures donnent les mêmes lignes (DuckDB est fidèle). Sur un petit volume, pandas
consomme moins (voir question Q3), mais c'est la croissance avec le volume qui compte.

### 6.3 Fichier complet — chargement (étapes 1b, 2b)

`& $PY scripts/01_charger_duckdb.py --source $SRC --memory-limit 12GB --count-lines`

| Mesure | Valeur |
|---|---|
| Lignes source / écrites / perdues | 4 535 553 / 4 535 553 / **0** |
| Durée | **22,9 s** |
| Pic mémoire | 10,7 Go (plafond 12 Go) ; RAM libre au plus bas : 7,6 Go |
| Taille | CSV 12,1 Go → Parquet **381,8 Mo** |
| Codes | 0 vide, 0 non numérique, 1 202 322 avec zéro de tête (conservés) |
| Doublons de code | 60 groupes, 60 lignes en trop (≈ 0,001 %) |
| Produits vendus en France | 1 263 854 (27,87 %) — profilage TP 2 : ≈ 1 136 108 |
| Fiches avec les 7 nutriments clés | 41,17 % |
| SHA-256 | dans `out/verification_produits_bruts.md` |

### 6.4 Fichier complet — nettoyage du TP 9 (étape 04)

| Run | Lignes traitées | Lots | Durée | Pic mémoire | Plus petite RAM libre | Lignes gardées |
|---|---|---|---|---|---|---|
| A | 200 000 premières | 1 | 8,9 s | 5,4 Go | 13,2 Go | 19 001 (9,5 %) |
| B | 1 000 000 premières | 1 | 31,3 s | 6,6 Go | 12,2 Go | 105 336 (10,5 %) |
| C | **toutes (4 535 553)** | **1** | **146,8 s** | **14,1 Go** | **4,9 Go** | **996 637 (22,0 %)** |
| D | 300 000 premières | 4 + `--compare` | 26,2 s | 5,6 Go | 13,5 Go | 27 130 — **identique au bloc** |
| E | **toutes (4 535 553)** | **8** | **188,2 s** | **2,5 Go** | **16,2 Go** | **996 637 (22,0 %)** |

Détail du run E (un lot ≈ 567 000 lignes, ≈ 1,13 Go de DataFrame, 22 à 25 s chacun) :

| Lot | Entrée | Sortie |
|---|---|---|
| 1 | 567 418 | 124 313 |
| 2 | 566 214 | 124 760 |
| 3 | 566 945 | 124 427 |
| 4 | 568 248 | 125 341 |
| 5 | 567 671 | 124 515 |
| 6 | 565 827 | 123 898 |
| 7 | 566 643 | 124 323 |
| 8 | 566 587 | 125 060 |
| **Total** | **4 535 553** | **996 637** |

Détail des règles, run C (toutes les lignes, un bloc) :

| Ordre | Règle (TP 9) | Lignes touchées | Lignes restantes | Ce que fait la règle |
|---|---|---|---|---|
| 1 | type_columns | 0 | 4 535 553 | convertit nutriments en nombres, dates en dates |
| 2 | normalize_texts | 3 483 384 | 4 535 553 | normalise les textes (modifie sans supprimer) |
| 3 | filter_codes | 446 494 | 4 089 059 | écarte les codes-barres non conformes |
| 4 | deduplicate_codes | 50 | 4 089 009 | supprime les codes en double |
| 5 | normalize_units | 289 497 | 4 089 009 | harmonise les unités (sel/sodium, kJ/kcal…) |
| 6 | bound_nutrients | 6 390 | 4 089 009 | neutralise les valeurs hors bornes |
| 7 | fix_energy | 21 568 | 4 089 009 | corrige l'énergie incohérente |
| 8 | handle_empty_categories | 2 386 227 | 1 702 990 | écarte les produits hors catégories retenues (périmètre TP 2) |
| 9 | apply_missing_strategy | 706 353 | 996 637 | écarte les fiches trop incomplètes (seuil TP 2) |
| 10 | validate_output | 0 | 996 637 | vérifie le schéma de sortie (pandera) |

**Lecture :**
- Le nettoyage existant **tient sur 32 Go en un bloc**, mais avec seulement 4,9 Go de marge.
- **En 8 lots, le pic tombe à 2,5 Go (÷ 5,5)** pour 41 s de plus (+28 %), avec **exactement le même nombre de lignes**.
- 78 % des lignes sont écartées, surtout par les deux règles du **périmètre** (catégories, complétude).

### 6.5 Enquête doublons (étape 05) — hypothèse confirmée

Commande : `& $PY scripts/05_enquete_doublons.py --repo $REPO --parquet out/produits_bruts.parquet` (quelques secondes).

| Mesure | Valeur |
|---|---|
| Codes en double (groupes) / lignes / lignes en trop | 60 / 120 / 60 |
| Lignes en trop écartées par `filter_codes` (avant la déduplication) | **10** |
| Suppressions prédites pour `deduplicate_codes` (60 − 10) | **50** |
| Suppressions au rejeu des règles 1-4 du dépôt | **50** |
| Suppressions observées sur le fichier complet (run C) | **50** |
| Groupes dont les deux lignes sont strictement identiques | **0 / 60** |
| **Hypothèse confirmée** | **OUI** |

Verdict par code en double (fonctions officielles du dépôt `schema.is_official_length`, `schema.is_not_in_store`) :

| Groupes | Verdict |
|---|---|
| 50 | code officiel : passe `filter_codes`, puis dédupliqué (une fiche gardée sur deux) |
| 4 | écarté par `filter_codes` : préfixe 200-299 (code interne magasin) |
| 3 | écarté par `filter_codes` : 18 chiffres (ni EAN-8, ni UPC-A, ni EAN-13) |
| 2 | écarté par `filter_codes` : 14 chiffres |
| 1 | écarté par `filter_codes` : 15 chiffres |

Lecture :
- Les **trois chiffres concordent** (prédiction, rejeu, fichier complet) : l'écart de 10 est entièrement expliqué.
  Ce n'est ni une perte ni un bug : ces 10 codes en double ne sont pas des codes-barres officiels, ils sont
  écartés en entier (les deux lignes) avant que la déduplication ne les voie.
- **Aucun doublon n'est une copie exacte** : pour chaque code, Open Food Facts exporte deux fiches au contenu
  différent (nom, complétude, date de modification…). D'où l'intérêt de la règle de choix de `deduplicate_codes` :
  garder la fiche la plus complète, puis la plus récente, plutôt que « la première venue ».
- Détail ligne à ligne : `out/doublons_detail.csv` (verdict et fiche gardée) ; synthèse : `out/doublons_rapport.md`.

## 7. Questions que nous nous sommes posées (et réponses)

**Q1. Pourquoi réduire les colonnes n'a-t-il pas suffi ?**
Le fichier compte 211 colonnes (et non 120 comme on le pensait) ; en garder 41 divise la largeur par 5, mais
le problème est la **hauteur** : 4,5 millions de lignes, dont des textes longs (ingrédients, 6 URL d'images,
tags). En pandas, chaque texte est un objet Python avec son surcoût. Mesure : le DataFrame complet en entrée
du nettoyage pèse **9,05 Go** à lui seul (run C).

**Q2. Pourquoi `chunksize` (même à 1 000) ne réglait-il rien ?**
Lire par blocs limite seulement le pic *pendant* la lecture. Mais `reader.py` fait ensuite `pd.concat` de tous
les blocs : le tableau final est le même, en entier, en mémoire. Un `chunksize` de 1 000 ajoute même des milliers
de petits blocs à concaténer, donc de la lenteur, sans gain de mémoire.

**Q3. Pourquoi DuckDB consomme-t-il plus que pandas sur 500 Mo (618 contre 310 Mo) ?**
DuckDB réserve des tampons pour ses 16 threads : c'est un **coût fixe**. pandas grandit avec le volume :
288 Mo pour 187 000 lignes → 9 Go pour 4,5 millions. DuckDB, lui, reste sous le plafond qu'on lui donne
(10,7 Go pour 12 Go autorisés sur 12 Go de CSV), et aurait débordé sur disque avec un plafond plus bas.

**Q4. Pourquoi la tranche de 500 Mo et le premier million de lignes « mentent » ?**
Le fichier OFF est **trié par code-barres**. Les premières lignes ne contiennent que des codes commençant par `0`
(100 % dans la tranche). Ce ne sont pas des produits représentatifs : 7,7 % de France dans la tranche contre
27,9 % dans le fichier ; 10 % de lignes gardées au nettoyage sur le premier million contre 22 % au total ;
`filter_codes` écarte 46 lignes sur le premier million contre 446 494 au total.
**Leçon :** une tranche sert à tester que le code tourne, jamais à estimer des pourcentages.

**Q5. « 4 lots de 300 000 » : pourquoi pas tout le fichier ? (run D)**
Confusion fréquente : `--rows 300000 --batches 4` signifie **300 000 lignes au total, coupées en 4 lots
d'environ 75 000** (75 459 + 74 624 + 74 911 + 75 006 = 300 000). Ce run sert uniquement à **prouver** que
« par lots » = « en un bloc » : `--compare` nettoie les mêmes lignes deux fois et garde les deux résultats
en mémoire pour les comparer, d'où un volume volontairement petit. Le fichier entier en lots, c'est le run E :
`--rows 0` (toutes les lignes) `--batches 8` (8 lots d'environ 567 000).

**Q6. Pourquoi répartir les lots par hachage du code et pas simplement par tranches de lignes ?**
À cause de `deduplicate_codes`. Si deux lignes ont le même code et tombent dans deux lots différents, chaque
lot les voit seules et les **garde toutes les deux** : le doublon survit. Avec `hash(code) modulo 8`, un même
code donne toujours le même numéro de lot, donc les doublons se retrouvent ensemble. Les autres règles
travaillent ligne par ligne : elles donnent le même résultat quel que soit le découpage.

**Q7. Comment sait-on que les lots donnent le même résultat ?** Trois niveaux de preuve :
1. **Raisonnement** (Q6) : seule la déduplication compare des lignes entre elles, et le hachage la protège.
2. **Comparaison ligne à ligne** sur 300 000 lignes (run D) : `Identique : True` (valeurs, colonnes, lignes).
3. **Comptage sur tout le fichier** (runs C et E) : 996 637 lignes dans les deux cas, avec les 50 doublons du fichier.
Limite honnête : sur le fichier entier on a comparé les **effectifs**, pas chaque valeur (voir section 11).

**Q8. Pourquoi les lots sont-ils plus lents (188 s contre 147 s) ?**
Chaque lot relit le Parquet pour y prendre ses lignes (8 lectures au lieu d'une) et le nettoyage a un coût
fixe par appel. On échange 41 secondes contre 11,6 Go de mémoire en moins.

**Q9. Pourquoi y a-t-il 60 lignes en double dans le brut mais seulement 50 supprimées au nettoyage ?**
**Réponse vérifiée (étape 05, section 6.5).** `filter_codes` (règle 3) passe avant `deduplicate_codes` (règle 4).
10 des 60 codes en double ne sont pas des codes officiels (4 codes internes magasin, préfixe 200-299 ; 6 codes de
14, 15 ou 18 chiffres) : leurs deux lignes sont écartées par `filter_codes` et n'arrivent jamais à la
déduplication. Il reste 50 codes officiels en double → 50 suppressions.

Pourquoi aucune autre explication n'était possible :
- tous les codes du brut sont uniquement des chiffres : le retrait des espaces ne crée ni ne fusionne de doublons ;
- `type_columns` et `normalize_texts` ne suppriment aucune ligne ;
- deux lignes de même code reçoivent le même verdict de `filter_codes` : un groupe est gardé ou écarté en entier.

Méthode de preuve, réutilisable : (1) **prédire** avec les fonctions du dépôt, (2) **rejouer** le code du dépôt sur
les seules lignes concernées, (3) **comparer** à l'observation sur le fichier complet. Les trois donnent 50.
Constat en plus : aucun des 60 doublons n'est une copie exacte ; ce sont deux fiches différentes pour un même code.

**Q10. Que veut dire « pic mémoire » et pourquoi dépasse-t-il parfois la limite DuckDB ?**
C'est la mémoire occupée par tout le processus Python (pandas + DuckDB), relevée toutes les 0,5 s ; un pic très
bref peut échapper à la mesure. La limite DuckDB ne concerne que les tampons de DuckDB, pas pandas. Le chiffre
à surveiller pour la sécurité de la machine est la **RAM libre au plus bas** : 4,9 Go au run C, 16,2 Go au run E.

**Q11. Pourquoi le Parquet est-il 32 fois plus petit que le CSV ?**
Trois effets cumulés : 41 colonnes sur 211 ; stockage par colonne (les valeurs d'une même colonne se ressemblent
et se compressent bien) ; compression ZSTD. Et beaucoup de cellules vides, qui ne coûtent presque rien en Parquet.

**Q12. Pourquoi tout lire en texte alors que les nutriments sont des nombres ?**
Un brut « figé » ne doit rien interpréter : un code `0012345678905` lu comme nombre perd ses zéros, une valeur mal
saisie ferait échouer la lecture. Le typage est la règle 1 du nettoyage du TP 9 ; on la laisse faire son travail.

**Q13. Pourquoi ne pas avoir tout réécrit en SQL DuckDB (plus rapide) ?**
L'énoncé du TP 13 interdit de refaire les TP précédents (« le TP 13 assemble, il ne refait pas ») ; le nettoyage
du TP 9 est testé et documenté. On a donc remplacé seulement la **lecture**, là où était le problème.

**Q14. Pourquoi 1 263 854 produits France contre 1 136 108 au TP 2 ?**
Non tranché. Hypothèses : export OFF plus récent ; comptage différent au TP 2 (colonne `countries` au lieu de
`countries_tags`, filtres déjà appliqués). Comme l'équipe garde tous les pays (section 9), cet écart n'a pas
d'impact sur le pipeline, mais il faudra l'expliquer si on cite ce chiffre.

**Q15. La tranche de 500 Mo et `--compare` suffisent-elles pour valider la méthode ?**
Pour valider que le code **fonctionne** : oui. Pour valider des **chiffres** : non (Q4). C'est pour ça qu'on a
fini par le fichier entier en un bloc puis en lots.

## 8. Incidents techniques et corrections

| # | Symptôme | Cause | Correction |
|---|---|---|---|
| 1 | `No runtime installed that matches 3.12` | Python 3.12 non installé (machine en 3.8 et 3.14) | `py install 3.12` |
| 2 | `Defaulting to user installation`, pandas 2.3 introuvable | venv non activé : `python` = Python 3.8 du système, pour lequel pandas s'arrête à 2.0.3 | appeler le Python du venv explicitement : `& $PY …` |
| 3 | `cd C:\Users\<vous>\…` : caractères non conformes | exemple du README recopié tel quel | chemin réel (README corrigé) |
| 4 | `--source: expected one argument` | `$SRC` non défini dans ce terminal | définir `$SRC`, `$REPO`, `$PY` dans le même terminal |
| 5 | `python.exe : accès refusé`, puis `WinError 32` pendant `pip install` | un autre processus (VS Code et son extension Python) ouvrait les fichiers du venv | fermer VS Code ; venv créé hors du projet ; pas de `pip install --upgrade pip` |
| 6 | `cannot import name '_log' from pip` | mise à jour de pip interrompue par l'incident 5 | venv neuf |
| 7 | `L'expression située après « & » … objet non valide` | nouveau terminal : `$PY` vide | redéfinir les variables (section 5) |
| 8 | 13,4 Go de RAM libre seulement | applications ouvertes | tout fermer (→ 17-19 Go libres) ; plafond DuckDB sous la RAM libre |

Leçon générale : sous Windows, **un terminal = ses variables**, et **un venv = un chemin à vérifier**
(`sys.executable`) avant d'installer quoi que ce soit.

## 9. Décisions prises

| Date | Décision | Raison | Conséquence |
|---|---|---|---|
| 14/10 | **Périmètre géographique : tous les pays** (aucun filtre pays au chargement ni au nettoyage) | choix d'équipe | s'écarte du critère « commercialisé en France » du TP 2 (`docs/cadrage/parties/perimetre.md`) : à reporter dans ce document et dans `docs/journal_tp13.md` ; tout le volume passe par le nettoyage |
| 14/10 | Chargement par **DuckDB** (texte, 41 colonnes, tri par code, plafond 12 Go) | 23 s, 0 perte, 10,7 Go de pic | méthode reprise pour l'étape `charger` du TP 13 |
| 14/10 | Nettoyage du TP 9 **inchangé** | conforme à l'énoncé ; tient sur le volume complet | pas de réécriture |
| à valider | Nettoyage **par lots** (8) par défaut, ou en un bloc | lots : 2,5 Go au lieu de 14,1 Go, +28 % de temps, même résultat | les lots rendent le pipeline exécutable sur une machine de 16 Go |

## 10. Conclusions pour le TP 13

- **Étape `charger`** : reprendre `bigtest/charger.py` (DuckDB, `all_varchar`, `quote=''`, 41 colonnes,
  `ORDER BY code`, plafond configurable, écriture dans un `.tmp` puis renommage) → Parquet brut **daté**.
- **Étape `nettoyer`** : lire ce Parquet et appeler `cleaning.clean()` ; option `--batches N` avec répartition
  par `hash(trim(code)) % N`. Recommandation : **8 lots par défaut** (robuste sur toute machine), 1 bloc possible
  sur 32 Go.
- **Volumes de référence** : brut 4 535 553 → nettoyé 996 637.
- **Durées de référence** pour `docs/data/pipeline.md` (Windows 11, 16 cœurs, 32 Go, Python 3.12, DuckDB 1.5.6) :
  chargement 23 s ; nettoyage 2 min 27 s (1 bloc) ou 3 min 08 s (8 lots).
- **Faut-il un orchestrateur ?** Non : le flux complet tient en quelques minutes ; une CLI (et un Makefile façade) suffit.
- **Tests du pipeline** : toujours sur l'échantillon (`data-nutriscope/echantillon_france.csv`), jamais sur les 12 Go.

## 11. Points ouverts et limites

1. **`filter_codes` écarte 446 494 lignes (9,8 %)** sur le fichier entier : vérifier quels formats de code sont
   rejetés (longueurs, préfixes) pour s'assurer qu'on n'élimine pas des codes valides.
2. **Égalité bloc / lots sur le fichier entier** : prouvée en effectifs (996 637), en valeurs seulement sur
   300 000 lignes. Pour une preuve complète : écrire les deux sorties triées par code et comparer leurs SHA-256.
3. **Écart France** avec le TP 2 (Q14) : à expliquer si le chiffre est cité.
3 bis. ~~60 doublons dans le brut, 50 au nettoyage~~ → **résolu** (section 6.5) : 10 lignes appartiennent à des codes non officiels écartés par `filter_codes`.
4. **Versions** : le test utilise pandera 0.34 et numpy 2.5, plus récentes que celles probablement utilisées au
   TP 9 ; le dépôt devra **épingler** ses versions (`requirements.txt`) pour que le TP 13 soit reproductible.
5. **Une seule machine mesurée** : refaire au moins le run E sur une autre machine de l'équipe.
6. **Mesure mémoire** toutes les 0,5 s : un pic très bref peut être sous-estimé.

## 12. Refaire la démonstration en 10 minutes

```powershell
# 0. terminal neuf, VS Code fermé
cd C:\Users\Administrateur\Desktop\cours\exo\nutriscope_bigdata_test
$PY   = "$env:USERPROFILE\venvs\nutriscope312\Scripts\python.exe"
$SRC  = "C:\Users\Administrateur\Desktop\cours\exo\Nutriscope_team_delegue\data\en.openfoodfacts.org.products.csv"
$REPO = "C:\Users\Administrateur\Desktop\cours\exo\Nutriscope_team_delegue"

& $PY -m pytest -q                                                            # 8 passed (secondes)
& $PY scripts/00_check_env.py --source $SRC                                   # environnement
& $PY scripts/01_charger_duckdb.py --source $SRC --memory-limit 12GB          # ≈ 23 s : 12 Go -> 382 Mo
& $PY scripts/02_verifier.py --parquet out/produits_bruts.parquet             # contrôles
& $PY scripts/04_mesure_nettoyage.py --repo $REPO --parquet out/produits_bruts.parquet --rows 0 --batches 8   # ≈ 3 min, 2,5 Go
```

Message à faire passer : **le problème n'était pas la quantité de colonnes mais la façon de lire ;
en confiant la lecture à DuckDB et en nettoyant par lots, le même code du TP 9 traite 4,5 millions de produits
avec 2,5 Go de mémoire.**

Données : © Open Food Facts contributors — ODbL.
