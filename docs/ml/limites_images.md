# Note : ce que le classifieur d'images sait et ne sait pas faire

Modèle décrit : _à compléter (MobileNetV2 fine-tuné ? CNN de référence ?)_, sauvegardé dans
`models/image_classifier/` (voir `metadata.json`). Toutes les mesures viennent de
`notebooks/dl_images.ipynb`.

Photos : contributeurs Open Food Facts, licence CC BY-SA.

## Contexte de mesure

| Élément | Valeur |
| --- | --- |
| Rayons | _à compléter_ (écart avec `docs/cadrage/parties/perimetre.md` : _à compléter_) |
| Photos retenues / écartées | _à compléter_ / _à compléter_ (`src/images_bucket/excluded_images.csv`) |
| Découpage train / validation / test | _à compléter_ |
| Plancher annoncé | _à compléter_ (hasard uniforme 1/K) |
| CNN de référence (validation) | _à compléter_ |
| Transfert retenu (validation) | _à compléter_ |
| **Test (ouvert une seule fois)** | _à compléter_ |
| Seuil « je ne sais pas » | _à compléter_ — justification : _à compléter_ |
| Couverture / accuracy sur les réponses (test) | _à compléter_ |

## 1. Ce que le modèle rate

_Paragraphe 1 — à compléter : quels rayons sont confondus entre eux, dans quelle proportion,
et pourquoi d'après la planche d'erreurs (formes d'emballage proches, photos hors sujet,
cadrage, etc.)._

_Paragraphe 2 — à compléter : ce que ces erreurs signifient pour l'utilisateur de NutriScope
et ce que le seuil rattrape (ou ne rattrape pas)._

## 2. Deux pistes d'amélioration (tirées de la planche d'erreurs)

1. _à compléter_
2. _à compléter_
