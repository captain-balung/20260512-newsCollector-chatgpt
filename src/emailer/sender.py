"""Email sender (SRS §8). SMTP primary; SendGrid stub for parity."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from ..config import get_settings

log = logging.getLogger(__name__)


class EmailResult:
    def __init__(self, ok: bool, message: str = "") -> None:
        self.ok = ok
        self.message = message


def send_daily(subject: str, *, html: str, plain: str) -> EmailResult:
    s = get_settings()
    if s.use_mock or not s.email_to or not s.smtp_user or not s.smtp_password:
        log.info("[mock email] would send to=%s subject=%s size_html=%dB",
                 s.email_to or "<unset>", subject, len(html))
        return EmailResult(ok=True, message="mocked")

    # SRS §8.3 size check
    cap_kb = s.system["publish"].get("email_max_size_kb", 500)
    if len(html.encode()) > cap_kb * 1024:
        log.warning("HTML over %dKB cap; sending plain only", cap_kb)
        html = ""

    if s.email_provider == "sendgrid":
        return _send_sendgrid_stub(subject, html=html, plain=plain)
    return _send_smtp(subject, html=html, plain=plain)


def _send_smtp(subject: str, *, html: str, plain: str) -> EmailResult:
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = ", ".join(s.email_to)
    msg["Subject"] = subject
    msg.set_content(plain or "(plain-text version unavailable)")
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
        return EmailResult(ok=True, message="sent via smtp")
    except Exception as e:  # noqa: BLE001
        log.exception("SMTP send failed")
        return EmailResult(ok=False, message=str(e))


def _send_sendgrid_stub(subject: str, *, html: str, plain: str) -> EmailResult:
    log.info("[sendgrid stub] not implemented; would send subject=%s", subject)
    return EmailResult(ok=True, message="sendgrid-stub")
