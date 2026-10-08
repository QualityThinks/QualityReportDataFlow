import mimetypes
import re
import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from OAuthManager import OAuthManagerFactory


class EmailManager:
    """Build and send a single HTML email over SMTP.

    SMTP settings are passed in through the constructor (not read from the
    environment here); use EmailManagerFactory to build an instance from an
    EnvManager. The object holds the message state; configure it with the
    set_* / add_* methods (which chain) and then call send():

        email = EmailManagerFactory.from_env(env, encryption)
        email.set_subject("Quality Report")
        email.set_body("<h1>Hello</h1><p>See attached.</p>")
        email.add_to("someone@example.com")
        email.attach_file("output/report.xlsx")
        email.send()

    Login (smtp_auth):
        "password"  SMTP AUTH with smtp_user / smtp_password (skipped if no user)
        "oauth2"    SMTP AUTH XOAUTH2 with smtp_user and an access token from
                    oauth_token_provider (e.g. OAuthManager.get_access_token).
                    This is how Gmail works without an app password.
    """

    #region CONSTANTS
    EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    VALID_SECURITIES = ("starttls", "ssl", "none")
    VALID_AUTHS = ("password", "oauth2")
    #endregion

    #region FIELDS
    __sender: str
    __to: list[str]
    __cc: list[str]
    __bcc: list[str]
    __subject: str
    __html_body: str
    __attachments: list[Path]
    __smtp_host: str
    __smtp_port: int
    __smtp_security: str
    __smtp_user: str
    __smtp_password: str
    __smtp_timeout: int
    __smtp_auth: str
    __oauth_token_provider: Callable[[], str] | None
    #endregion

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        smtp_security: str = "starttls",
        smtp_user: str = "",
        smtp_password: str = "",
        smtp_timeout: int = 30,
        sender: str = "",
        smtp_auth: str = "password",
        oauth_token_provider: Callable[[], str] | None = None,
    ):
        """Create an empty message with explicit SMTP settings."""
        if not smtp_host:
            raise ValueError("smtp_host is required.")

        security = (smtp_security or "starttls").lower()
        if security not in self.VALID_SECURITIES:
            raise ValueError(
                f"smtp_security must be one of {self.VALID_SECURITIES}, got '{smtp_security}'."
            )

        auth = (smtp_auth or "password").lower()
        if auth not in self.VALID_AUTHS:
            raise ValueError(f"smtp_auth must be one of {self.VALID_AUTHS}, got '{smtp_auth}'.")
        if auth == "oauth2" and not smtp_user:
            raise ValueError("smtp_user is required for oauth2 (the account that granted access).")
        if auth == "oauth2" and oauth_token_provider is None:
            raise ValueError("oauth_token_provider is required for oauth2.")

        self.__smtp_host = smtp_host
        self.__smtp_port = int(smtp_port)
        self.__smtp_security = security
        self.__smtp_user = smtp_user
        self.__smtp_password = smtp_password
        self.__smtp_timeout = int(smtp_timeout)
        self.__smtp_auth = auth
        self.__oauth_token_provider = oauth_token_provider

        self.__sender = self.__validate(sender) if sender else ""
        self.__to = []
        self.__cc = []
        self.__bcc = []
        self.__subject = ""
        self.__html_body = ""
        self.__attachments = []

    #region VALIDATION
    @classmethod
    def is_valid_email(cls, address: str) -> bool:
        """True if the address matches EMAIL_REGEX."""
        return bool(cls.EMAIL_REGEX.match(address.strip())) if address else False

    @classmethod
    def __validate(cls, address: str) -> str:
        """Return the trimmed address, or raise if it fails the regex."""
        cleaned = address.strip()
        if not cls.is_valid_email(cleaned):
            raise ValueError(f"Invalid email address: '{address}'")
        return cleaned

    @classmethod
    def __validate_many(cls, value: str | list[str]) -> list[str]:
        """Split (if a string) and validate every address."""
        if isinstance(value, str):
            parts = [part for part in value.replace(";", ",").split(",")]
        else:
            parts = [str(item) for item in value]
        return [cls.__validate(part) for part in parts if part.strip()]
    #endregion

    #region SETTERS
    def set_sender(self, address: str) -> "EmailManager":
        self.__sender = self.__validate(address)
        return self

    def set_subject(self, subject: str) -> "EmailManager":
        self.__subject = subject
        return self

    def set_body(self, html_body: str) -> "EmailManager":
        """Set the HTML body of the email."""
        self.__html_body = html_body
        return self

    def set_to(self, addresses: str | list[str]) -> "EmailManager":
        self.__to = self.__validate_many(addresses)
        return self

    def set_cc(self, addresses: str | list[str]) -> "EmailManager":
        self.__cc = self.__validate_many(addresses)
        return self

    def set_bcc(self, addresses: str | list[str]) -> "EmailManager":
        self.__bcc = self.__validate_many(addresses)
        return self

    def add_to(self, address: str) -> "EmailManager":
        self.__to.append(self.__validate(address))
        return self

    def add_cc(self, address: str) -> "EmailManager":
        self.__cc.append(self.__validate(address))
        return self

    def add_bcc(self, address: str) -> "EmailManager":
        self.__bcc.append(self.__validate(address))
        return self

    def attach_file(self, file_path: str | Path) -> "EmailManager":
        """Queue a file to be attached when the email is built/sent."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Attachment not found: {path}")
        self.__attachments.append(path)
        return self
    #endregion

    #region PROPERTIES
    @property
    def recipients(self) -> list[str]:
        """Every address the message is delivered to (To + Cc + Bcc)."""
        return [*self.__to, *self.__cc, *self.__bcc]
    #endregion

    #region BUILD / SEND
    def build_message(self) -> EmailMessage:
        """Assemble an EmailMessage from the current state."""
        if not self.__sender:
            raise RuntimeError("No sender set. Use set_sender() or pass sender= to the constructor.")
        if not self.recipients:
            raise RuntimeError("No recipients set. Use set_to()/add_to().")

        message = EmailMessage()
        message["From"] = self.__sender
        if self.__to:
            message["To"] = ", ".join(self.__to)
        if self.__cc:
            message["Cc"] = ", ".join(self.__cc)
        if self.__bcc:
            message["Bcc"] = ", ".join(self.__bcc)
        message["Subject"] = self.__subject
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid()

        # HTML body, with a minimal plain-text fallback for clients without HTML.
        message.set_content("This email requires an HTML-capable mail client.")
        message.add_alternative(self.__html_body or "", subtype="html")

        for path in self.__attachments:
            mime_type, _ = mimetypes.guess_type(path.name)
            maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
            message.add_attachment(
                path.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

        return message

    def send(self) -> None:
        """Build the message and send it over SMTP using the constructor settings."""
        message = self.build_message()
        server = self.__open_connection()
        try:
            # send_message reads From/To/Cc and strips Bcc; pass recipients
            # explicitly so Bcc addresses still receive the message.
            server.send_message(message, from_addr=self.__sender, to_addrs=self.recipients)
        finally:
            self.__close_connection(server)

    def verify_login(self) -> None:
        """Connect and log in without sending anything, to check the SMTP settings."""
        self.__close_connection(self.__open_connection())
    #endregion

    #region SMTP CONNECTION
    def __open_connection(self) -> smtplib.SMTP:
        """Connect, switch to TLS if configured, and log in (password or XOAUTH2)."""
        # Get the OAuth token before connecting, so a token problem fails
        # without leaving an SMTP connection open.
        access_token = self.__oauth_token_provider() if self.__smtp_auth == "oauth2" else None

        context = ssl.create_default_context()
        if self.__smtp_security == "ssl":
            server = smtplib.SMTP_SSL(
                self.__smtp_host, self.__smtp_port, timeout=self.__smtp_timeout, context=context
            )
        else:
            server = smtplib.SMTP(self.__smtp_host, self.__smtp_port, timeout=self.__smtp_timeout)
            # server.set_debuglevel(1)
        try:
            server.ehlo()
            if self.__smtp_security == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if access_token is not None:
                self.__login_xoauth2(server, access_token)
            elif self.__smtp_user:
                server.login(self.__smtp_user, self.__smtp_password)
        except BaseException:
            self.__close_connection(server)
            raise
        return server

    def __login_xoauth2(self, server: smtplib.SMTP, access_token: str) -> None:
        """SMTP AUTH XOAUTH2: log in with an OAuth access token instead of a password."""
        offered = server.esmtp_features.get("auth", "").upper().split()
        if "XOAUTH2" not in offered:
            raise smtplib.SMTPNotSupportedError(
                f"{self.__smtp_host} does not offer XOAUTH2 login "
                f"(offers: {', '.join(offered) or 'no AUTH'}). For Gmail use port 587 "
                "with SMTP_SECURITY=starttls, or port 465 with ssl."
            )

        auth_string = f"user={self.__smtp_user}\x01auth=Bearer {access_token}\x01\x01"
        try:
            # smtplib calls this once for the initial response, then again with
            # the server's error challenge; answering that with "" makes the
            # server return its final 535 instead of waiting.
            server.auth("XOAUTH2", lambda challenge=None: auth_string if challenge is None else "")
        except smtplib.SMTPAuthenticationError as error:
            reply = error.smtp_error
            if isinstance(reply, bytes):
                reply = reply.decode("utf-8", "replace")
            raise smtplib.SMTPAuthenticationError(
                error.smtp_code,
                f"{' '.join(str(reply).split())} | OAuth login for {self.__smtp_user} was "
                "rejected. The token must come from signing in as this account with Gmail "
                "access allowed: run script\\create_oauth_token.py again.",
            ) from error

    @staticmethod
    def __close_connection(server: smtplib.SMTP) -> None:
        try:
            server.quit()
        except OSError:  # includes SMTPException; never hide the original error
            server.close()
    #endregion


class EmailManagerFactory:
    """Logic layer: reads SMTP settings from an EnvManager and builds an EmailManager."""

    @staticmethod
    def from_env(env, encryption) -> EmailManager:
        """Build an EmailManager from an EnvManager and an EncryptionManager.

        Expects these .env keys:
            SMTP_HOST, EMAIL_SENDER
            SMTP_PORT (587), SMTP_SECURITY (starttls), SMTP_TIMEOUT (30)
            SMTP_AUTH       oauth2 or password (default: password)
            SMTP_USER       login account; required for oauth2
            SMTP_PASSWORD   encrypted; only for SMTP_AUTH = password
            OAUTH_*         only for SMTP_AUTH = oauth2 (see OAuthManagerFactory)

        `encryption` decrypts the stored secrets (SMTP_PASSWORD / OAUTH_*).
        """
        auth = (env.get("SMTP_AUTH") or "password").lower()
        if auth not in EmailManager.VALID_AUTHS:
            raise ValueError(f"SMTP_AUTH must be one of {EmailManager.VALID_AUTHS}, got '{auth}'.")

        settings = {
            "smtp_host": env.require("SMTP_HOST"),
            "smtp_port": env.get_int("SMTP_PORT", 587),
            "smtp_security": env.get("SMTP_SECURITY", "starttls"),
            "smtp_timeout": env.get_int("SMTP_TIMEOUT", 30),
            "sender": env.require("EMAIL_SENDER"),
            "smtp_auth": auth,
        }
        if auth == "oauth2":
            smtp_user = env.require("SMTP_USER")
            oauth = OAuthManagerFactory.from_env(env, encryption)
            return EmailManager(
                smtp_user=smtp_user,
                oauth_token_provider=oauth.get_access_token,
                **settings,
            )
        return EmailManager(
            smtp_user=env.get("SMTP_USER", "") or "",
            smtp_password=encryption.decrypt_text(env.require("SMTP_PASSWORD")),
            **settings,
        )
