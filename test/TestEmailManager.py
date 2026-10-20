import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from EnvManager import EnvManager
from EmailManager import EmailManager, EmailManagerFactory
from EncryptionManager import EncryptionManagerFactory

# Optional attachment: the report moved by TestFileManager.py (if present).
REPORT_XLSX = PROJECT_ROOT / "reports" / "2026" / "october" / "test_users.xlsx"

HTML_BODY = """\
<html>
  <body>
    <h2>Quality Report</h2>
    <p>Hello,</p>
    <p>Please find the latest quality report attached.</p>
    <p>Regards,<br>Automation</p>
  </body>
</html>
"""


def load_environment() -> EnvManager:
    return EnvManager(PROJECT_ROOT / ".env")


def main():
    print("TEST EMAIL MANAGER")

    # Quick check of the regex validation on the class constant.
    print("Regex check:")
    print(f"  good@example.com -> {EmailManager.is_valid_email('good@example.com')}")
    print(f"  bad@@example     -> {EmailManager.is_valid_email('bad@@example')}")

    env = load_environment()

    # Logic layer: read the Gmail OAuth2 settings from .env and build the
    # EmailManager. The factory decrypts the stored OAUTH_* secrets.
    try:
        encryption = EncryptionManagerFactory.from_env(env)
        email = EmailManagerFactory.from_env(env, encryption)
    except RuntimeError as error:
        print(f"Gmail is not configured: {error}")
        print("Add SMTP_USER and the OAUTH_* keys to .env (see .env.example) to run the send test.")
        return

    recipient = env.get("EMAIL_RECIPIENT")
    subject = env.get("EMAIL_SUBJECT", "Quality Report")

    if recipient:
        email.set_to(recipient)

    email.set_subject(subject)
    email.set_body(HTML_BODY)

    if REPORT_XLSX.is_file():
        email.attach_file(REPORT_XLSX)
        print(f"Attached: {REPORT_XLSX.name}")
    else:
        print(f"No attachment found at {REPORT_XLSX} (sending without attachment).")

    print(f"Recipients: {email.recipients}")

    try:
        email.send()
        print("Email sent.")
    except Exception as error:  # noqa: BLE001
        print(f"Could not send email: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
