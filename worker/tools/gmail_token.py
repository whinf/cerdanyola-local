#!/usr/bin/env python3
"""Obtiene un refresh token de Gmail (scope gmail.send) con OAuth2 + PKCE. Solo stdlib.

Uso (una sola vez):
    python tools/gmail_token.py CLIENT_ID CLIENT_SECRET

Abre el navegador, recibe el código en http://127.0.0.1:PUERTO/ y lo cambia por tokens.
Imprime el refresh token y los comandos para guardarlo como secreto del worker.
"""

import base64
import hashlib
import http.server
import json
import secrets
import socket
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/gmail.send"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    client_id, client_secret = sys.argv[1], sys.argv[2]

    # PKCE S256
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    port = free_port()
    redirect_uri = f"http://127.0.0.1:{port}/"

    result: dict = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):  # silencio
            pass

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            ok = q.get("state", [""])[0] == state and "code" in q
            if ok:
                result["code"] = q["code"][0]
            else:
                result["error"] = q.get("error", ["sin código"])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Listo. Ya puedes cerrar esta pestaña." if ok else "Error: " + result["error"]
            self.wfile.write(f"<!doctype html><meta charset=utf-8><p>{msg}</p>".encode())
            done.set()

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(params)
    print("Abriendo el navegador para autorizar el envío de correo…")
    print("Si no se abre, copia esta URL:\n" + url + "\n")
    webbrowser.open(url)

    done.wait(timeout=600)
    server.shutdown()
    if "code" not in result:
        print("No se recibió el código:", result.get("error", "tiempo agotado"))
        return 1

    data = urllib.parse.urlencode(
        {
            "code": result["code"],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
    ).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req) as r:
        tokens = json.load(r)
    refresh = tokens.get("refresh_token")
    if not refresh:
        print("Google no devolvió refresh_token. Revoca el acceso en https://myaccount.google.com/permissions y repite.")
        return 1

    print("\nRefresh token (guárdalo como secreto, no lo subas a git):\n")
    print(refresh)
    print(
        "\nAhora, desde la carpeta worker/, ejecuta cada comando y pega el valor cuando lo pida:\n"
        "  npx wrangler secret put GMAIL_CLIENT_ID       (el client id)\n"
        "  npx wrangler secret put GMAIL_CLIENT_SECRET   (el client secret)\n"
        "  npx wrangler secret put GMAIL_REFRESH_TOKEN   (el refresh token de arriba)\n"
        "  npx wrangler secret put GMAIL_FROM            (la dirección Gmail que envía)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
