"""
Firebase Cloud Messaging push notification service.
Requires GOOGLE_APPLICATION_CREDENTIALS env var pointing to a service-account JSON file,
OR FIREBASE_SERVICE_ACCOUNT_JSON env var containing the JSON string directly.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)


class PushService:
    def __init__(self):
        self._app = None

    def _get_app(self):
        if self._app is not None:
            return self._app
        try:
            import firebase_admin
            from firebase_admin import credentials

            # Support inline JSON string or file path
            sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
            if sa_json:
                cred = credentials.Certificate(json.loads(sa_json))
            else:
                cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not cred_path:
                    logger.warning("No Firebase credentials configured — push notifications disabled")
                    return None
                cred = credentials.Certificate(cred_path)

            if not firebase_admin._apps:
                self._app = firebase_admin.initialize_app(cred)
            else:
                self._app = firebase_admin.get_app()
            return self._app
        except Exception as e:
            logger.warning(f"Firebase init failed: {e}")
            return None

    def send(self, token: str, title: str, body: str, data: dict = None) -> bool:
        """
        Send a push notification to a single device token.
        Returns True on success, False on failure (never raises).
        """
        app = self._get_app()
        if not app:
            logger.info(f"[Push SKIP] Firebase not configured. Would send: {title} → {body}")
            return False
        try:
            from firebase_admin import messaging
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                token=token,
            )
            response = messaging.send(msg)
            logger.info(f"[Push OK] {response} | {title}")
            return True
        except Exception as e:
            logger.warning(f"[Push FAIL] {e}")
            return False


push_service = PushService()
