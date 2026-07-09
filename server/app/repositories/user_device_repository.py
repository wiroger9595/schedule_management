import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Session, select

from ..models.user_device import UserDevice

logger = logging.getLogger(__name__)


class UserDeviceRepository:
    def __init__(self, session: Session):
        self.session = session

    def register_or_update(self, user_id: str, device_id: str, platform: str, fcm_token: str) -> UserDevice:
        """Register or update a device's FCM token for a user."""
        stmt = select(UserDevice).where(
            (UserDevice.user_id == user_id) & (UserDevice.device_id == device_id)
        )
        device = self.session.exec(stmt).first()
        if device:
            device.fcm_token = fcm_token
            device.platform = platform
            device.last_registered_at = datetime.now(timezone.utc)
            logger.info(f"Updated device {device_id} for user {user_id}")
        else:
            device = UserDevice(
                user_id=user_id,
                device_id=device_id,
                platform=platform,
                fcm_token=fcm_token,
                last_registered_at=datetime.now(timezone.utc)
            )
            self.session.add(device)
            logger.info(f"Registered new device {device_id} for user {user_id}")

        self.session.commit()
        return device

    def get_user_devices(self, user_id: str) -> List[UserDevice]:
        """Get all devices registered for a user."""
        stmt = select(UserDevice).where(UserDevice.user_id == user_id)
        return self.session.exec(stmt).all()

    def get_device(self, device_id: str) -> Optional[UserDevice]:
        """Get a specific device by device_id."""
        stmt = select(UserDevice).where(UserDevice.device_id == device_id)
        return self.session.exec(stmt).first()

    def delete_device(self, user_id: str, device_id: str) -> bool:
        """Delete a device. Returns True if deleted, False if not found."""
        stmt = select(UserDevice).where(
            (UserDevice.user_id == user_id) & (UserDevice.device_id == device_id)
        )
        device = self.session.exec(stmt).first()
        if device:
            self.session.delete(device)
            self.session.commit()
            logger.info(f"Deleted device {device_id} for user {user_id}")
            return True
        return False

    def delete_user_devices(self, user_id: str):
        """Delete all devices for a user (e.g., on account deletion)."""
        stmt = select(UserDevice).where(UserDevice.user_id == user_id)
        devices = self.session.exec(stmt).all()
        for device in devices:
            self.session.delete(device)
        self.session.commit()
        logger.info(f"Deleted all devices for user {user_id}")
