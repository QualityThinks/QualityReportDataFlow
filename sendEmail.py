"""Send .eml files produced by fetchMySql.py.

Usage examples:
    python sendEmail.py                      # send every .eml in ./output
    python sendEmail.py --latest             # send only the newest .eml in ./output
    python sendEmail.py path\\to\\file.eml    # send specific file(s) or folder(s)
    python sendEmail.py --method outlook     # send through the local Outlook client
    python sendEmail.py --dry-run            # show what would be sent

Successfully sent files are moved to ./output/sent so they are not sent twice
(use --keep to leave them in place).
"""

import argparse
import os
import shutil
import smtplib
import socket
import ssl
import sys
import tempfile
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formatdate, getaddresses, make_msgid
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_SOURCE_DIR = BASE_DIR / "output"
SENT_DIR_NAME = "sent"


def get_env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if value is not None:
        value = value.strip()
    if required and not value:
        raise RuntimeError(
            f"{name} environment variable has not been configured. "
            f"Add it to {BASE_DIR / '.env'}"
        )
    return value


# --------------------------------------------------------------------------- #
# Loading .eml files
# --------------------------------------------------------------------------- #
def collect_eml_files(sources, latest_only):
    """Resolve CLI arguments (files and/or folders) into a list of .eml paths."""
    files = []
    for source in sources:
        path = Path(source).resolve()
        if path.is_dir():
            # Only the folder itself, not ./sent, to avoid re-sending.
            files.extend(sorted(path.glob("*.eml")))
        elif path.is_file() and path.suffix.lower() == ".eml":
            files.append(path)
        else:
            print(f"Skipping '{source}': not an .eml file or folder.")

    # Remove duplicates while keeping order.
    files = list(dict.fromkeys(files))

    if latest_only and files:
        files = [max(files, key=lambda p: p.stat().st_mtime)]

    return files


def load_eml(eml_path):
    with open(eml_path, "rb") as eml_file:
        return BytesParser(policy=policy.default).parse(eml_file)


def get_recipients(message):
    """Return every address in To/Cc/Bcc."""
    headers = []
    for field in ("To", "Cc", "Bcc"):
        headers.extend(message.get_all(field, []))
    return [address for _, address in getaddresses(headers) if address]


def refresh_headers(message):
    """Update Date to the actual send time and make sure a Message-ID exists."""
    del message["Date"]
    message["Date"] = formatdate(localtime=True)
    if not message["Message-ID"]:
        message["Message-ID"] = make_msgid()


# --------------------------------------------------------------------------- #
# SMTP sender
# --------------------------------------------------------------------------- #
class SmtpSender:
    def __init__(self):
        self.host = get_env("SMTP_HOST", required=True)
        self.port = int(get_env("SMTP_PORT", "587"))
        self.security = get_env("SMTP_SECURITY", "starttls").lower()
        self.user = get_env("SMTP_USER", "")
        self.password = get_env("SMTP_PASSWORD", "")
        self.timeout = int(get_env("SMTP_TIMEOUT", "30"))
        self.server = None

        if self.security not in ("starttls", "ssl", "none"):
            raise RuntimeError("SMTP_SECURITY must be 'starttls', 'ssl' or 'none'.")

    def __enter__(self):
        context = ssl.create_default_context()

        if self.security == "ssl":
            self.server = smtplib.SMTP_SSL(
                self.host, self.port, timeout=self.timeout, context=context
            )
        else:
            self.server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            self.server.ehlo()
            if self.security == "starttls":
                self.server.starttls(context=context)
                self.server.ehlo()

        if self.user:
            self.server.login(self.user, self.password)

        print(f"Connected to SMTP server {self.host}:{self.port} ({self.security}).")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.server is not None:
            try:
                self.server.quit()
            except smtplib.SMTPException:
                self.server.close()

    def send(self, message: EmailMessage):
        refresh_headers(message)
        # send_message reads From/To/Cc/Bcc and strips Bcc before transmitting.
        refused = self.server.send_message(message)
        if refused:
            print(f"  Some recipients were refused: {refused}")


# --------------------------------------------------------------------------- #
# Outlook sender (Windows + Outlook desktop, requires pywin32)
# --------------------------------------------------------------------------- #
class OutlookSender:
    OL_MAIL_ITEM = 0
    OL_TO, OL_CC, OL_BCC = 1, 2, 3

    def __enter__(self):
        try:
            import win32com.client  # noqa: WPS433 (optional dependency)
        except ImportError as error:
            raise RuntimeError(
                "Outlook sending requires pywin32. Install it with: pip install pywin32"
            ) from error

        self.outlook = win32com.client.Dispatch("Outlook.Application")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="eml_attachments_"))
        print("Connected to Outlook.")
        return self

    def __exit__(self, exc_type, exc, tb):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _find_account(self, sender_address):
        """Return the Outlook account matching the .eml From address, if any."""
        if not sender_address:
            return None
        for account in self.outlook.Session.Accounts:
            if str(account.SmtpAddress).lower() == sender_address.lower():
                return account
        return None

    def send(self, message: EmailMessage):
        mail = self.outlook.CreateItem(self.OL_MAIL_ITEM)
        mail.Subject = str(message.get("Subject", ""))

        for field, recipient_type in (
            ("To", self.OL_TO),
            ("Cc", self.OL_CC),
            ("Bcc", self.OL_BCC),
        ):
            for _, address in getaddresses(message.get_all(field, [])):
                if address:
                    mail.Recipients.Add(address).Type = recipient_type

        if not mail.Recipients.ResolveAll():
            raise RuntimeError("Outlook could not resolve one or more recipients.")

        html_part = message.get_body(preferencelist=("html",))
        text_part = message.get_body(preferencelist=("plain",))
        if html_part is not None:
            mail.HTMLBody = html_part.get_content()
        elif text_part is not None:
            mail.Body = text_part.get_content()

        # Outlook needs attachments on disk.
        message_dir = Path(tempfile.mkdtemp(dir=self.temp_dir))
        for index, part in enumerate(message.iter_attachments(), start=1):
            filename = Path(part.get_filename() or f"attachment_{index}").name
            attachment_path = message_dir / filename
            attachment_path.write_bytes(part.get_payload(decode=True) or b"")
            mail.Attachments.Add(str(attachment_path))

        _, sender_address = getaddresses([message.get("From", "")])[0]
        account = self._find_account(sender_address)
        if account is not None:
            # SendUsingAccount is an object property; with late-bound COM a plain
            # assignment fails, so call PROPERTYPUTREF (8) on its DISPID (64209).
            mail._oleobj_.Invoke(64209, 0, 8, 0, account)
        elif sender_address:
            print(
                f"  No Outlook account matches {sender_address}; "
                "using the default Outlook account."
            )

        mail.Send()


# --------------------------------------------------------------------------- #
# Main flow
# --------------------------------------------------------------------------- #
def move_to_sent(eml_path):
    sent_dir = eml_path.parent / SENT_DIR_NAME
    sent_dir.mkdir(parents=True, exist_ok=True)
    destination = sent_dir / eml_path.name
    counter = 1
    while destination.exists():
        destination = sent_dir / f"{eml_path.stem}_{counter:03d}{eml_path.suffix}"
        counter += 1
    shutil.move(str(eml_path), str(destination))
    return destination


def parse_args():
    parser = argparse.ArgumentParser(description="Send .eml files automatically.")
    parser.add_argument(
        "sources",
        nargs="*",
        default=[str(DEFAULT_SOURCE_DIR)],
        help=".eml files or folders containing .eml files (default: ./output)",
    )
    parser.add_argument(
        "--method",
        choices=("smtp", "outlook"),
        default=(get_env("EMAIL_SEND_METHOD", "smtp") or "smtp").lower(),
        help="Delivery method (default: EMAIL_SEND_METHOD from .env, or smtp)",
    )
    parser.add_argument("--latest", action="store_true", help="Send only the newest .eml")
    parser.add_argument("--keep", action="store_true", help="Do not move sent files")
    parser.add_argument("--dry-run", action="store_true", help="List emails without sending")
    return parser.parse_args()


def main():
    args = parse_args()
    eml_files = collect_eml_files(args.sources, args.latest)

    if not eml_files:
        print("No .eml files found. Nothing to send.")
        return 0

    # Validate everything first so a bad file doesn't stop the batch mid-way.
    jobs = []
    for eml_path in eml_files:
        try:
            message = load_eml(eml_path)
        except Exception as error:  # noqa: BLE001
            print(f"Skipping {eml_path.name}: could not parse ({error}).")
            continue

        recipients = get_recipients(message)
        if not recipients:
            print(f"Skipping {eml_path.name}: no recipients in To/Cc/Bcc.")
            continue

        jobs.append((eml_path, message, recipients))

    if args.dry_run:
        for eml_path, message, recipients in jobs:
            print(
                f"[dry-run] {eml_path.name}: subject='{message.get('Subject', '')}', "
                f"to={', '.join(recipients)}, "
                f"attachments={len(list(message.iter_attachments()))}"
            )
        return 0

    if not jobs:
        print("No valid .eml files to send.")
        return 1

    sender_class = SmtpSender if args.method == "smtp" else OutlookSender
    sent_count = 0
    failed_count = 0

    try:
        with sender_class() as sender:
            for eml_path, message, recipients in jobs:
                try:
                    sender.send(message)
                    sent_count += 1
                    print(f"Sent {eml_path.name} -> {', '.join(recipients)}")
                    if not args.keep:
                        print(f"  Moved to {move_to_sent(eml_path)}")
                except Exception as error:  # noqa: BLE001
                    failed_count += 1
                    print(f"Failed to send {eml_path.name}: {error}")
    except smtplib.SMTPAuthenticationError:
        print("SMTP authentication failed. Check SMTP_USER / SMTP_PASSWORD.")
        return 1
    except socket.gaierror:
        print(
            f"Cannot resolve SMTP_HOST '{get_env('SMTP_HOST', '')}'. "
            "Set it to your real mail server in .env (e.g. smtp.office365.com), "
            "or use --method outlook."
        )
        return 1
    except (ConnectionRefusedError, TimeoutError, socket.timeout):
        print(
            f"Could not connect to {get_env('SMTP_HOST', '')}:{get_env('SMTP_PORT', '')}. "
            "Check SMTP_PORT/SMTP_SECURITY, or whether a firewall blocks the port."
        )
        return 1
    except Exception as error:  # noqa: BLE001
        print(f"Could not start the {args.method} sender: {error}")
        return 1

    print(f"Done. Sent: {sent_count}, failed: {failed_count}.")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
