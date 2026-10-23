# Gabarits : ADR et Note des limites

Deux documents différents, à ne pas fusionner :

- l'**ADR** justifie un choix (quel modèle/architecture, pourquoi celui-là et pas un autre)
- la **note des limites** documente ce qu'un modèle déjà choisi sait et ne sait pas faire, pour que quelqu'un d'autre sache quand lui faire confiance.

## 1. Structure d'une ADR (Architecture Decision Record)

```markdown
# ADR-<numéro> : <Décision en une phrase>

## Contexte

Quel problème force cette décision ? Quelles contraintes (produit, données, délai,
infrastructure) cadrent les options possibles ?

## Options considérées

| Option   | Métrique clé | Coût (taille / latence / complexité) | Autre critère |
| -------- | ------------ | ------------------------------------ | ------------- |
| Option A | ...          | ...                                  | ...           |
| Option B | ...          | ...                                  | ...           |
| Option C | ...          | ...                                  | ...           |

Une ligne par option réellement envisagée, pas une liste exhaustive de tout ce qui existe.

## Décision

Une phrase, sans ambiguïté : « Nous retenons X. »

## Conséquences

- Ce que ce choix facilite (immédiatement, chiffré si possible).
- Ce qu'il rend plus difficile ou ce qu'on sacrifie en échange.

## Ce qui déclencherait une révision

Seuil ou événement concret qui remettrait la décision en cause (ex. métrique qui chute sous un
concurrent de X % sur N mesures, nouvelle contrainte produit, changement de volumétrie).
```

**Règles de rédaction**

- Une ADR par décision, pas un journal de toutes les décisions du projet.
- Chiffrer les options sur les mêmes conditions (mêmes données, même split)
- La section « Ce qui déclencherait une révision » est obligatoire : une décision sans condition de révision est une décision qu'on ne réévaluera jamais.

## 2. Structure d'une Note des limites

```markdown
# Note : Ce que modèle sait et ne sait pas faire

## 1. Ce que le modèle sait faire

Métrique globale de référence (quelle métrique, quelle valeur, dans quelles conditions de
mesure). Ce que révèle la structure des erreurs quand il se trompe (proche ou loin de la bonne
réponse ?).

## 2. Les cas difficiles

Quelles classes/catégories/entrées se confondent le plus, et pourquoi on peut le comprendre
(proximité réelle, ambiguïté de la donnée).

## 3. Les zones les moins bien couvertes

Quels sous-groupes (catégorie rare, segment peu représenté) ont une performance nettement
inférieure à la moyenne, avec la taille d'échantillon qui explique en partie l'écart.

## 4. Quand ne pas faire confiance au modèle

Liste de règles concrètes et actionnables, pas des généralités :

- Condition explicite (seuil, taille d'échantillon, combinaison de features) => action à prendre (ne pas afficher, marquer comme incertain, escalader).
- Chaque règle doit pouvoir être vérifiée automatiquement par le code qui consomme le modèle.
```

**Règles de rédaction**

- Chaque affirmation renvoie à une mesure reproductible.
- La section 4 est la plus importante : elle doit être directement traduisible en code (if/else sur un seuil), pas rester une intention vague.
- Ne pas répéter dans la note ce qui relève de la décision de modèle (ça va dans l'ADR).

---

## 3. Quand utiliser laquelle

| Question à laquelle on répond                                             | Document                                     |
| ------------------------------------------------------------------------- | -------------------------------------------- |
| Pourquoi avoir choisi ce modèle plutôt qu'un autre ?                      | ADR                                          |
| Ce modèle, une fois en prod, dans quels cas a-t-il raison de se tromper ? | Note des limites                             |
| Faut-il changer de modèle ?                                               | ADR (section « déclencherait une révision ») |
| Faut-il masquer/escalader une prédiction précise ?                        | Note des limites (section 4)                 |
