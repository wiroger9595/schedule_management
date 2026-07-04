
import os
import sys
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextMessage, TextSendMessage, MessageEvent
import logging
logger = logging.getLogger(__name__)

# Retrieve credentials from environment
access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
channel_secret = os.getenv("LINE_CHANNEL_SECRET")

class LineService:
    def __init__(self):
        self.enabled = False
        if access_token and channel_secret:
            try:
                self.line_bot_api = LineBotApi(access_token)
                self.handler = WebhookHandler(channel_secret)
                self.enabled = True
                logger.info("LineService initialized.")
            except Exception as e:
                logger.info(f"Failed to initialize LineService: {e}")
        else:
            logger.info("Line credentials not found in .env")

    def push_message(self, user_id: str, message: str) -> bool:
        if not self.enabled:
            logger.info(f"[LineService Mock] Push to {user_id}: {message}")
            return False
            
        try:
            self.line_bot_api.push_message(user_id, TextSendMessage(text=message))
            return True
        except Exception as e:
            logger.info(f"Failed to push Line message: {e}")
            return False

    def handle_webhook(self, body: str, signature: str):
        if not self.enabled:
            raise Exception("LineService is disabled")
            
        try:
            self.handler.handle(body, signature)
        except InvalidSignatureError:
            raise ValueError("Invalid signature")
        except Exception as e:
             raise e

line_service = LineService()
