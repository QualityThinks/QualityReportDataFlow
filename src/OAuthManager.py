import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request


class OAuthError(RuntimeError):
    """An OAuth 2.0 request to Google failed.

    `error_code` holds Google's error string (e.g. "invalid_grant") when there
    is one, so callers can react to specific failures.
    """

    def __init__(self, message: str, error_code: str = ""):
        super().__init__(message)
        self.error_code = error_code


class OAuthManager:
    """OAuth 2.0 tokens for Gmail SMTP login (XOAUTH2), so no app password is needed.

    The client ID/secret belong to a "Desktop app" OAuth client created in the
    Google Cloud console; use OAuthManagerFactory to build an instance from an
    EnvManager. Each run swaps the long-lived refresh token for a short-lived
    access token, which EmailManager sends to smtp.gmail.com:

        oauth = OAuthManagerFactory.from_env(env, encryption)
        access_token = oauth.get_access_token()

    The refresh token comes from a one-time sign-in in the browser:
        python script\\create_oauth_token.py

    Only Google's OAuth endpoints are called. This does not use the Gmail API.
    """

    #region CONSTANTS
    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_SCOPE = "https://mail.google.com/"  # the scope Gmail requires for SMTP
    EXPIRY_MARGIN_SECONDS = 60  # refresh a bit before the token actually expires
    #endregion

    #region FIELDS
    __client_id: str
    __client_secret: str
    __refresh_token: str
    __timeout: int
    __access_token: str
    __expires_at: float
    #endregion

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str = "",
        timeout: int = 30,
    ):
        """Create a manager for one OAuth client and (optionally) its refresh token."""
        if not client_id:
            raise ValueError("client_id is required.")
        if not client_secret:
            raise ValueError("client_secret is required.")

        self.__client_id = client_id
        self.__client_secret = client_secret
        self.__refresh_token = refresh_token
        self.__timeout = int(timeout)
        self.__access_token = ""
        self.__expires_at = 0.0

    #region ACCESS TOKEN
    def get_access_token(self) -> str:
        """Return a valid access token, refreshing it when missing or about to expire."""
        if not self.__access_token or time.monotonic() >= self.__expires_at:
            self.refresh_access_token()
        return self.__access_token

    def refresh_access_token(self) -> str:
        """Swap the refresh token for a new access token (valid for about an hour)."""
        if not self.__refresh_token:
            raise OAuthError(
                "No refresh token configured. Run script\\create_oauth_token.py "
                "and set OAUTH_REFRESH_TOKEN in .env."
            )
        payload = self.__request_token({
            "grant_type": "refresh_token",
            "refresh_token": self.__refresh_token,
            "client_id": self.__client_id,
            "client_secret": self.__client_secret,
        })
        self.__store_access_token(payload)
        return self.__access_token
    #endregion

    #region ONE-TIME AUTHORIZATION (used by script/create_oauth_token.py)
    @staticmethod
    def create_pkce_pair() -> tuple[str, str]:
        """Return (code_verifier, code_challenge) for PKCE with S256."""
        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return verifier, challenge

    def build_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        code_challenge: str,
        login_hint: str | None = None,
    ) -> str:
        """URL of Google's consent page asking for Gmail SMTP access."""
        params = {
            "client_id": self.__client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.GMAIL_SCOPE,
            "access_type": "offline",  # ask for a refresh token
            "prompt": "consent",  # return a refresh token even if access was granted before
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        if login_hint:
            params["login_hint"] = login_hint
        return f"{self.AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str) -> str:
        """Swap the code from the consent redirect for tokens. Returns the refresh token."""
        payload = self.__request_token({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.__client_id,
            "client_secret": self.__client_secret,
            "code_verifier": code_verifier,
        })

        granted = str(payload.get("scope", "")).split()
        if self.GMAIL_SCOPE not in granted:
            raise OAuthError(
                f"Gmail access was not granted (granted: {', '.join(granted) or 'nothing'}). "
                "Run the script again and allow access to Gmail on the consent screen.",
                "insufficient_scope",
            )
        refresh_token = payload.get("refresh_token")
        if not refresh_token:
            raise OAuthError(
                "Google did not return a refresh token. Remove the app at "
                "https://myaccount.google.com/permissions and run the script again.",
                "no_refresh_token",
            )

        self.__refresh_token = refresh_token
        self.__store_access_token(payload)
        return refresh_token
    #endregion

    #region HELPERS
    def __store_access_token(self, payload: dict) -> None:
        access_token = payload.get("access_token")
        if not access_token:
            raise OAuthError("Google's token response did not contain an access token.")
        lifetime = int(payload.get("expires_in", 3600))
        self.__access_token = access_token
        self.__expires_at = time.monotonic() + max(0, lifetime - self.EXPIRY_MARGIN_SECONDS)

    def __request_token(self, form: dict) -> dict:
        """POST a form to Google's token endpoint and return the JSON response."""
        request = urllib.request.Request(
            self.TOKEN_URL,
            data=urllib.parse.urlencode(form).encode("ascii"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.__timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            error_code, description = self.__read_error(error)
            message = self.__explain(form["grant_type"], error_code, description, error.code)
            raise OAuthError(message, error_code) from error
        except OSError as error:  # URLError, timeouts, connection resets
            reason = getattr(error, "reason", error)
            raise OAuthError(
                f"Could not reach {self.TOKEN_URL}: {reason}. "
                "Check the internet connection (and proxy settings, if any)."
            ) from error
        except ValueError as error:  # the response was not JSON
            raise OAuthError(f"Unexpected non-JSON response from {self.TOKEN_URL}.") from error

        if not isinstance(payload, dict):
            raise OAuthError(f"Unexpected response from {self.TOKEN_URL}.")
        return payload

    @staticmethod
    def __read_error(error: urllib.error.HTTPError) -> tuple[str, str]:
        """Return Google's (error, error_description), or empty strings if unreadable."""
        try:
            body = json.loads(error.read().decode("utf-8", "replace"))
        except (OSError, ValueError):
            return "", ""
        if not isinstance(body, dict):
            return "", ""
        return str(body.get("error", "")), str(body.get("error_description", ""))

    @staticmethod
    def __explain(grant_type: str, error_code: str, description: str, status: int) -> str:
        """Turn a token endpoint error into a message that says what to do next."""
        detail = ": ".join(part for part in (error_code, description) if part) or f"HTTP {status}"
        if error_code in ("invalid_client", "unauthorized_client"):
            return (
                f"Google rejected the OAuth client ({detail}). Check OAUTH_CLIENT_ID and "
                "OAUTH_CLIENT_SECRET in .env, and that the client still exists in the "
                "Google Cloud console."
            )
        if error_code == "invalid_grant" and grant_type == "refresh_token":
            return (
                f"Google rejected the refresh token ({detail}). Run "
                "script\\create_oauth_token.py again and update OAUTH_REFRESH_TOKEN in .env. "
                "If this happens every 7 days, publish the app (Google Auth platform > "
                "Audience > Publish app)."
            )
        if error_code == "invalid_grant":
            return (
                f"Google rejected the sign-in code ({detail}). Run the script again and "
                "finish signing in within a few minutes."
            )
        return f"Google's token endpoint returned an error ({detail})."
    #endregion


class OAuthManagerFactory:
    """Logic layer: reads the OAuth client and refresh token from an EnvManager."""

    @staticmethod
    def from_env(env, encryption, require_refresh_token: bool = True) -> OAuthManager:
        """Build an OAuthManager from an EnvManager and an EncryptionManager.

        Expects these .env keys:
            OAUTH_CLIENT_ID       client ID of the "Desktop app" OAuth client
            OAUTH_CLIENT_SECRET   its client secret, encrypted with script/encrypt_value.py
            OAUTH_REFRESH_TOKEN   encrypted, printed by script/create_oauth_token.py
                                  (skipped when require_refresh_token=False)
        """
        client_id = env.require("OAUTH_CLIENT_ID")
        client_secret = encryption.decrypt_text(env.require("OAUTH_CLIENT_SECRET"))
        refresh_token = ""
        if require_refresh_token:
            refresh_token = encryption.decrypt_text(env.require("OAUTH_REFRESH_TOKEN"))
        return OAuthManager(client_id, client_secret, refresh_token)
