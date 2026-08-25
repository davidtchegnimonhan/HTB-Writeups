# Reactor

Hack The Box write-up and proof of concept for the **Reactor** machine.

## Attack path

```text
Next.js 15.0.3
      │
      ▼
React2Shell RCE
      │
      ▼
node
      │
      ▼
SQLite database
      │
      ▼
MD5 password → engineer
      │
      ▼
SSH
      │
      ▼
Node.js Inspector :9229
      │
      ▼
Runtime.evaluate()
      │
      ▼
root
```

## Contents

- [`PoC/Reactor-PoC.md`](PoC/Reactor-PoC.md) — concise exploitation proof
- [`PoC/node_inspector_poc.py`](PoC/node_inspector_poc.py) — dependency-free Node Inspector PoC
- [`Writeup/Reactor-Writeup.md`](Writeup/Reactor-Writeup.md) — full walkthrough

> This repository documents an authorized Hack The Box lab.
