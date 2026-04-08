import logging
from typing import List, Dict, Any, Optional
from .email_service import email_service
from .push_service import push_service

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def notify_attendees(
        schedule: Any,
        attendees: List[Any],
        contacts_map: Dict[str, Any],
        users_map: Optional[Dict[str, Any]] = None,
        inviter_name: str = "某人"
    ):
        """
        Notify attendees about a schedule creation or update.

        :param schedule: Schedule object
        :param attendees: List of `attend` SQLAlchemy model objects
        :param contacts_map: Dict mapping contact_id -> Contact object
        :param users_map: Dict mapping user_id -> User object (for linked users)
        :param inviter_name: Display name of the schedule creator
        """
        users_map = users_map or {}
        schedule_title = schedule.title if hasattr(schedule, 'title') else "Unknown"
        print(f"\n[NotificationService] Notifying attendees for schedule: '{schedule_title}'\n" + "-"*60)

        for attendee in attendees:
            contact = contacts_map.get(attendee.contact_id)
            if not contact:
                print(f"[ERROR] Could not find contact details for attendee contact_id: {attendee.contact_id}")
                continue

            name = contact.nick_name or "Unknown User"

            if contact.contact_user_id:
                # Attendee is a registered user — send push + RSVP email
                user = users_map.get(contact.contact_user_id)

                # Push notification (in-app)
                if user and user.fcm_token:
                    from .email_service import _fmt_time
                    start_str = ""
                    if hasattr(schedule, "meeting_start_time") and schedule.meeting_start_time:
                        start_str = _fmt_time(schedule.meeting_start_time, "%m/%d %H:%M")
                    push_service.send(
                        token=user.fcm_token,
                        title=f"{inviter_name} 邀請您參加活動",
                        body=f"{schedule.title}{'  ' + start_str if start_str else ''}",
                        data={
                            "type": "invitation",
                            "attend_id": attendee.attend_id,
                            "schedule_id": str(schedule.schedule_id),
                        },
                    )
                    print(f"[PUSH] Sent invite push to user '{name}'")

                user_email = user.email if user else contact.email
                if user_email:
                    print(f"[RSVP EMAIL] Sending RSVP invite to user '{name}' ({user_email})")
                    email_service.send_attend_invitation_to_user(
                        email=user_email,
                        user_name=name,
                        schedule=schedule,
                        attend_id=attendee.attend_id,
                        inviter_name=inviter_name
                    )
                else:
                    print(f"[RSVP SKIP] User '{name}' (ID: {contact.contact_user_id}) has no email on record.")
            else:
                # Attendee is an external contact — check if they have an email
                if contact.email:
                    # Send registration invitation
                    print(f"[REG EMAIL] Sending registration invite to '{name}' at {contact.email}")
                    email_service.send_registration_invitation(
                        email=contact.email,
                        contact_name=name,
                        schedule=schedule,
                        inviter_name=inviter_name
                    )
                else:
                    # Fall back to LINE/SMS
                    method = contact.default_notification_method or "mobile"
                    if method == "line" and contact.line_id:
                        print(f"[LINE MESSAGE] Sending LINE msg to '{name}' at Line ID {contact.line_id}")
                    else:
                        print(f"[SMS] Sending SMS to '{name}' at {contact.phone or '(No Phone)'}")

        print("-" * 60 + "\n[NotificationService] Finished sending notifications.\n")

    @staticmethod
    def notify_creator_of_decline(schedule: Any, attendee_name: str, creator_user: Any):
        """
        Notify the schedule creator that an attendee has declined the invitation.

        :param schedule: Schedule object
        :param attendee_name: Display name of the person who declined
        :param creator_user: User object of the schedule creator
        """
        if not creator_user or not creator_user.email:
            print(f"[NotificationService] Creator has no email, skipping decline notification.")
            return

        print(f"[DECLINE NOTIFY] Notifying creator '{creator_user.full_name}' that '{attendee_name}' declined '{schedule.title}'")
        email_service.send_decline_notification(
            creator_email=creator_user.email,
            creator_name=creator_user.full_name or "您",
            attendee_name=attendee_name,
            schedule_title=schedule.title
        )


notification_service = NotificationService()
