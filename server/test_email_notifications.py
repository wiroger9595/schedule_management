import sys
import os
from datetime import datetime

# Add the server directory to the sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.notification_service import notification_service

class MockSchedule:
    def __init__(self):
        self.title = "Direct Test Event"
        self.description = "Testing the HTML template logic directly without spinning up the server."
        self.meeting_start_time = datetime.now()
        self.meeting_end_time = datetime.now()
        self.meeting_location = "Taipei 101"

class MockAttend:
    def __init__(self, contact_id):
        self.contact_id = contact_id

class MockContactUser:
    def __init__(self):
        self.id = 1
        self.contact_user_id = "user123"
        self.nick_name = "Existing User"
        self.default_notification_method = "mobile"
        self.email = "should.not@receive.email.com"

class MockContactEmail:
    def __init__(self):
        self.id = 2
        self.contact_user_id = None
        self.nick_name = "Non User (Email)"
        self.default_notification_method = "email"
        self.email = "test.nonuser@example.com"

class MockContactSMS:
    def __init__(self):
        self.id = 3
        self.contact_user_id = None
        self.nick_name = "Non User (SMS)"
        self.default_notification_method = "sms"
        self.email = None
        self.phone = "12345678"

def main():
    schedule = MockSchedule()
    attends = [MockAttend(1), MockAttend(2), MockAttend(3)]
    contacts_map = {
        1: MockContactUser(),
        2: MockContactEmail(),
        3: MockContactSMS()
    }
    
    print("Executing notify_attendees...")
    notification_service.notify_attendees(schedule, attends, contacts_map)
    print("Done!")

if __name__ == "__main__":
    main()
