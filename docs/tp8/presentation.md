# Trame de présentation (10 minutes) — TP 8, Jalon J2
### Note de cadrage & backlog — NutriScope

**Équipe :** Sébastien HUS / Nicolas CUSUMANO
**Objectif de l'exercice :** obtenir la validation de la direction (formateur) sur le jalon J2, ou repartir avec des points de correction précis.

---

## Répartition du temps (10 minutes)

| Temps | Contenu | Support |
|---|---|---|
| 0–1 min | Rappel de l'objectif du jalon J2 et de ce qui est présenté | `note_cadrage_tp8.md` (préambule) |
| 1–3 min | Besoin, cible et périmètre du MVP | `note_cadrage_tp8.md` §1 et §3 |
| 3–5 min | KPI et retour sur investissement : les trois scénarios, le seuil de rentabilité | `note_cadrage_tp8.md` §4 |
| 5–7 min | Le risque critique et les risques importants, leurs plans de mitigation | `note_cadrage_tp8.md` §5, matrice `matrice-risques.jpg` |
| 7–9 min | Backlog priorisé, outil de suivi retenu et rituels d'équipe | `backlog_produit_tp8.md`, `outillage_rituels_tp8.md` |
| 9–10 min | Macro-planning J3 à J7 et point à trancher avec la direction | `planning.md` |

---

## Message central à faire passer

NutriScope est cadré pour livrer un MVP resserré sur quatre briques d'intelligence artificielle et cinq à huit rayons alimentaires, avec des indicateurs et un modèle de retour sur investissement chiffrés — mais ce modèle repose sur une hypothèse encore jamais vérifiée : le taux de conversion vers l'abonnement Premium. Le jalon J2 est atteint ; le jalon suivant qui compte réellement pour la viabilité économique du projet est le jalon J4, avant lequel ce taux de conversion doit être testé auprès d'un échantillon réel d'utilisateurs.

## Point à trancher avec la direction (à préparer avant la présentation)

Faut-il engager le test réel du taux de conversion Premium (présentation de l'offre payante à 200–300 utilisateurs, sans encaissement) dès le mois 3, en parallèle du travail sur le modèle Nutri-Score, plutôt que d'attendre le mois 4 ? Avancer ce test réduit le risque du jalon J4 mais mobilise une partie de l'équipe marketing plus tôt que prévu.

## Anticiper les questions probables du formateur

- Pourquoi ce périmètre MVP et pas un périmètre plus large ou plus restreint ? → renvoyer à la matrice de priorisation MoSCoW (`backlog_produit_tp8.md`) et au tableau de priorisation du cahier des charges.
- Pourquoi ce risque est-il classé critique et pas les autres ? → renvoyer à la matrice probabilité × impact et à sa légende (rouge = mitigation obligatoire avant le go).
- Pourquoi ce choix d'outil de suivi plutôt qu'un tableau kanban externe ? → renvoyer à l'argument de simplicité opérationnelle (`outillage_rituels_tp8.md` §1.1).
- Que se passe-t-il si le taux de conversion réel est inférieur au scénario pessimiste ? → le scénario pessimiste n'atteint la rentabilité qu'au mois 34 ; un taux plus bas remettrait en cause la viabilité du modèle économique tel que chiffré, et non plus seulement son horizon de rentabilité.

## À l'issue de la présentation

Si la direction valide : committer la note de cadrage, le backlog, `docs/cadrage/planning.md`, et poser le tag `v0.2` (voir instructions ci-dessous).
Si la direction renvoie en correction : noter précisément le ou les points contestés avant de quitter la salle — ne pas reformuler de mémoire après coup.

---

## Instructions de commit et de tag (à exécuter par l'équipe sur son dépôt)

```
git add docs/cadrage/note_cadrage.md docs/cadrage/backlog_produit.md docs/cadrage/planning.md docs/cadrage/outillage_rituels.md
git commit -m "TP8 : note de cadrage, backlog outillé, planning J3-J7, rituels — jalon J2 atteint"
git tag -a v0.2 -m "Jalon J2 : cadrage consolidé et backlog outillé"
git push origin main --tags
```

Ces commandes sont à exécuter sur le dépôt d'équipe réel ; elles ne peuvent pas être lancées depuis cet environnement de travail.