# ADR-EXEMPLE : Modèle retenu pour le moteur de popularité

## Contexte

Le moteur doit classer un livre en cinq niveaux de popularité avant publication, à partir de
ses caractéristiques éditoriales. Trois familles de modèles ont été comparées à conditions
égales (même préparation, mêmes plis, même test) dans les démos 01 et 04.

## Options considérées

| Option        | F1 macro (test) | Taille    | Latence / produit |
| ------------- | --------------- | --------- | ----------------- |
| Logistique    | 0.647           | 6.5 Ko    | 0.015 ms          |
| Random Forest | 0.608           | 50702 Ko  | 0.165 ms          |
| LightGBM      | 0.612           | 5113.9 Ko | 0.047 ms          |

## Décision

Nous retenons la régression logistique.

## Conséquences

- Modèle livrable en 6 Ko contre plusieurs dizaines de méga-octets pour la forêt : aucune
  contrainte de taille sur le service qui le chargera.
- Coefficients directement lisibles par classe : explicabilité native, sans outil tiers.
- Performance égale ou supérieure aux alternatives plus lourdes sur ce jeu précis — à
  réévaluer si la relation entre features et cible devient moins linéaire (nouvelles features,
  nouveau catalogue).

## Ce qui déclencherait une révision

Si le F1 macro de la logistique retombe sous celui de LightGBM de plus de deux écarts-types
sur trois mesures consécutives, ou si de nouvelles features à fortes interactions non
linéaires sont ajoutées (ce que la logistique capture mal, voir démo 01).
