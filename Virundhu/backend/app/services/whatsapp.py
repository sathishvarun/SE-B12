"""WhatsApp alerts through Meta's WhatsApp Cloud API.

Business-started messages must use a template approved by Meta. Create one in WhatsApp Manager named
WHATSAPP_TEMPLATE (default "virundhu_alert"), category Utility, language English, body for example:

    Urgent review at {{1}}: {{2}}. Open it in Virundhu: {{3}}

Then set WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env. Until both are set, nothing is sent.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _send_template(to: str, template: str, params: list[str]) -> bool:
    """Send one approved template message. Returns True if Meta accepted it."""
    if not settings.whatsapp_enabled:
        return False
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    body = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": settings.WHATSAPP_TEMPLATE_LANG},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}],
        },
    }
    try:
        res = httpx.post(url, json=body, headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}, timeout=15)
    except httpx.HTTPError as exc:
        logger.warning("WhatsApp %s to ...%s failed: %s", template, to[-4:], exc)
        return False
    if res.status_code >= 400:
        logger.warning("WhatsApp %s to ...%s refused %s: %s", template, to[-4:], res.status_code, res.text[:300])
        return False
    return True


def send_alert(to: str, where: str, summary: str, link: str) -> bool:
    """Urgent-review alert (template WHATSAPP_TEMPLATE: 'Urgent review at {{1}}: {{2}}. Open it: {{3}}')."""
    return _send_template(to, settings.WHATSAPP_TEMPLATE, [where[:60], summary[:500], link])


def send_review_request(to: str, place: str, link: str) -> bool:
    """Ask a guest for feedback (template WHATSAPP_TEMPLATE_REVIEW: 'Thank you for eating at {{1}}! {{2}}')."""
    return _send_template(to, settings.WHATSAPP_TEMPLATE_REVIEW, [place[:60], link])


def send_summary(to: str, name: str, summary: str, link: str) -> bool:
    """Weekly summary (template WHATSAPP_TEMPLATE_SUMMARY: 'Your week at {{1}}: {{2}} See details: {{3}}')."""
    return _send_template(to, settings.WHATSAPP_TEMPLATE_SUMMARY, [name[:60], summary[:900], link])


def send_plan_reminder(to: str, name: str, line: str, link: str) -> bool:
    """Trial/plan ending (template WHATSAPP_TEMPLATE_PLAN, Utility: '{{1}}: {{2}}. Choose a plan here: {{3}}')."""
    return _send_template(to, settings.WHATSAPP_TEMPLATE_PLAN, [name[:60], line[:300], link])
