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
    if "forgot-password" in url:
        return "It wasn't me: reset my password"
    if "verify-email" in url:
        return "Confirm my email"
    if "/billing" in url or "pay" in url:
        return "Open plan and payment"
    if "/support" in url:
        return "Open your request"
    if "/join" in url or "invite" in url:
        return "Accept the invitation"
    if "/inbox" in url or "/alerts" in url:
        return "Open in Virundhu"
    return "Open Virundhu"


QUOTES = (
    "“To welcome a guest with a warm face is the finest wealth a home can hold.” A thought from the Thirukkural, "
    "chapter on hospitality",
    "“A guest who leaves happy comes back, and brings two more.”",
    "“Good food fills the plate. Being heard fills the heart.”",
)


def closing_text() -> str:
    return "\n\nThank you so much,\nTeam Virundhu\n\n" + _quote() + "\n"


def _quote() -> str:
    from datetime import date

    return QUOTES[date.today().toordinal() % len(QUOTES)]


def _cell(content: str, pad: str = "0 28px") -> str:
    return f'<tr><td bgcolor="#ffffff" style="background:#ffffff;padding:{pad}">{content}</td></tr>'


def branded_html(
    subject: str,
    text: str,
    details: list[tuple[str, str]] | None = None,
) -> str:
    """The Virundhu email card: green header, greeting, message, details, a turmeric button, thanks and a quote.

    Built with tables, bgcolor attributes and inline styles so phone mail apps (Gmail, Outlook, Apple Mail) keep the
    colours. A line that is only a link becomes the button.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    paras = [p for p in paras if p not in ("- Virundhu", "Team Virundhu")]
    rows: list[str] = []
    for para in paras:
        lines = para.split("\n")
        if len(lines) == 1 and URL_LINE.match(lines[0]):
            url = htmlmod.escape(lines[0].strip(), quote=True)
            rows.append(
                _cell(
                    f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:6px 0 22px"><tr>'
                    f'<td bgcolor="{TURMERIC}" style="background:{TURMERIC};border-radius:10px">'
                    f'<a href="{url}" style="display:inline-block;padding:14px 26px;color:{INK};font-weight:700;'
                    f'font-size:16px;text-decoration:none">{_button_label(url)}</a></td></tr></table>'
                )
            )
            continue
        safe = "<br>".join(htmlmod.escape(line) for line in lines)
        safe = re.sub(r"(https?://[^\s<]+)", rf'<a href="\1" style="color:{FOREST}">\1</a>', safe)
        big = lines[0].startswith(("Hi ", "Welcome", "Hello")) and len(lines) == 1
        style = f"margin:0 0 16px;font-size:{'18px;font-weight:700' if big else '15px'};line-height:1.6;color:{INK}"
        rows.append(_cell(f'<p style="{style}">{safe}</p>'))
        if details and para.rstrip().endswith("details you gave us:"):
            trs = "".join(
                f'<tr><td style="padding:7px 12px;color:{SOFT};font-size:14px;width:38%">{htmlmod.escape(k)}</td>'
                f'<td style="padding:7px 12px;color:{INK};font-size:14px;font-weight:700">{htmlmod.escape(v)}</td></tr>'
                for k, v in details
            )
            rows.append("__DETAILS__" + trs)
    if details:
        table = (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{CREAM}" '
            f'style="background:{CREAM};border-radius:12px;margin:0 0 18px">'
        )
        rows = [_cell(table + r[len("__DETAILS__") :] + "</table>") if r.startswith("__DETAILS__") else r for r in rows]
    site = settings.APP_URL.replace("https://", "").replace("http://", "")
    place = htmlmod.escape(settings.COMPANY_ADDRESS or "Coimbatore, Tamil Nadu")
    closing = _cell(
        f'<p style="margin:8px 0 4px;font-size:15px;color:{INK}">Thank you so much,</p>'
        f'<p style="margin:0 0 18px;font-size:15px;font-weight:700;color:{FOREST}">Team Virundhu</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td bgcolor="{CREAM}" style="background:{CREAM};border-left:4px solid {TURMERIC};padding:12px 14px;'
        f'font-size:13px;font-style:italic;color:{SOFT};line-height:1.5">{htmlmod.escape(_quote())}</td></tr></table>',
        "0 28px 24px",
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light only"><meta name="supported-color-schemes" content="light">'
        f"<title>{htmlmod.escape(subject)}</title></head>"
        f'<body bgcolor="{CREAM}" style="margin:0;padding:0;background:{CREAM};font-family:Arial,Helvetica,sans-serif">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{CREAM}" '
        f'style="background:{CREAM}"><tr><td align="center" style="padding:20px 10px">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#ffffff" '
        f'style="max-width:560px;background:#ffffff;border-radius:16px;border:1px solid #efdcbf">'
        f'<tr><td bgcolor="{FOREST}" style="background:{FOREST};padding:22px 28px;border-radius:16px 16px 0 0">'
        f'<div style="color:{CREAM};font-size:24px;font-weight:700">Virundhu</div>'
        f'<div style="color:{TURMERIC};font-size:13px;margin-top:3px">Every guest, heard</div></td></tr>'
        f'<tr><td bgcolor="{TURMERIC}" style="background:{TURMERIC};height:4px;line-height:4px;font-size:0">'
        "&nbsp;</td></tr>"
        + _cell(f'<p style="margin:0 0 18px;font-size:13px;color:{SOFT}">{htmlmod.escape(subject)}</p>', "22px 28px 0")
        + "".join(rows)
        + closing
        + f'<tr><td bgcolor="{CREAM}" style="background:{CREAM};padding:14px 28px;font-size:12px;color:{SOFT};'
        f'border-radius:0 0 16px 16px">Virundhu · {place} · {htmlmod.escape(site)}<br>Need help? Reply to this email '
        f"or use Quick help on the site.</td></tr></table></td></tr></table></body></html>"
    )


def send_email(
    to: list[str],
    subject: str,
    text: str,
    html: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
    details: list[tuple[str, str]] | None = None,
) -> bool:
    """Send one email to several recipients. Returns True when sent (or logged in development).

    Customer emails get the branded Virundhu design automatically; emails to the platform admin stay plain.
    """
    recipients = sorted({r.strip().lower() for r in to if r and "@" in r})
    if not recipients:
        return False
    if html is None and settings.SUPERADMIN_EMAIL.lower() not in recipients:
        html = branded_html(subject, text, details)
        text = text.rstrip() + closing_text()
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
