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

NutriScope est cadré pour livrer un MVP resserré sur cinq à huit rayons alimentaires, quatre briques d'intelligence artificielle tournées vers l'utilisateur et deux briques techniques qui les fiabilisent, avec des indicateurs et un modèle de retour sur investissement chiffrés — mais ce modèle repose sur une hypothèse encore jamais vérifiée : le taux de conversion vers l'abonnement Premium. Le jalon J2 est atteint ; le moment qui compte réellement pour la viabilité économique du projet se situe entre les jalons J5 et J6, lorsque la cohorte de bêta-testeurs sera la première à voir l'offre payante.

## Point à trancher avec la direction (à préparer avant la présentation)

La cohorte de bêta-testeurs prévue avant le jalon J6 compte vingt à trente personnes. C'est assez pour recueillir des retours d'usage, mais très insuffisant pour mesurer un taux de conversion : avec trente personnes, un seul abonné de plus ou de moins fait varier le taux de plusieurs points. Faut-il élargir cette cohorte au-delà de trente personnes pour obtenir un signal économique exploitable — ce qui mobilise le marketing plus tôt et plus fortement que prévu — ou assumer que le taux de conversion restera une hypothèse non vérifiée jusqu'à l'ouverture publique ?

## Anticiper les questions probables du formateur

- Pourquoi ce périmètre MVP et pas un périmètre plus large ou plus restreint ? → renvoyer à la matrice de priorisation MoSCoW (`backlog_produit_tp8.md`) et au tableau de priorisation du cahier des charges.
- Pourquoi ce risque est-il classé critique et pas les autres ? → renvoyer à la matrice probabilité × impact et à sa légende (rouge = mitigation obligatoire avant le go).
- Pourquoi ce choix d'outil de suivi plutôt qu'un tableau kanban externe ? → renvoyer à l'argument de simplicité opérationnelle (`outillage_rituels_tp8.md` §1.1).
- Que se passe-t-il si le taux de conversion réel est inférieur au scénario pessimiste ? → le scénario pessimiste n'atteint déjà plus l'équilibre sur les trois années observées ; en dessous de 0,7 % de conversion, c'est la viabilité même du modèle économique qui est en cause, pas son horizon de rentabilité.
- Le budget couvre-t-il bien tout le périmètre annoncé ? → oui : le chiffrage intègre les 19 500 € de construction des briques complémentaires (classifieur d'images, segmentation, tableaux de bord, supervision) et le coût récurrent de journalisation, soit 260 154 € sur la première année.

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
