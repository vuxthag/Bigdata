"""
crawler/alerts.py
=================
Simple alert system for crawler failures and anomalies.

Behavior:
  - If TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID are set → send Telegram message
  - Otherwise → print alert to console (stdout/log)

Configure via environment variables:
  TELEGRAM_BOT_TOKEN  — BotFather token
  TELEGRAM_CHAT_ID    — target chat/group/channel ID (can be negative for groups)

Usage:
    from crawler.alerts import send_alert
    send_alert("Crawler blocked by ITviec (403). Please check immediately.", level="critical")
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Emoji prefixes by severity
_LEVEL_PREFIX = {
    "critical": "🚨 CRITICAL",
    "warning": "⚠️ WARNING",
    "info": "ℹ️ INFO",
}


def _send_telegram(message: str) -> bool:
    """
    Send a message via Telegram Bot API.
    Returns True if sent successfully, False otherwise.
    """
    if not _TELEGRAM_TOKEN or not _TELEGRAM_CHAT_ID:
        return False

    try:
        import requests  # already in requirements.txt
        url = f"https://api.telegram.org/bot{_TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={
                "chat_id": _TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logger.debug("[Alerts] Telegram message sent successfully")
            return True
        else:
            logger.warning(f"[Alerts] Telegram API error: {resp.status_code} — {resp.text[:200]}")
            return False
    except Exception as exc:
        logger.warning(f"[Alerts] Failed to send Telegram message: {exc}")
        return False


def send_alert(message: str, level: str = "warning") -> None:
    """
    Send an alert through available channels.

    Priority:
      1. Telegram (if configured)
      2. Console log

    Args:
        message: Human-readable alert message
        level:   Severity level — "critical", "warning", or "info"
    """
    prefix = _LEVEL_PREFIX.get(level, "⚠️ ALERT")
    full_message = f"{prefix}\n\n{message}"

    # Try Telegram first
    if _TELEGRAM_TOKEN and _TELEGRAM_CHAT_ID:
        sent = _send_telegram(full_message)
        if sent:
            return
        # Fall through to console if Telegram fails

    # Console fallback
    if level == "critical":
        logger.error(f"[ALERT] {full_message}")
    elif level == "warning":
        logger.warning(f"[ALERT] {full_message}")
    else:
        logger.info(f"[ALERT] {full_message}")
