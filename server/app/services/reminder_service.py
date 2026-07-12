import logging
from datetime import datetime, timedelta
from typing import Optional

from ..models.schedule import Schedule
from .osmnx_service import OSMnxService

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for computing departure-reminder times based on travel duration."""

    BUFFER_MINUTES = 10  # Safety margin after travel time calculation
    DEFAULT_TRAVEL_MINUTES = 30  # Fallback if travel-time lookup fails or no coordinates
    # TDXService (server/app/services/tdx_service.py) is currently an unconfigured
    # placeholder (no TDX_CLIENT_ID/SECRET anywhere in this codebase) — its
    # get_transit_route() would just fail. Until real transit routing is wired up,
    # use a fixed estimate for "transit" mode.
    TRANSIT_DEFAULT_MINUTES = 45
    DEFAULT_USER_LAT = 25.0330  # Taipei (default, until per-user home location exists)
    DEFAULT_USER_LON = 121.5654

    @staticmethod
    def _as_datetime(value) -> Optional[datetime]:
        """meeting_start_time/meeting_end_time are stored as VARCHAR in the DB
        (schema drift from the DateTime column declared on the model), so a fresh
        fetch returns a str, not a datetime. Normalize defensively, matching the
        isinstance(..., datetime) pattern already used elsewhere in this codebase
        (see app/api/endpoints/schedules.py, admin.py, users.py)."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            logger.warning(f"Could not parse datetime string: {value!r}")
            return None

    @staticmethod
    def compute_leave_by_time(schedule: Schedule) -> Optional[datetime]:
        """
        Compute the time the user should leave to arrive by meeting_start_time.
        Uses travel time from default user location to meeting location based on transport_mode.
        Returns None if meeting_start_time is missing.

        Formula: leave_by_time = meeting_start_time - travel_duration - buffer
        """
        start_time = ReminderService._as_datetime(schedule.meeting_start_time)
        if not start_time:
            logger.warning(f"Schedule {schedule.schedule_id} has no meeting_start_time")
            return None

        # If no location, can't compute travel time; use default buffer
        if not schedule.latitude or not schedule.longitude:
            logger.info(f"Schedule {schedule.schedule_id} has no coordinates, using default buffer")
            return start_time - timedelta(
                minutes=ReminderService.DEFAULT_TRAVEL_MINUTES + ReminderService.BUFFER_MINUTES
            )

        mode = schedule.transport_mode or "car"

        if mode == "transit":
            travel_minutes = ReminderService.TRANSIT_DEFAULT_MINUTES
        else:
            try:
                result = OSMnxService.get_travel_estimate(
                    ReminderService.DEFAULT_USER_LAT,
                    ReminderService.DEFAULT_USER_LON,
                    schedule.latitude,
                    schedule.longitude,
                    mode=mode,
                )
                # duration is always in minutes (see OSMnxService.get_travel_estimate)
                travel_minutes = result["duration"] if result else ReminderService.DEFAULT_TRAVEL_MINUTES
            except Exception as e:
                logger.warning(
                    f"Travel time lookup failed for schedule {schedule.schedule_id}: {e}, using default"
                )
                travel_minutes = ReminderService.DEFAULT_TRAVEL_MINUTES

        logger.info(f"Schedule {schedule.schedule_id}: {mode} → {travel_minutes:.0f} min from default location")

        leave_by_time = start_time - timedelta(
            minutes=travel_minutes + ReminderService.BUFFER_MINUTES
        )
        return leave_by_time

    @staticmethod
    def compute_and_update_leave_by_time(schedule: Schedule, session) -> Optional[datetime]:
        """Compute and store leave_by_time on a schedule."""
        leave_by_time = ReminderService.compute_leave_by_time(schedule)
        schedule.reminder_leave_by_time = leave_by_time
        session.add(schedule)
        session.commit()
        logger.info(f"Updated reminder_leave_by_time for schedule {schedule.schedule_id}: {leave_by_time}")
        return leave_by_time

    @staticmethod
    def compute_before_start_time(schedule: Schedule) -> Optional[datetime]:
        """Fixed reminder: N minutes before meeting_start_time (user-adjustable, default 60)."""
        start_time = ReminderService._as_datetime(schedule.meeting_start_time)
        if not start_time:
            return None
        minutes = schedule.reminder_before_start_minutes or 60
        return start_time - timedelta(minutes=minutes)

    @staticmethod
    def compute_before_leave_time(schedule: Schedule) -> Optional[datetime]:
        """Heads-up reminder: N minutes before the computed leave-by time (user-adjustable, default 60).
        Requires reminder_leave_by_time to already be computed."""
        if not schedule.reminder_leave_by_time:
            return None
        minutes = schedule.reminder_before_leave_minutes or 60
        return schedule.reminder_leave_by_time - timedelta(minutes=minutes)

    @staticmethod
    def get_reminder_message(schedule: Schedule) -> tuple[str, str]:
        """
        Generate reminder notification title and body for the "time to leave" moment.
        Returns (title, body)
        """
        start_time = ReminderService._as_datetime(schedule.meeting_start_time)
        if not schedule.reminder_leave_by_time or not start_time:
            return "時間提醒", f"《{schedule.title}》"

        travel_minutes = int(
            (start_time - schedule.reminder_leave_by_time).total_seconds() / 60
        ) - ReminderService.BUFFER_MINUTES

        mode_icon = {
            "car": "🚗",
            "motorcycle": "🏍️",
            "transit": "🚌",
            "bike": "🚴",
            "walk": "🚶",
        }.get(schedule.transport_mode or "car", "📍")

        start_time_str = start_time.strftime("%H:%M")
        title = f"是時候出發了 {mode_icon}"
        body = f"{schedule.title} 於 {start_time_str} 開始 (預計 {travel_minutes} 分鐘)"

        return title, body

    @staticmethod
    def get_before_start_message(schedule: Schedule) -> tuple[str, str]:
        """Notification for the fixed "N minutes before start" reminder."""
        minutes = schedule.reminder_before_start_minutes or 60
        start_time = ReminderService._as_datetime(schedule.meeting_start_time)
        start_time_str = start_time.strftime("%H:%M") if start_time else ""
        title = "行程提醒"
        body = f"《{schedule.title}》還有 {minutes} 分鐘於 {start_time_str} 開始"
        return title, body

    @staticmethod
    def get_before_leave_message(schedule: Schedule) -> tuple[str, str]:
        """Notification for the "N minutes before you need to leave" heads-up reminder."""
        minutes = schedule.reminder_before_leave_minutes or 60
        title = "準備出發提醒"
        body = f"還有 {minutes} 分鐘該準備出發前往《{schedule.title}》了"
        return title, body
