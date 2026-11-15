"""Sends the password-reset email when SMTP is set in .env (Hostinger, Gmail, Zoho... all work).

Without SMTP the app still works: the request is shown to the admin, who creates a reset link
in the admin console and shares it with the person (WhatsApp, phone, email).
"""
from __future__ import annotations

import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger("beldex.mail")


def enabled() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def _send(to: str, subject: str, text: str, html: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or f"Beldex AI <{settings.smtp_user}>"
    msg["To"], msg["Subject"] = to, subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    try:
        ctx = ssl.create_default_context()
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, 465, context=ctx, timeout=20) as s:
                s.login(settings.smtp_user, settings.smtp_password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
                s.starttls(context=ctx)
                s.login(settings.smtp_user, settings.smtp_password)
                s.send_message(msg)
        log.info("reset email sent to %s", to)
    except Exception as e:
        log.warning("could not send email to %s: %s", to, e)


def send_reset(to: str, name: str, link: str, minutes: int, lang: str = "en") -> None:
    if lang == "ta":
        subject = "Beldex AI — கடவுச்சொல்லை மாற்றுங்கள்"
        text = (f"வணக்கம் {name},\n\nஉங்கள் Beldex AI கடவுச்சொல்லை மாற்ற இந்த இணைப்பைத் திறங்கள் "
                f"({minutes} நிமிடங்களுக்கு மட்டும் செல்லும்):\n{link}\n\nநீங்கள் கேட்கவில்லை என்றால் இந்த மின்னஞ்சலைப் புறக்கணிக்கவும்.")
        btn, note = "புதிய கடவுச்சொல்லை அமைக்கவும்", f"இந்த இணைப்பு {minutes} நிமிடங்களுக்கு மட்டும். நீங்கள் கேட்கவில்லை என்றால் புறக்கணிக்கவும்."
    else:
        subject = "Beldex AI — reset your password"
        text = (f"Hi {name},\n\nOpen this link to choose a new Beldex AI password (valid for {minutes} minutes):\n{link}\n\n"
                "If you did not ask for this, you can ignore this email.")
        btn, note = "Choose a new password", f"This link works for {minutes} minutes. If you did not ask for it, ignore this email."
    html = (f'<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;color:#121318">'
            f'<h2 style="margin:0 0 12px">Beldex AI</h2><p>{"வணக்கம்" if lang == "ta" else "Hi"} {name},</p>'
            f'<p><a href="{link}" style="display:inline-block;background:#121318;color:#fff;padding:12px 20px;'
            f'border-radius:10px;text-decoration:none;font-weight:700">{btn}</a></p>'
            f'<p style="color:#5E5D57;font-size:13px">{note}</p></div>')
    threading.Thread(target=_send, args=(to, subject, text, html), daemon=True).start()
