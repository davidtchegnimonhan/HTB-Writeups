#!/usr/bin/env python3
"""
Nexus HTB — Flag POC

POC post-exploitation READ-ONLY.

Le script ne lance pas d'exploitation réseau et ne modifie aucun fichier.
Il est destiné à être exécuté sur la machine du lab une fois un accès
shell obtenu.

Il :
  - affiche l'utilisateur courant ;
  - vérifie les artefacts Nexus importants ;
  - lit les emplacements classiques user.txt/root.txt ;
  - recherche des candidats de flags dans quelques répertoires HTB.

Usage:
    python3 nexus_flag_poc.py
"""

from pathlib import Path
import re
import subprocess

FLAG_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])")

KNOWN = [
    Path("/home/jones/user.txt"),
    Path("/root/root.txt"),
]

SEARCH_ROOTS = [
    Path("/home"),
    Path("/root"),
    Path("/tmp"),
    Path("/var/tmp"),
]

MAX_SIZE = 1024 * 1024


def cmd(args):
    try:
        p = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return p.stdout.strip()
    except Exception:
        return ""


def read_candidate(path):
    try:
        if not path.is_file() or path.stat().st_size > MAX_SIZE:
            return None
        data = path.read_text(errors="replace").strip()
        match = FLAG_RE.search(data)
        return match.group(0) if match else None
    except (OSError, PermissionError):
        return None


def main():
    print("=" * 64)
    print("NEXUS HTB — FLAG POC")
    print("=" * 64)

    print("\n[+] Identity")
    print("    whoami:", cmd(["whoami"]))
    print("    id    :", cmd(["id"]))

    print("\n[+] Nexus artifacts")
    artifacts = [
        "/etc/systemd/system/gitea-template-sync.timer",
        "/etc/systemd/system/gitea-template-sync.service",
        "/etc/gitea/template-sync.py",
        "/var/log/template-sync.log",
    ]

    for item in artifacts:
        p = Path(item)
        print(("    [+] " if p.exists() else "    [-] ") + item)

    print("\n[+] Known flag locations")
    found = {}

    for path in KNOWN:
        flag = read_candidate(path)
        if flag:
            label = "USER FLAG" if path.name == "user.txt" else "ROOT FLAG"
            found[label] = flag
            print(f"    [+] {label}: {flag}")
        else:
            print(f"    [-] Not readable/not found: {path}")

    print("\n[+] Candidate discovery")
    candidates = {}

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        try:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue

                flag = read_candidate(path)
                if not flag:
                    continue

                name = path.name.lower()
                if (
                    name in {"user.txt", "root.txt"}
                    or "flag" in name
                    or FLAG_RE.fullmatch(flag)
                ):
                    candidates[str(path)] = flag

        except (OSError, PermissionError):
            continue

    for path, flag in sorted(candidates.items()):
        print(f"    [+] {path}: {flag}")

    print("\n" + "=" * 64)
    print("FLAGS")
    print("=" * 64)

    all_flags = set(found.values()) | set(candidates.values())

    if all_flags:
        for flag in sorted(all_flags):
            print(flag)
    else:
        print("No readable 32-hex flag found.")

    print("=" * 64)


if __name__ == "__main__":
    main()
