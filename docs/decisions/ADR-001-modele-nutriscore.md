# ADR-001 : Modèle de prédiction du Nutri-Score

## Contexte

L'application doit prédire le grade Nutri-Score (a à e) des produits qui n'en ont pas
(TP 16), et repérer les fiches dont le grade déclaré ne colle pas aux nutriments. En
phase 6, le pipeline persisté sera chargé dans l'API : sa taille et sa latence sont des
contraintes. Il sera réentraîné à chaque évolution des règles de nettoyage, d'où
l'importance du coût de réentraînement.

Conditions de comparaison, identiques pour toutes les options (`nutriscope.classification`) :

- même jeu : `nutriscope_ml_sample.parquet`, 30 041 produits, split figé du TP 13
  (24 076 train / 5 965 test) ;
- même préparation (`preparation()`) : features dérivées, imputation avec indicateur de
  manquant, standardisation, one-hot des rayons ;
- mêmes plis (`StratifiedKFold(5, shuffle=True, random_state=42)`), mêmes métriques ;
- test regardé une seule fois, après tous les choix.

Toutes les valeurs ci-dessous viennent de `notebooks/ml_nutriscore.ipynb`.

## Options considérées

| Option                     | F1 macro CV (± é.-t.) | F1 macro test | Ajustement (s / pli) | Latence (ms / produit) | Taille (joblib) |
| -------------------------- | --------------------- | ------------- | -------------------- | ---------------------- | --------------- |
| Régression logistique      | 0,781 ± 0,007         | 0,782         | 1,6                  | 0,004                  | 11 Ko           |
| Forêt aléatoire            | 0,856 ± 0,007         | 0,856         | 1,7                  | 0,012                  | 78,6 Mo         |
| **XGBoost (défaut)**       | 0,894 ± 0,007         | 0,895         | 3,7                  | 0,007                  | 1,7 Mo          |
| XGBoost réglé (Optuna)     | 0,898 ± 0,007         | 0,899         | 42,2                 | 0,023                  | 27,5 Mo         |
| HistGradientBoosting       | 0,890 ± 0,005         | 0,888         | 7,0                  | 0,013                  | 1,8 Mo          |
| LightGBM                   | 0,888 ± 0,010         | 0,886         | 2,8                  | 0,012                  | 1,7 Mo          |
| CatBoost                   | 0,889 ± 0,005         | 0,885         | 31,3                 | 0,005                  | 3,1 Mo          |

Lecture :

- **Le boosting sépare nettement les familles.** Il gagne environ 0,04 de F1 macro sur la
  forêt et 0,11 sur la logistique, soit plus de cinq écarts-types des plis.
- **Le réglage ne paie pas.** Optuna (30 essais, 11 minutes réelles) apporte +0,0044 sur
  XGBoost, sous le seuil de deux écarts-types (0,0136). En échange, l'ajustement est onze
  fois plus long (42,2 s contre 3,7 s), la latence trois fois plus élevée et le modèle
  seize fois plus lourd (27,5 Mo contre 1,7 Mo).
- **Les boosters ne se départagent pas sur la performance.** Ils tiennent en 0,006 de
  F1 macro (de 0,888 à 0,894), soit environ un écart-type des plis : nous n'affirmons
  pas que XGBoost surpasse HistGradientBoosting, LightGBM ou CatBoost. Seule la version
  réglée de XGBoost les dépasse de plus d'un écart-type (0,0066, calculé à la section
  « Critères de décision mesurés »), et son gain n'est pas significatif face à XGBoost
  par défaut. Le choix se fait donc sur les autres critères.
- **L'écart entre validation croisée et test reste sous 0,004 pour toutes les options** :
  le test confirme le classement de la validation croisée, il ne l'a pas produit.

Autres critères :

- **Explicabilité** : les quatre boosters sont compatibles avec SHAP (`TreeExplainer`),
  qui servira en phase 6. La logistique a des coefficients lisibles nativement.
- **Maintenance** : HistGradientBoosting ne demande aucune dépendance hors scikit-learn.
  XGBoost, LightGBM et CatBoost ajoutent chacun une bibliothèque à épingler. CatBoost
  demande en plus une enveloppe pour ses prédictions de forme (n, 1).

## Décision

Nous retenons XGBoost avec ses paramètres par défaut, dans le pipeline
`make_model(XGBClassifier(random_state=42))`.

## Conséquences

- **Performance** : 0,894 ± 0,007 de F1 macro en validation croisée, 0,895 sur le test,
  soit 0,04 de mieux que la forêt du TP 14.
- **Coûts** : 7 µs de prédiction par produit et 1,7 Mo sur disque, compatibles avec
  l'API de la phase 6. Un réentraînement complet prend quelques secondes sur ce jeu. La
  forêt du TP 14 pesait 78,6 Mo, au-dessus de la limite de 50 Mo fixée pour un modèle
  versionné.
- **Simplicité** : aucun hyperparamètre réglé à maintenir. Le budget Optuna n'a pas à être
  relancé à chaque nouvel export.
- **Ce qu'on sacrifie** : 0,004 de F1 macro, non significatif, par rapport à la version
  réglée. On ajoute aussi une dépendance (`xgboost`) que HistGradientBoosting aurait
  évitée, pour un F1 inférieur de 0,004, lui aussi non significatif.
- **Explicabilité** : les prédictions s'expliquent par SHAP ; sans outil tiers, le modèle
  ne se lit pas directement.

## Ce qui déclencherait une révision

- Sur un nouvel export daté, XGBoost tombe sous un autre booster de plus de deux
  écarts-types des plis, sur deux exports consécutifs.
- La latence mesurée dans l'API dépasse 1 ms par produit, ou le modèle sérialisé dépasse
  50 Mo.
- La dépendance `xgboost` bloque une montée de version de Python ou de scikit-learn :
  basculer sur HistGradientBoosting, dont la performance est équivalente sur ce jeu.
- Un réglage sur l'extrait complet (422 470 produits) apporte un gain supérieur à deux
  écarts-types : réévaluer la version réglée.

Données : © Open Food Facts contributors — ODbL.
