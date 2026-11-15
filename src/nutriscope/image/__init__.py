"""
Classifieur d'images de NutriScope (TP 17) : reconnaître le rayon d'un produit à partir de sa photo.

Sous-modules :
- `data` : inventaire des photos, exclusions, découpage figé, pipelines tf.data ;
- `models` : CNN de référence, transfert MobileNetV2, fine-tuning, sauvegarde ;
- `evaluation` : plancher, scores par rayon, confusion, seuil « je ne sais pas », planche d'erreurs ;
- `classifier` : brique photo → rayon + confiance, appelée par l'API (TP 23).

Seule la brique est exposée ici : `from nutriscope.image import ImageClassifier` n'importe
pas TensorFlow tant qu'aucun modèle n'est chargé.

Photos : CC BY-SA, contributeurs Open Food Facts.
"""

from .classifier import DEFAULT_MODEL_DIR, UNKNOWN, ImageClassifier, Prediction, decide

__all__ = ["DEFAULT_MODEL_DIR", "UNKNOWN", "ImageClassifier", "Prediction", "decide"]
