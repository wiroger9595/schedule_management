import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from ..db.database import engine
from ..models.schedule import Schedule
from ..models.user_device import UserDevice
from .push_service import push_service
from .reminder_service import ReminderService

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Background scheduler for reminder notifications."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("ReminderScheduler started")

    def schedule_reminder(self, schedule_id: str, leave_by_time: datetime, user_id: str):
        """
        Schedule a reminder notification to fire at leave_by_time.
        """
        if not leave_by_time:
            logger.warning(f"Cannot schedule reminder for {schedule_id}: leave_by_time is None")
            return

        job_id = f"reminder-{schedule_id}"

        # Remove existing job if it exists (for rescheduling)
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job {job_id}")
        except Exception:
            pass

        try:
            self.scheduler.add_job(
                self._send_reminder,
                "date",
                run_date=leave_by_time,
                args=[schedule_id, user_id],
                id=job_id,
                replace_existing=True,
            )
            logger.info(f"Scheduled reminder for schedule {schedule_id} at {leave_by_time} UTC")
        except Exception as e:
            logger.error(f"Failed to schedule reminder for {schedule_id}: {e}")

    def _send_reminder(self, schedule_id: str, user_id: str):
        """
        Callback: Fetch schedule and send push notifications to all user's devices.
        """
        try:
            with Session(engine) as session:
                # Fetch schedule
                stmt = select(Schedule).where(Schedule.schedule_id == schedule_id)
                schedule = session.exec(stmt).first()
                if not schedule:
                    logger.warning(f"Schedule {schedule_id} not found during reminder callback")
                    return

                # Fetch all user devices
                stmt = select(UserDevice).where(UserDevice.user_id == user_id)
                devices = session.exec(stmt).all()
                if not devices:
                    logger.info(f"No devices registered for user {user_id}")
                    return

                # Generate message
                title, body = ReminderService.get_reminder_message(schedule)

                # Send push to each device
                for device in devices:
                    success = push_service.send(
                        token=device.fcm_token,
                        title=title,
                        body=body,
                        data={
                            "type": "departure_reminder",
                            "schedule_id": schedule_id,
                        },
                    )
                    if success:
                        logger.info(
                            f"Sent reminder to device {device.device_id} (platform: {device.platform})"
                        )
                    else:
                        logger.warning(
                            f"Failed to send reminder to device {device.device_id}"
                        )

        except Exception as e:
            logger.error(f"Error in reminder callback for schedule {schedule_id}: {e}")

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("ReminderScheduler shut down")


# Global instance
reminder_scheduler: Optional[ReminderScheduler] = None


def init_reminder_scheduler():
    """Initialize the global reminder scheduler."""
    global reminder_scheduler
    if reminder_scheduler is None:
        reminder_scheduler = ReminderScheduler()
    return reminder_scheduler


def get_reminder_scheduler() -> Optional[ReminderScheduler]:
    """Get the global reminder scheduler instance."""
    return reminder_scheduler
