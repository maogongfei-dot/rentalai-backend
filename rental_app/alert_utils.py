"""Lightweight alerting for RentalAI — no external dependencies.

Provides:
  send_alert(message, level)   – structured log + optional webhook
  FailureTracker               – fires alert after N consecutive failures
"""

import logging
import os
import threading
from datetime import datetime, timezone

logger = logging.getLogger("rentalai.alert")

# P0=fatal  P1=critical  P2=warning  P3=info
ALERT_LEVELS = ("P0", "P1", "P2", "P3")

_WEBHOOK_URL = os.environ.get("RENTALAI_ALERT_WEBHOOK")


def send_alert(message: str, *, level: str = "P1", source: str = "unknown") -> None:
    """Emit a structured alert.

    Always logs to stdout (captured by Render).  When ``RENTALAI_ALERT_WEBHOOK``
    is configured, also POSTs a JSON payload to the URL (Slack / Discord / custom).
    The webhook call is fire-and-forget so it never blocks the request path.
    """
    ts = datetime.now(timezone.utc).isoformat()
    log_line = "[ALERT %s] %s | source=%s | ts=%s" % (level, message, source, ts)

    if level in ("P0", "P1"):
        logger.critical(log_line)
    else:
        logger.warning(log_line)

    if _WEBHOOK_URL:
        _post_webhook(log_line)


def _post_webhook(text: str) -> None:
    """Best-effort POST to a webhook URL in a background thread."""

    def _do():
        try:
            import urllib.request
            import json

            payload = json.dumps({"text": text}).encode()
            req = urllib.request.Request(
                _WEBHOOK_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            logger.debug("Webhook delivery failed (non-fatal)", exc_info=True)

    threading.Thread(target=_do, daemon=True).start()


class FailureTracker:
    """Track consecutive failures per key and fire an alert at a threshold.

    >>> tracker = FailureTracker(threshold=3, source="api")
    >>> tracker.record_failure("/analyze", "timeout")   # 1st – silent
    >>> tracker.record_failure("/analyze", "timeout")   # 2nd – silent
    >>> tracker.record_failure("/analyze", "timeout")   # 3rd – fires alert
    >>> tracker.record_success("/analyze")              # resets counter
    """

    def __init__(self, *, threshold: int = 3, source: str = "unknown"):
        self._threshold = threshold
        self._source = source
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def record_failure(self, key: str, detail: str = "") -> int:
        """Increment failure count for *key*. Returns new count."""
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + 1
            count = self._counts[key]
        if count == self._threshold:
            send_alert(
                "%s consecutive failures on %s: %s" % (count, key, detail),
                level="P1",
                source=self._source,
            )
        return count

    def record_success(self, key: str) -> None:
        """Reset failure count for *key*."""
        with self._lock:
            self._counts.pop(key, None)

    def get_counts(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)
