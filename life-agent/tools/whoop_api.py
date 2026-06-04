import os
import json
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import requests
import secrets

WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_BASE_URL = "https://api.prod.whoop.com/developer/v2"
TOKEN_FILE = ".whoop_token.json"


class _CallbackHandler(BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        _CallbackHandler.code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Login gelukt! Sluit dit venster.")

    def log_message(self, *args):
        pass


def _run_server(server):
    server.handle_request()


def _load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None


def _save_token(token: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)


def authenticate():
    client_id = os.environ["WHOOP_CLIENT_ID"]
    client_secret = os.environ["WHOOP_CLIENT_SECRET"]
    redirect_uri = os.environ["WHOOP_REDIRECT_URI"]

    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "offline read:recovery read:sleep read:workout read:cycles read:body_measurement",
        "state": state,
    }
    auth_url = f"{WHOOP_AUTH_URL}?{urlencode(params)}"

    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    t = threading.Thread(target=_run_server, args=(server,))
    t.start()

    print("Browser openen voor Whoop login...")
    webbrowser.open(auth_url)
    t.join()

    code = _CallbackHandler.code
    if not code:
        raise RuntimeError("Geen autorisatiecode ontvangen van Whoop.")

    resp = requests.post(WHOOP_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    resp.raise_for_status()
    token = resp.json()
    _save_token(token)
    print("Whoop authenticatie geslaagd.")
    return token


def _refresh_token(token: dict) -> dict:
    resp = requests.post(WHOOP_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
        "client_id": os.environ["WHOOP_CLIENT_ID"],
        "client_secret": os.environ["WHOOP_CLIENT_SECRET"],
    })
    resp.raise_for_status()
    new_token = resp.json()
    _save_token(new_token)
    return new_token


def get_headers() -> dict:
    token = _load_token()
    if not token:
        token = authenticate()

    resp = requests.get(f"{WHOOP_BASE_URL}/cycle",
                        headers={"Authorization": f"Bearer {token['access_token']}"},
                        params={"limit": 1})
    if resp.status_code == 401:
        token = _refresh_token(token)

    return {"Authorization": f"Bearer {token['access_token']}"}


def get_latest_recovery() -> dict:
    headers = get_headers()
    resp = requests.get(f"{WHOOP_BASE_URL}/recovery", headers=headers,
                        params={"limit": 1})
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    records = resp.json().get("records", [])
    return records[0] if records else {}


def get_latest_sleep() -> dict:
    headers = get_headers()
    resp = requests.get(f"{WHOOP_BASE_URL}/activity/sleep", headers=headers,
                        params={"limit": 1})
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    records = resp.json().get("records", [])
    return records[0] if records else {}


def get_todays_strain() -> dict:
    headers = get_headers()
    resp = requests.get(f"{WHOOP_BASE_URL}/cycle", headers=headers,
                        params={"limit": 1})
    resp.raise_for_status()
    records = resp.json().get("records", [])
    return records[0] if records else {}
