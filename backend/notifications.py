"""
backend/notifications.py
━━━━━━━━━━━━━━━━━━━━━━━━
Sends HTML fraud-alert e-mails via Gmail SMTP and logs every dispatch
to logs/notifications.log.

Environment variables (loaded from .env):
  GMAIL_USER         – sender Gmail address
  GMAIL_APP_PASSWORD – 16-char Gmail App Password (not your account password)
  ALERT_EMAIL        – recipient address for send_alert()
"""

import os
import ssl
import smtplib
import logging
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()

GMAIL_USER     = os.getenv("GMAIL_USER", "")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
ALERT_EMAIL    = os.getenv("ALERT_EMAIL", "")

# ── Logging setup ─────────────────────────────────────────────────────────────
_LOG_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "notifications.log")

os.makedirs(_LOG_DIR, exist_ok=True)

# Open log file in append mode; create it if it doesn't exist
_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(message)s"))

_notif_logger = logging.getLogger("notifications")
_notif_logger.setLevel(logging.INFO)
_notif_logger.addHandler(_file_handler)
_notif_logger.propagate = False  # don't bubble up to Flask root logger


# ── HTML email template ───────────────────────────────────────────────────────
def _build_html(txn: dict) -> str:
    amount    = txn.get("amount", "N/A")
    merchant  = txn.get("merchant", "Unknown")
    location  = txn.get("location", "Unknown")
    risk      = txn.get("risk_level", "HIGH")
    confidence= txn.get("confidence", 0)
    is_fraud  = txn.get("is_fraud", True)
    timestamp = txn.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    decision_label = "🚫 BLOCKED" if is_fraud else "⚠️ FLAGGED"
    decision_color = "#ef4444"    if is_fraud else "#f59e0b"
    risk_color     = {
        "HIGH":   "#ef4444",
        "MEDIUM": "#f59e0b",
        "LOW":    "#10b981",
    }.get(risk, "#ef4444")

    risk_pct = f"{float(confidence) * 100:.1f}%" if confidence != "N/A" else "N/A"

    # Format amount
    try:
        amount_fmt = f"${float(amount):,.2f}"
    except (ValueError, TypeError):
        amount_fmt = str(amount)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Fraud Alert</title>
</head>
<body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 0;">
    <tr><td align="center">

      <!-- Card -->
      <table width="580" cellpadding="0" cellspacing="0"
             style="background:#1a1f2e;border-radius:16px;overflow:hidden;
                    border:1px solid rgba(239,68,68,0.25);
                    box-shadow:0 0 40px rgba(239,68,68,0.12);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#7f1d1d,#991b1b);
                     padding:32px 36px;text-align:center;">
            <div style="font-size:40px;margin-bottom:10px;">🚨</div>
            <h1 style="color:#fef2f2;font-size:22px;font-weight:800;
                       letter-spacing:-0.02em;margin:0 0 6px;">
              FRAUD ALERT
            </h1>
            <p style="color:#fca5a5;font-size:13px;margin:0;">
              A high-risk transaction has been detected and requires your attention.
            </p>
          </td>
        </tr>

        <!-- Decision badge -->
        <tr>
          <td style="padding:24px 36px 0;text-align:center;">
            <span style="display:inline-block;padding:8px 24px;border-radius:99px;
                         background:{decision_color}22;color:{decision_color};
                         font-size:13px;font-weight:800;letter-spacing:0.08em;
                         border:1px solid {decision_color}55;">
              {decision_label}
            </span>
          </td>
        </tr>

        <!-- Transaction table -->
        <tr>
          <td style="padding:24px 36px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border-radius:10px;overflow:hidden;
                          border:1px solid rgba(255,255,255,0.07);">

              <!-- Row helper macro (inline) -->
              {''.join([
                f"""<tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
                  <td style="padding:13px 18px;background:#111827;
                             font-size:12px;font-weight:700;
                             text-transform:uppercase;letter-spacing:0.07em;
                             color:#6b7280;width:42%;">{label}</td>
                  <td style="padding:13px 18px;background:#0f1117;
                             font-size:14px;font-weight:600;color:{color};">{value}</td>
                </tr>"""
                for label, value, color in [
                    ("Transaction Amount", amount_fmt,    "#f0f4ff"),
                    ("Merchant Name",      merchant,      "#f0f4ff"),
                    ("Location",           location,      "#f0f4ff"),
                    ("Risk Score",         risk_pct,      risk_color),
                    ("Risk Level",         risk,          risk_color),
                    ("Decision",           decision_label, decision_color),
                    ("Date &amp; Time",    timestamp,     "#9ca3af"),
                ]
              ])}

            </table>
          </td>
        </tr>

        <!-- CTA note -->
        <tr>
          <td style="padding:0 36px 28px;">
            <p style="background:rgba(239,68,68,0.08);border-left:3px solid #ef4444;
                      border-radius:4px;margin:0;padding:12px 16px;
                      font-size:12px;color:#9ca3af;line-height:1.6;">
              <strong style="color:#fca5a5;">Action required:</strong>
              Review this transaction in your
              <a href=http://localhost:5000/dashboard style="color:#6366f1;">FraudGuard dashboard</a>
              and verify with the cardholder if needed.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#111827;padding:18px 36px;text-align:center;
                     border-top:1px solid rgba(255,255,255,0.06);">
            <p style="color:#374151;font-size:11px;margin:0;">
              FraudGuard Detection System &nbsp;·&nbsp;
              Auto-generated alert &nbsp;·&nbsp;
              {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""


# ── Core send function ────────────────────────────────────────────────────────
def send_email(to_email: str, transaction_data: dict) -> dict:
    """
    Send a styled HTML fraud-alert email via Gmail SMTP (TLS port 587).

    Parameters
    ----------
    to_email         : recipient address
    transaction_data : dict with keys: amount, merchant, location,
                       risk_level, confidence, is_fraud, timestamp

    Returns
    -------
    {"status": "sent", "to": to_email}  on success
    {"status": "error", "error": str}   on failure
    """
    if not GMAIL_USER or not GMAIL_PASSWORD:
        msg = "GMAIL_USER / GMAIL_APP_PASSWORD not configured in .env"
        _notif_logger.error("[%s] EMAIL ERROR - %s",
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
        return {"status": "error", "error": msg}

    subject  = "🚨 FRAUD ALERT - Transaction Blocked"
    html_body = _build_html(transaction_data)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"]    = GMAIL_USER
    message["To"]      = to_email
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, message.as_string())

        return {"status": "sent", "to": to_email}

    except smtplib.SMTPAuthenticationError:
        err = "Gmail authentication failed — check GMAIL_APP_PASSWORD in .env"
        _notif_logger.error("[%s] EMAIL ERROR - %s",
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), err)
        return {"status": "error", "error": err}

    except Exception as exc:
        _notif_logger.error("[%s] EMAIL ERROR - %s",
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(exc))
        return {"status": "error", "error": str(exc)}


# ── High-level alert helper ───────────────────────────────────────────────────
def send_alert(transaction_data: dict) -> dict:
    """
    Fire-and-forget fraud alert email + log entry.

    Sends the email in a daemon background thread so it never blocks
    the Flask request/response cycle.

    Parameters
    ----------
    transaction_data : dict (same shape as send_email expects)

    Returns
    -------
    {"email": "queued", "time": ISO-timestamp}
    """
    recipient = ALERT_EMAIL
    now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log immediately (before the thread fires) so the record is never lost
    amount   = transaction_data.get("amount", "N/A")
    merchant = transaction_data.get("merchant", "Unknown")
    risk     = transaction_data.get("confidence", 0)
    risk_pct = f"{float(risk) * 100:.1f}" if risk != "N/A" else "N/A"

    _notif_logger.info(
        "[%s] EMAIL SENT - Amount: %s  Merchant: %s  Risk: %s%%",
        now_str, amount, merchant, risk_pct,
    )

    def _send():
        result = send_email(recipient, transaction_data)
        if result.get("status") == "error":
            _notif_logger.error(
                "[%s] EMAIL DELIVERY FAILED - %s",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                result.get("error"),
            )

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()

    return {"email": "queued", "time": now_str}
