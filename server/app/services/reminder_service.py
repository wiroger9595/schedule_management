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
    def compute_leave_by_time(schedule: Schedule) -> Optional[datetime]:
        """
        Compute the time the user should leave to arrive by meeting_start_time.
        Uses travel time from default user location to meeting location based on transport_mode.
        Returns None if meeting_start_time is missing.

        Formula: leave_by_time = meeting_start_time - travel_duration - buffer
        """
        if not schedule.meeting_start_time:
            logger.warning(f"Schedule {schedule.schedule_id} has no meeting_start_time")
            return None

        # If no location, can't compute travel time; use default buffer
        if not schedule.latitude or not schedule.longitude:
            logger.info(f"Schedule {schedule.schedule_id} has no coordinates, using default buffer")
            return schedule.meeting_start_time - timedelta(
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

        leave_by_time = schedule.meeting_start_time - timedelta(
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
    def get_reminder_message(schedule: Schedule) -> tuple[str, str]:
        """
        Generate reminder notification title and body.
        Returns (title, body)
        """
        if not schedule.reminder_leave_by_time or not schedule.meeting_start_time:
            return "時間提醒", f"《{schedule.title}》"

        travel_minutes = int(
            (schedule.meeting_start_time - schedule.reminder_leave_by_time).total_seconds() / 60
        ) - ReminderService.BUFFER_MINUTES

        mode_icon = {
            "car": "🚗",
            "motorcycle": "🏍️",
            "transit": "🚌",
            "bike": "🚴",
            "walk": "🚶",
        }.get(schedule.transport_mode or "car", "📍")

        start_time_str = schedule.meeting_start_time.strftime("%H:%M")
        title = f"是時候出發了 {mode_icon}"
        body = f"{schedule.title} 於 {start_time_str} 開始 (預計 {travel_minutes} 分鐘)"

        return title, body
