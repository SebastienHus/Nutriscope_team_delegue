### Contribution au projet Deluscop

Ce document décrit les règles et bonnes pratiques mise en place par l'équipe Team délégué pour contribuer efficacement sur le projet Deluscop


### Table des matieres

- [Objectifs](#objectifs)
- [Prérequis](#prérequis)
- [Regles de Branches](#regles-de-branches)
- [Messages de Commit](#messages-de-commit)
- [Tests et Qualite](#tests-et-qualite)
- [Soumettre une Pull Request](#soumettre-une-pull-request)

---

## Objectifs

Vos contributions auront pour but :

- Corriger des anomalies.
- Ajouter de nouvelles fonctionnalités.
- Améliorer les performances.
- Améliorer la documentation.
- Renforcer la qualité du code.

---

## Prérequis

1. Forkez le projet sur votre compte GitHub ou GitLab.
   
2. Clonez :
   ```bash
   git clone https://github.com[votre-utilisateur]/Nutriscope_team_delegue.git
   ```
3. Installez les dependances necessaires :
   ```bash
   [Exemple: npm install / pip install -r requirements.txt]
   ```

---

## Regles de Branches

Creez toujours une nouvelle branche depuis la branche dev pour vos modifications. 
N'envoyez jamais de commits directement sur la branche principale (main).

Nommez vos branches selon la convention suivante :
* `feature/[nom-court]` : Ajout d'une nouvelle fonctionnalite.
* `fix/[nom-court]` : Correction d'un bug.
* `docs/[nom-court]` : Modification de la documentation.


## Messages de Commit

Nous suivons la convention Conventional Commits. Vos messages doivent etre clairs et structures :

`type(contexte): description courte en minuscule`

* `feat`: Une nouvelle fonctionnalite.
* `fix`: Une correction de bug.
* `docs`: Changement dans la documentation.
* `refactor`: Modification de code qui ne corrige pas un bug et n'ajoute pas de fonctionnalite.

Exemple : `feat(auth): ajouter la connexion par mot de passe`


## Tests et Qualite

Avant de soumettre votre travail :
* Assurez-vous que le projet compile sans erreur.
* Lancez les tests locaux : `[Commande de test, ex: npm test]`
* Respectez les conventions de code du projet.


## Soumettre une Pull Request

1. Mettez a jour votre branche par rapport a la branche principale officielle.
2. Poussez (push) vos modifications sur votre fork.
3. Ouvrez une Pull Request avec un titre clair.
4. Decrivez precisement vos changements.
5. Attendez la relecture et la validation d'un mainteneur du projet.
