# Note — Ce que le moteur de popularité (démo) sait et ne sait pas faire

## 1. Ce que le modèle sait faire

F1 macro 0,63 en validation croisée sur cinq plis (démo 01). Sur les erreurs du test (démo 03),
95,8 % sont à un seul cran d'écart (`meconnu`/`lu`, `lu`/`apprecie`, etc.) : le modèle situe le
bon voisinage même quand il rate la classe exacte, et ne confond presque jamais les extrêmes.

## 2. Les classes difficiles

`apprecie` et `lu` se confondent le plus (démo 03, couples les plus fréquents parmi les
erreurs) : ce sont les deux classes centrales, les plus proches l'une de l'autre dans le score
latent. `meconnu` et `culte`, aux extrêmes, sont nettement mieux séparées.

## 3. Les rayons les moins bien couverts

`theatre` (f1 macro ≈ 0,47, n=21) et `policier` (f1 macro ≈ 0,50, n=115) sont les deux rayons
les plus faibles (démo 03) — `theatre` probablement par manque d'effectif, `policier` pour une
raison qui reste à investiguer sur le vrai jeu.

## 4. Quand ne pas faire confiance au modèle

- Ne pas afficher de prédiction pour les rayons de moins de 30 exemplaires dans le train : le
  modèle n'a pas vu assez de cas pour généraliser (`theatre`, `poesie`).
- Signaler comme incertaine toute prédiction dont `nb_recommandations_libraires` dépasse 60 %
  mais dont `note_moyenne` est sous 4,0 : c'est exactement la zone où l'interaction mal apprise
  de la démo 04 produit des faux `culte` à haute confiance.
