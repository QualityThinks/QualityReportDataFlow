"""One-time setup: sign in to Gmail with OAuth2 and print the refresh token
(encrypted) for .env, so the flow can send email without an app password.

Before running, in the Google Cloud console (https://console.cloud.google.com/):
    1. Create a project (any name).
    2. Menu > Google Auth platform > Get started: enter an app name and your
       email, choose audience "External", and finish.
    3. Google Auth platform > Audience: click "Publish app" so the status is
       "In production". While it is "Testing", the refresh token stops
       working after 7 days.
    4. Google Auth platform > Clients > Create client > Application type
       "Desktop app". Copy the Client ID and the Client secret right away:
       the secret is only shown once.
    You don't need to enable the Gmail API.

Then set these in .env:
    SMTP_USER           = your Gmail address
    OAUTH_CLIENT_ID     = the Client ID
    OAUTH_CLIENT_SECRET = the output of: python script\\encrypt_value.py "<client secret>"

Usage:
    python script\\create_oauth_token.py

Your browser opens Google's sign-in page. Sign in as SMTP_USER and allow
access. Google warns that the app isn't verified; it's your own app, so click
Advanced > Go to <app name>. The script then checks the SMTP login and prints
the lines to add to .env.
"""

import html
import secrets
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from EmailManager import EmailManager
from EncryptionManager import EncryptionManagerFactory
from EnvManager import EnvManager
from OAuthManager import OAuthManager, OAuthManagerFactory

WAIT_SECONDS = 300  # how long to wait for the sign-in in the browser


class CallbackServer(HTTPServer):
    """Local server on 127.0.0.1 that receives Google's redirect after sign-in."""

    callback_params: dict | None = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
        if "code" not in params and "error" not in params:
            self.send_error(404)  # e.g. the browser asking for /favicon.ico
            return

        self.server.callback_params = params
        if "code" in params:
            message = "Access granted."
        else:
            message = f"Sign-in failed: {html.escape(params['error'])}."
        body = (
            f"<html><body><h3>{message}</h3>"
            "<p>You can close this tab and go back to the terminal.</p></body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # keep the terminal output clean


def get_refresh_token(oauth: OAuthManager, smtp_user: str) -> str:
    """Open Google's consent page, wait for the redirect, and swap the code for tokens."""
    verifier, challenge = OAuthManager.create_pkce_pair()
    state = secrets.token_urlsafe(16)

    with CallbackServer(("127.0.0.1", 0), CallbackHandler) as server:
        server.timeout = 1  # handle_request() returns every second, so we can time out
        redirect_uri = f"http://127.0.0.1:{server.server_port}/"
        url = oauth.build_authorization_url(redirect_uri, state, challenge, login_hint=smtp_user)

        print("Opening your browser. If it doesn't open, paste this URL into it:\n")
        print(url)
        print(f"\nSign in as {smtp_user} and allow access. Waiting up to {WAIT_SECONDS // 60} minutes...")
        webbrowser.open(url)

        deadline = time.monotonic() + WAIT_SECONDS
        while server.callback_params is None and time.monotonic() < deadline:
            server.handle_request()
        params = server.callback_params

    if params is None:
        raise TimeoutError(f"No sign-in response within {WAIT_SECONDS // 60} minutes.")
    if params.get("state") != state:
        raise RuntimeError("The sign-in response doesn't match this request (state mismatch).")
    if "error" in params:
        raise RuntimeError(f"Google returned '{params['error']}'. Allow access on the consent screen.")
    return oauth.exchange_code(params["code"], redirect_uri, verifier)


def check_smtp_login(env: EnvManager, oauth: OAuthManager, smtp_user: str) -> None:
    """Log in to the SMTP server with the new token, without sending anything."""
    EmailManager(
        smtp_host=env.get("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=env.get_int("SMTP_PORT", 587),
        smtp_security=env.get("SMTP_SECURITY", "starttls"),
        smtp_user=smtp_user,
        smtp_timeout=env.get_int("SMTP_TIMEOUT", 30),
        smtp_auth="oauth2",
        oauth_token_provider=oauth.get_access_token,
    ).verify_login()


def main():
    try:
        env = EnvManager(PROJECT_ROOT / ".env")
        encryption = EncryptionManagerFactory.from_env(env)
        smtp_user = env.require("SMTP_USER")
        oauth = OAuthManagerFactory.from_env(env, encryption, require_refresh_token=False)
    except Exception as error:  # noqa: BLE001
        print(f"Could not load the OAuth settings: {type(error).__name__}: {error}")
        print("Set SMTP_USER, OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET (encrypted) in .env.")
        print("The setup steps are at the top of script\\create_oauth_token.py.")
        return 1

    print(f"Gmail OAuth2 setup for {smtp_user}\n")
    try:
        refresh_token = get_refresh_token(oauth, smtp_user)
    except Exception as error:  # noqa: BLE001
        print(f"\nSign-in failed: {type(error).__name__}: {error}")
        return 1

    print("\nAccess granted. Checking the SMTP login...")
    try:
        check_smtp_login(env, oauth, smtp_user)
    except Exception as error:  # noqa: BLE001
        print(f"SMTP login failed: {type(error).__name__}: {error}")
        print(f"Check that you signed in as {smtp_user}, and that SMTP_HOST / SMTP_PORT /")
        print("SMTP_SECURITY are smtp.gmail.com / 587 / starttls. Then run this script again.")
        return 1

    print("SMTP login OK.\n")
    print("Add these to your .env:\n")
    print("SMTP_AUTH = oauth2")
    print(f"OAUTH_REFRESH_TOKEN = {encryption.encrypt_text(refresh_token)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
