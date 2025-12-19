from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from pathlib import Path
from string import Template

from smart_common.core.config import settings


TEMPLATES_DIR = Path(__file__).parent / "email_templates"


def send_email(
    *,
    recipient: str,
    subject: str,
    template_name: str,
    context: dict,
) -> None:
    """
    Generic email sender.

    :param recipient: email address
    :param subject: email subject
    :param template_name: HTML template filename
    :param context: dict injected into template
    """

    html_body = _render_template(template_name, context)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = recipient

    msg.attach(MIMEText(html_body, "html"))

    _send_smtp(msg)


def _render_template(template_name: str, context: dict) -> str:
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Email template not found: {template_name}")

    template = Template(template_path.read_text(encoding="utf-8"))
    return template.safe_substitute(context)


def _send_smtp(message: MIMEMultipart) -> None:
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_TLS:
            server.starttls()

        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.send_message(message)
