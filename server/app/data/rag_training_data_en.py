"""
RAG Training Dataset (English) V1 - Base Scenarios
67 examples covering 20 categories.

Today: 2026-05-08 (Friday)
"""

TODAY = "2026-05-08"

RAG_TRAINING_DATA_EN = [
    # ========================================================================
    # Category 1: Create complete schedules (is_complete=True)
    # ========================================================================
    {
        "category": "create_complete",
        "user_message": "Meeting with Mike at Taipei 101 tomorrow at 3pm",
        "intent": "create",
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "Meeting with Mike",
            "start_time": "2026-05-09T15:00:00",
            "end_time": "2026-05-09T17:00:00",
            "location": "Taipei 101",
            "participants": ["@Mike"]
        },
        "is_complete": True,
        "explanation": "Time + location + person + activity all complete"
    },
    {
        "category": "create_complete",
        "user_message": "Dinner with friends at Xinyi district at 7pm day after tomorrow",
        "intent": "create",
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "Dinner with friends",
            "start_time": "2026-05-10T19:00:00",
            "end_time": "2026-05-10T21:00:00",
            "location": "Xinyi district",
            "participants": []
        },
        "is_complete": True,
        "explanation": "'friends' is generic, goes in title not participants"
    },
    {
        "category": "create_complete",
        "user_message": "Monday morning standup at 9am at the office",
        "intent": "create",
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "Monday standup",
            "start_time": "2026-05-11T09:00:00",
            "end_time": "2026-05-11T10:00:00",
            "location": "office",
            "participants": []
        },
        "is_complete": True
    },
    {
        "category": "create_complete",
        "user_message": "Basketball today at 4pm",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "Basketball",
            "start_time": "2026-05-08T16:00:00",
            "end_time": "2026-05-08T18:00:00"
        },
        "is_complete": False,
        "missing": ["location"],
        "explanation": "Sports require location"
    },
    {
        "category": "create_complete",
        "user_message": "Lunch with coworkers tomorrow",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "Lunch with coworkers",
            "start_time": "2026-05-09T12:00:00"
        },
        "is_complete": False,
        "missing": ["location"]
    },

    # ========================================================================
    # Category 2: Create with missing info
    # ========================================================================
    {
        "category": "create_partial",
        "user_message": "Meeting tomorrow",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {"title": "Meeting", "start_time": "2026-05-09T09:00:00"},
        "is_complete": False,
        "question": "What time? Where?"
    },
    {
        "category": "create_partial",
        "user_message": "Coffee with Alex this afternoon",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "Coffee with Alex",
            "start_time": "2026-05-08T14:00:00",
            "participants": ["@Alex"]
        },
        "is_complete": False,
        "missing": ["location"]
    },
    {
        "category": "create_partial",
        "user_message": "Family dinner on Friday",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "Family dinner",
            "start_time": "2026-05-15T19:00:00"
        },
        "is_complete": False,
        "missing": ["location"]
    },

    # ========================================================================
    # Category 3: Time parsing
    # ========================================================================
    {"category": "time_parsing", "user_message": "tomorrow", "parsed_time": "2026-05-09"},
    {"category": "time_parsing", "user_message": "day after tomorrow", "parsed_time": "2026-05-10"},
    {"category": "time_parsing", "user_message": "next Monday", "parsed_time": "2026-05-11"},
    {"category": "time_parsing", "user_message": "this Saturday", "parsed_time": "2026-05-09"},
    {"category": "time_parsing", "user_message": "next Friday", "parsed_time": "2026-05-15"},
    {"category": "time_parsing", "user_message": "in 3 days", "parsed_time": "2026-05-11"},
    {"category": "time_parsing", "user_message": "3pm", "parsed_time": "T15:00:00"},
    {"category": "time_parsing", "user_message": "7:30pm", "parsed_time": "T19:30:00"},
    {"category": "time_parsing", "user_message": "evening", "parsed_time": "T19:00:00"},
    {"category": "time_parsing", "user_message": "early morning", "parsed_time": "T06:00:00"},
    {"category": "time_parsing", "user_message": "noon", "parsed_time": "T12:00:00"},
    {"category": "time_parsing", "user_message": "May 20 at 4pm", "parsed_time": "2026-05-20T16:00:00"},
    {"category": "time_parsing", "user_message": "in 2 hours", "parsed_time": "now+2h"},
    {"category": "time_parsing", "user_message": "tonight", "parsed_time": "today T19:00:00"},

    # ========================================================================
    # Category 4: Edit schedules
    # ========================================================================
    {
        "category": "edit",
        "user_message": "Change the meeting to 4pm",
        "intent": "edit",
        "context": {"schedule_list": [{"id": "abc-123", "title": "Meeting", "start_time": "2026-05-09T09:00:00"}]},
        "expected_action": "update_schedule",
        "parsed_data": {"schedule_id": "abc-123", "start_time": "2026-05-09T16:00:00"}
    },
    {
        "category": "edit",
        "user_message": "Move dinner with Mike to Starbucks",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {"location": "Starbucks"}
    },
    {
        "category": "edit",
        "user_message": "Add @Sarah",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {"participants": ["@Sarah"]}
    },
    {
        "category": "edit",
        "user_message": "Remove @Mike",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {"remove_participants": ["@Mike"]}
    },
    {
        "category": "edit",
        "user_message": "Remove all participants",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {"clear_participants": True}
    },
    {
        "category": "edit",
        "user_message": "Make it later",
        "intent": "edit",
        "expected_action": "ask_user",
        "question": "What time?"
    },
    {
        "category": "edit",
        "user_message": "Reschedule to 9am",
        "intent": "edit",
        "context": {"schedule_list": [{"id": "abc", "start_time": "2026-05-09T15:00:00"}]},
        "expected_action": "update_schedule",
        "parsed_data": {"schedule_id": "abc", "start_time": "2026-05-09T09:00:00"},
        "explanation": "Keep original date, only change time"
    },

    # ========================================================================
    # Category 5: Delete
    # ========================================================================
    {
        "category": "delete",
        "user_message": "Delete the meeting",
        "intent": "delete",
        "context": {"schedule_list": [{"id": "abc", "title": "Meeting"}]},
        "expected_action": "delete_schedule",
        "parsed_data": {"schedule_id": "abc"}
    },
    {
        "category": "delete",
        "user_message": "Cancel tomorrow's meeting",
        "intent": "delete",
        "expected_action": "delete_schedule"
    },
    {
        "category": "delete",
        "user_message": "I'm not going",
        "intent": "delete",
        "expected_action": "ask_user",
        "question": "Which schedule do you want to cancel?"
    },
    {
        "category": "delete",
        "user_message": "Drop all schedules with Mike",
        "intent": "delete",
        "context": {"schedule_list": [{"id": "a", "title": "Lunch with Mike"}, {"id": "b", "title": "Meeting with Mike"}]},
        "expected_action": "ask_user",
        "question": "You have 2 schedules with Mike:\n1️⃣ Lunch with Mike\n2️⃣ Meeting with Mike\n\nDelete all or just one?"
    },

    # ========================================================================
    # Category 6: Query
    # ========================================================================
    {"category": "query", "user_message": "What's on my schedule?", "intent": "query"},
    {"category": "query", "user_message": "What's tomorrow looking like?", "intent": "query"},
    {"category": "query", "user_message": "When's the meeting?", "intent": "query"},

    # ========================================================================
    # Category 7: Duplicate contacts
    # ========================================================================
    {
        "category": "duplicate_contact",
        "user_message": "Lunch with Mike tomorrow",
        "context": {"duplicate_contacts": [{"name": "Mike", "comment": "coworker", "phone_last4": "1234"}, {"name": "Mike", "comment": "friend", "phone_last4": "5678"}]},
        "expected_action": "ask_user",
        "question": "Which Mike?\n1️⃣ Mike (coworker) - phone ends 1234\n2️⃣ Mike (friend) - phone ends 5678"
    },
    {
        "category": "duplicate_contact",
        "user_message": "1",
        "context": {"_pending_duplicate": "Mike"},
        "expected_action": "continue_create"
    },

    # ========================================================================
    # Category 8: Online meetings
    # ========================================================================
    {
        "category": "online_meeting",
        "user_message": "Online meeting tomorrow at 3pm",
        "intent": "create",
        "parsed_data": {"title": "Online meeting", "start_time": "2026-05-09T15:00:00", "is_online": True},
        "is_complete": True
    },
    {
        "category": "online_meeting",
        "user_message": "Zoom call with the team tomorrow",
        "intent": "create",
        "expected_action": "ask_user",
        "is_complete": False,
        "missing": ["start_time"]
    },

    # ========================================================================
    # Category 9: Out of scope
    # ========================================================================
    {
        "category": "out_of_scope",
        "user_message": "What's the weather today?",
        "expected_action": "reply_to_user",
        "reply": "I'm a schedule assistant, here to help you plan and manage your schedule 📅 Any schedules to plan?"
    },
    {
        "category": "out_of_scope",
        "user_message": "Recommend a song",
        "expected_action": "reply_to_user",
        "reply": "I'm a schedule assistant. Any schedules to plan?"
    },
    {
        "category": "out_of_scope",
        "user_message": "Hi",
        "expected_action": "reply_to_user",
        "reply": "Hi! I'm your schedule assistant. Any schedules to plan?"
    },

    # ========================================================================
    # Category 10: Edge cases
    # ========================================================================
    {
        "category": "edge_case",
        "user_message": "Dinner at 5pm with @Sam and @Alex at Sam's place",
        "intent": "create",
        "expected_action": "ask_user",
        "is_complete": False,
        "missing": ["location"],
        "explanation": "'Sam's place' is not a valid location, ask for address"
    },
    {
        "category": "edge_case",
        "user_message": "Going to the airport on the 15th of next month",
        "intent": "create",
        "expected_action": "ask_user",
        "is_complete": False,
        "missing": ["location_specific", "time_specific"]
    },
    {
        "category": "edge_case",
        "user_message": "Change to Starbucks",
        "intent": "edit",
        "expected_action": "ask_user",
        "question": "Which schedule's location do you want to change?"
    },
    {
        "category": "edge_case",
        "user_message": "Add another one",
        "expected_action": "ask_user",
        "question": "What schedule would you like to add?"
    },
    {
        "category": "edge_case",
        "user_message": "uh",
        "expected_action": "reply_to_user"
    },

    # ========================================================================
    # Category 11: Title inference
    # ========================================================================
    {"category": "title_inference", "user_message": "Going for dinner tomorrow", "title": "Dinner"},
    {"category": "title_inference", "user_message": "Dinner with Mike tomorrow", "title": "Dinner with Mike"},
    {"category": "title_inference", "user_message": "Movie tomorrow night", "title": "Movie"},
    {"category": "title_inference", "user_message": "Run this afternoon", "title": "Run"},
    {"category": "title_inference", "user_message": "Business meeting with client at Hyatt tomorrow", "title": "Business meeting with client", "location": "Hyatt"},
    {"category": "title_inference", "user_message": "Doctor's appointment tomorrow", "title": "Doctor's appointment"},

    # ========================================================================
    # Category 12: Multi-field edit
    # ========================================================================
    {
        "category": "multi_edit",
        "user_message": "Change to 9am and switch location to Starbucks",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {"start_time": "..T09:00:00", "location": "Starbucks"}
    },
    {
        "category": "multi_edit",
        "user_message": "Move meeting to day after tomorrow at 2pm at Taipei 101",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {"start_time": "2026-05-10T14:00:00", "location": "Taipei 101"}
    },

    # ========================================================================
    # Category 13: Chain stores
    # ========================================================================
    {"category": "chain_store", "user_message": "Meeting at Starbucks tomorrow at 3pm", "location": "Starbucks"},
    {"category": "chain_store", "user_message": "Going to McDonald's this afternoon", "location": "McDonald's"},

    # ========================================================================
    # Category 14: Context memory
    # ========================================================================
    {
        "category": "context_memory",
        "user_message": "7pm",
        "context": {"_pending_question": "What time?", "_collecting": {"title": "Dinner with Mike", "location": "Xinyi"}},
        "expected_action": "create_schedule"
    },
    {
        "category": "context_memory",
        "user_message": "Yes",
        "context": {"_pending_confirmation": "Confirm meeting at Taipei 101?"},
        "expected_action": "create_schedule"
    },

    # ========================================================================
    # Category 15: Cancel actions
    # ========================================================================
    {
        "category": "cancel_action",
        "user_message": "Never mind",
        "context": {"_pending_action": "create"},
        "expected_action": "reply_to_user",
        "reply": "OK, cancelled."
    },
    {"category": "cancel_action", "user_message": "Forget it", "expected_action": "reply_to_user"},

    # ========================================================================
    # Category 16: Duplicate check
    # ========================================================================
    {
        "category": "duplicate_check",
        "user_message": "Meeting tomorrow at 3pm",
        "context": {"schedule_list": [{"id": "abc", "title": "Meeting", "start_time": "2026-05-09T15:00:00"}]},
        "expected_action": "ask_user",
        "question": "You already have a 'Meeting' tomorrow at 3pm. Create new or modify existing?"
    },

    # ========================================================================
    # Category 17: Overnight schedules
    # ========================================================================
    {
        "category": "overnight",
        "user_message": "Karaoke from 11:30pm tomorrow to 2am",
        "intent": "create",
        "parsed_data": {
            "title": "Karaoke",
            "start_time": "2026-05-09T23:30:00",
            "end_time": "2026-05-10T02:00:00",
            "location": "Karaoke"
        },
        "is_complete": True
    },

    # ========================================================================
    # Category 18: With description
    # ========================================================================
    {
        "category": "with_description",
        "user_message": "Meeting tomorrow at 3pm to discuss Q2 results",
        "intent": "create",
        "parsed_data": {"title": "Meeting", "description": "Discuss Q2 results", "start_time": "2026-05-09T15:00:00"}
    },

    # ========================================================================
    # Category 19: Reminders
    # ========================================================================
    {
        "category": "reminder",
        "user_message": "Remind me about the 3pm meeting tomorrow",
        "intent": "create",
        "expected_action": "create_schedule"
    },

    # ========================================================================
    # Category 20: Recurring
    # ========================================================================
    {
        "category": "recurring",
        "user_message": "Weekly standup every Monday at 9am",
        "intent": "create",
        "expected_action": "ask_user",
        "question": "Recurring schedules aren't supported yet. Create just next Monday's 9am standup?"
    },
]


def stats():
    print(f"EN V1 Total: {len(RAG_TRAINING_DATA_EN)}")


if __name__ == "__main__":
    stats()
