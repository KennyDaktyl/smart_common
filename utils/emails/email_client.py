from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import logging
from pathlib import Path
from string import Template

from smart_common.core.config import settings

logger = logging.getLogger(__name__)

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

    In development environment all emails are redirected
    to DEFAULT_EMAIL to prevent accidental delivery.
    """

    original_recipient = recipient

    # --------------------------------------------------
    # DEV REDIRECTION
    # --------------------------------------------------
    if settings.ENV.lower() == "development":
        if not settings.DEFAULT_EMAIL:
            raise RuntimeError("DEFAULT_EMAIL must be set in development")

        recipient = settings.DEFAULT_EMAIL
        subject = f"[DEV] {subject}"

        logger.info(
            "Email redirected in DEV mode: original=%s redirected_to=%s",
            original_recipient,
            recipient,
        )

    html_body = _render_template(template_name, context)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = recipient

    msg.attach(MIMEText(html_body, "html"))

    logger.info(
        "Sending email to=%s via %s:%s tls=%s ssl=%s",
        recipient,
        settings.EMAIL_HOST,
        settings.EMAIL_PORT,
        settings.EMAIL_USE_TLS,
        settings.EMAIL_USE_SSL,
    )

    _send_email_smtp(msg)


def _render_template(template_name: str, context: dict) -> str:
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Email template not found: {template_name}")

    template = Template(template_path.read_text(encoding="utf-8"))
    return template.safe_substitute(context)


def _send_email_smtp(message: MIMEMultipart) -> None:
    try:
        if settings.EMAIL_USE_SSL:
            server = smtplib.SMTP_SSL(
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                timeout=10,
            )
        else:
            server = smtplib.SMTP(
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                timeout=10,
            )

        with server:
            server.ehlo()

            if settings.EMAIL_USE_TLS:
                server.starttls()
                server.ehlo()

            if settings.EMAIL_USER:
                server.login(
                    settings.EMAIL_USER,
                    settings.EMAIL_PASSWORD.get_secret_value()
                    if settings.EMAIL_PASSWORD
                    else "",
                )

            server.send_message(message)

            logger.info("Email successfully sent to %s", message["To"])

    except Exception:
        logger.exception(
            "EMAIL SEND FAILED host=%s port=%s user=%s",
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
            settings.EMAIL_USER,
        )
        raise
