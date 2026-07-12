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

# A schedule can have up to three independent reminders:
#  - before_start: fixed N minutes before meeting_start_time
#  - leave:        the computed "time to leave" moment (travel-time based)
#  - before_leave: fixed N minutes before the "time to leave" moment
REMINDER_TYPES = ("before_start", "leave", "before_leave")

_MESSAGE_BUILDERS = {
    "before_start": ReminderService.get_before_start_message,
    "leave": ReminderService.get_reminder_message,
    "before_leave": ReminderService.get_before_leave_message,
}


class ReminderScheduler:
    """Background scheduler for reminder notifications."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("ReminderScheduler started")

    def schedule_reminder(
        self,
        schedule_id: str,
        run_date: Optional[datetime],
        user_id: str,
        reminder_type: str = "leave",
    ):
        """
        Schedule a single reminder notification to fire at run_date.
        reminder_type is one of REMINDER_TYPES and selects which message gets sent.
        """
        if not run_date:
            logger.info(f"Skip {reminder_type} reminder for {schedule_id}: no run_date")
            return

        now = datetime.now(run_date.tzinfo) if run_date.tzinfo else datetime.now()
        if run_date <= now:
            logger.info(
                f"Skip {reminder_type} reminder for {schedule_id}: {run_date} already passed"
            )
            return

        job_id = f"reminder-{schedule_id}-{reminder_type}"

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
                run_date=run_date,
                args=[schedule_id, user_id, reminder_type],
                id=job_id,
                replace_existing=True,
            )
            logger.info(f"Scheduled {reminder_type} reminder for schedule {schedule_id} at {run_date}")
        except Exception as e:
            logger.error(f"Failed to schedule {reminder_type} reminder for {schedule_id}: {e}")

    def schedule_all_reminders(self, schedule: Schedule, user_id: str):
        """Compute and (re)schedule all three reminder types for a schedule."""
        self.schedule_reminder(
            schedule.schedule_id,
            ReminderService.compute_before_start_time(schedule),
            user_id,
            "before_start",
        )
        self.schedule_reminder(
            schedule.schedule_id, schedule.reminder_leave_by_time, user_id, "leave"
        )
        self.schedule_reminder(
            schedule.schedule_id,
            ReminderService.compute_before_leave_time(schedule),
            user_id,
            "before_leave",
        )

    def remove_all_reminders(self, schedule_id: str):
        """Remove all pending reminder jobs for a schedule (e.g. on delete/cancel)."""
        for reminder_type in REMINDER_TYPES:
            try:
                self.scheduler.remove_job(f"reminder-{schedule_id}-{reminder_type}")
            except Exception:
                pass

    def _send_reminder(self, schedule_id: str, user_id: str, reminder_type: str = "leave"):
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
                if schedule.status == "cancelled":
                    logger.info(f"Schedule {schedule_id} is cancelled, skipping {reminder_type} reminder")
                    return

                # Fetch all user devices
                stmt = select(UserDevice).where(UserDevice.user_id == user_id)
                devices = session.exec(stmt).all()
                if not devices:
                    logger.info(f"No devices registered for user {user_id}")
                    return

                # Generate message for this reminder type
                message_builder = _MESSAGE_BUILDERS.get(reminder_type, ReminderService.get_reminder_message)
                title, body = message_builder(schedule)

                # Send push to each device
                for device in devices:
                    success = push_service.send(
                        token=device.fcm_token,
                        title=title,
                        body=body,
                        data={
                            "type": "departure_reminder",
                            "reminder_type": reminder_type,
                            "schedule_id": schedule_id,
                        },
                    )
                    if success:
                        logger.info(
                            f"Sent {reminder_type} reminder to device {device.device_id} (platform: {device.platform})"
                        )
                    else:
                        logger.warning(
                            f"Failed to send {reminder_type} reminder to device {device.device_id}"
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
