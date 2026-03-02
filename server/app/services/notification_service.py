import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def notify_attendees(schedule_title: str, attendees: List[Any], contacts_map: Dict[str, Any]):
        """
        Simulate notifying attendees about a schedule creation or update.
        :param schedule_title: Title of the schedule
        :param attendees: List of `attend` SQLAlchemy model objects
        :param contacts_map: Dict mapping contact_id -> Contact object for fast lookup
        """
        print(f"\n[NotificationService] Beginning notifications for schedule: '{schedule_title}'\n" + "-"*60)
        
        for attendee in attendees:
            contact = contacts_map.get(attendee.contact_id)
            if not contact:
                print(f"[ERROR] Could not find contact details for attendee contact_id: {attendee.contact_id}")
                continue

            name = contact.nick_name or contact.name or "Unknown User"
            
            if contact.contact_user_id:
                # App user route
                print(f"[APP PUSH] Sending in-app notification to User '{name}' (App ID: {contact.contact_user_id})")
            else:
                # External contact route
                method = contact.default_notification_method or "mobile"
                if method == "email":
                    print(f"[EMAIL] Sending email notification to '{name}' at {contact.email or '(No Email Provided)'}")
                elif method == "line":
                    print(f"[LINE MESSAGE] Sending LINE msg to '{name}' at Line ID {contact.line_id or '(No Line ID Provided)'}")
                else:
                    print(f"[SMS] Sending SMS notification to '{name}' at {contact.phone or '(No Phone Provided)'}")

        print("-" * 60 + "\n[NotificationService] Finished sending notifications.\n")

notification_service = NotificationService()
