"""Send email over SMTP. With no SMTP_HOST set, emails are written to the log instead."""

import html as htmlmod
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

from app.config import settings

logger = logging.getLogger(__name__)


URL_LINE = re.compile(r"^\s*(https?://\S+)\s*$")
FOREST, CREAM, TURMERIC, INK, SOFT = "#0c3b2e", "#fff8ee", "#f8b62d", "#17251f", "#55625b"


def sender() -> str:
    """'Virundhu <address>' so inboxes show Virundhu as the sender (Gmail sends from the signed-in address)."""
    name, addr = parseaddr(settings.EMAIL_FROM)
    if not addr or "example.com" in addr or "yourdomain" in addr:
        addr = settings.SMTP_USER or addr
    return formataddr((name or "Virundhu", addr))


def _button_label(url: str) -> str:
    if "reset-password" in url:
        return "Choose a new password"
    if "/billing" in url or "pay" in url:
        return "Open plan and payment"
    if "/support" in url:
        return "Open your request"
    if "/join" in url or "invite" in url:
        return "Accept the invitation"
    if "/inbox" in url or "/alerts" in url:
        return "Open in Virundhu"
    return "Open Virundhu"


def branded_html(subject: str, text: str) -> str:
    """Turn a plain-text customer email into the Virundhu card: green header, paragraphs, turmeric buttons for links."""
    blocks: list[str] = []
    for para in re.split(r"\n\s*\n", text.strip()):
        lines = para.split("\n")
        if len(lines) == 1 and URL_LINE.match(lines[0]):
            url = htmlmod.escape(lines[0].strip(), quote=True)
            blocks.append(
                f'<p style="margin:22px 0"><a href="{url}" style="background:{TURMERIC};color:{INK};'
                f"text-decoration:none;font-weight:700;padding:12px 22px;border-radius:10px;"
                f'display:inline-block">{_button_label(url)}</a></p>'
            )
            continue
        safe = "<br>".join(htmlmod.escape(line) for line in lines)
        safe = re.sub(r"(https?://[^\s<]+)", rf'<a href="\1" style="color:{FOREST}">\1</a>', safe)
        blocks.append(f'<p style="margin:0 0 14px;line-height:1.6">{safe}</p>')
    site = settings.APP_URL.replace("https://", "").replace("http://", "")
    place = htmlmod.escape(settings.COMPANY_ADDRESS or "Coimbatore, Tamil Nadu")
    return (
        f'<!doctype html><html><body style="margin:0;background:{CREAM};font-family:Arial,Helvetica,sans-serif;'
        f'color:{INK}"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{CREAM};padding:24px 12px"><tr><td align="center">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;'
        f'background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #efdcbf">'
        f'<tr><td style="background:{FOREST};padding:20px 24px"><div style="color:{CREAM};font-size:22px;'
        f'font-weight:700">Virundhu</div><div style="color:{TURMERIC};font-size:13px;margin-top:2px">'
        f"Every guest, heard</div></td></tr>"
        f'<tr><td style="padding:24px;font-size:15px">'
        f'<div style="font-size:18px;font-weight:700;margin:0 0 16px">{htmlmod.escape(subject)}</div>'
        f"{''.join(blocks)}</td></tr>"
        f'<tr><td style="padding:14px 24px;border-top:1px solid #efdcbf;font-size:12px;color:{SOFT}">'
        f"Virundhu · {place} · {htmlmod.escape(site)}<br>You're getting this because you have a Virundhu "
        f"account or contacted us. Need help? Reply to this email or use Quick help on the site."
        f"</td></tr></table></td></tr></table></body></html>"
    )


def send_email(
    to: list[str],
    subject: str,
    text: str,
    html: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bool:
    """Send one email to several recipients. Returns True when sent (or logged in development).

    Customer emails get the branded Virundhu design automatically; emails to the platform admin stay plain.
    """
    recipients = sorted({r.strip().lower() for r in to if r and "@" in r})
    if not recipients:
        return False
    if html is None and settings.SUPERADMIN_EMAIL.lower() not in recipients:
        html = branded_html(subject, text)
    if not settings.SMTP_HOST:
        files = ", ".join(f[0] for f in attachments or [])
        logger.info("EMAIL (not sent, SMTP_HOST is empty) to=%s subject=%s %s\n%s", recipients, subject, files, text)
        return True
    msg = EmailMessage()
    msg["From"] = sender()
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    for filename, data, mime in attachments or []:
        main, _, sub = mime.partition("/")
        msg.add_attachment(data, maintype=main, subtype=sub, filename=filename)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception:
        logger.exception("Email to %s failed", recipients)
        return False
