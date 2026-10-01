import mimetypes
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path


class EmailManager:
    """Build and send a single HTML email over SMTP.

    SMTP settings are passed in through the constructor (not read from the
    environment here); use EmailManagerFactory to build an instance from an
    EnvManager. The object holds the message state; configure it with the
    set_* / add_* methods (which chain) and then call send():

        email = EmailManagerFactory.from_env(env)
        email.set_subject("Quality Report")
        email.set_body("<h1>Hello</h1><p>See attached.</p>")
        email.add_to("someone@example.com")
        email.attach_file("output/report.xlsx")
        email.send()
    """

    #region CONSTANTS
    EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    VALID_SECURITIES = ("starttls", "ssl", "none")
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
    ):
        """Create an empty message with explicit SMTP settings."""
        if not smtp_host:
            raise ValueError("smtp_host is required.")

        security = (smtp_security or "starttls").lower()
        if security not in self.VALID_SECURITIES:
            raise ValueError(
                f"smtp_security must be one of {self.VALID_SECURITIES}, got '{smtp_security}'."
            )

        self.__smtp_host = smtp_host
        self.__smtp_port = int(smtp_port)
        self.__smtp_security = security
        self.__smtp_user = smtp_user
        self.__smtp_password = smtp_password
        self.__smtp_timeout = int(smtp_timeout)

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
        recipients = self.recipients

        context = ssl.create_default_context()
        if self.__smtp_security == "ssl":
            server = smtplib.SMTP_SSL(
                self.__smtp_host, self.__smtp_port, timeout=self.__smtp_timeout, context=context
            )
        else:
            server = smtplib.SMTP(self.__smtp_host, self.__smtp_port, timeout=self.__smtp_timeout)

        try:
            server.ehlo()
            if self.__smtp_security == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if self.__smtp_user:
                server.login(self.__smtp_user, self.__smtp_password)
            # send_message reads From/To/Cc and strips Bcc; pass recipients
            # explicitly so Bcc addresses still receive the message.
            server.send_message(message, from_addr=self.__sender, to_addrs=recipients)
        finally:
            try:
                server.quit()
            except smtplib.SMTPException:
                server.close()
    #endregion


class EmailManagerFactory:
    """Logic layer: reads SMTP settings from an EnvManager and builds an EmailManager."""

    @staticmethod
    def from_env(env) -> EmailManager:
        """Build an EmailManager from an EnvManager (or compatible object).

        Expects the same .env keys used by sendEmail.py:
            SMTP_HOST, SMTP_PORT, SMTP_SECURITY, SMTP_USER,
            SMTP_PASSWORD, SMTP_TIMEOUT, EMAIL_SENDER
        """
        return EmailManager(
            smtp_host=env.require("SMTP_HOST"),
            smtp_port=env.get_int("SMTP_PORT", 587),
            smtp_security=env.get("SMTP_SECURITY", "starttls"),
            smtp_user=env.get("SMTP_USER", "") or "",
            smtp_password=env.get("SMTP_PASSWORD", "") or "",
            smtp_timeout=env.get_int("SMTP_TIMEOUT", 30),
            sender=env.get("EMAIL_SENDER", "") or "",
        )
