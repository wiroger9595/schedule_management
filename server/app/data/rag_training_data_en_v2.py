"""
RAG Training Dataset (English) V2 - Extended Real-world Scenarios
71 examples covering activity types and casual expressions.
"""

TODAY = "2026-05-08"  # Friday

RAG_TRAINING_DATA_EN_V2 = [

    # ========================================================================
    # A. Food & Dining
    # ========================================================================
    {"scenario": "breakfast", "user_message": "Breakfast at 8am tomorrow", "title": "Breakfast", "start_time": "2026-05-09T08:00:00", "needs_location": True},
    {"scenario": "brunch", "user_message": "Brunch on Saturday", "title": "Brunch", "start_time": "2026-05-09T11:00:00"},
    {"scenario": "afternoon tea", "user_message": "Afternoon tea with Sarah", "title": "Afternoon tea with Sarah", "start_time": "2026-05-08T15:00:00", "participants": ["@Sarah"]},
    {"scenario": "late night snack", "user_message": "Late night snack at 10pm", "title": "Late night snack", "start_time": "2026-05-08T22:00:00"},
    {"scenario": "new year eve", "user_message": "NYE dinner on 12/31", "title": "NYE dinner", "start_time": "2026-12-31T19:00:00"},
    {"scenario": "company party", "user_message": "Company holiday party next month", "title": "Company holiday party", "needs_specific_time": True},
    {"scenario": "wedding", "user_message": "Mike's wedding on June 15", "title": "Mike's wedding", "start_time": "2026-06-15T12:00:00"},

    # ========================================================================
    # B. Work
    # ========================================================================
    {"scenario": "interview", "user_message": "Google interview at 3pm today", "title": "Google interview", "start_time": "2026-05-08T15:00:00", "needs_location": True},
    {"scenario": "presentation", "user_message": "Presentation Wednesday morning", "title": "Presentation", "start_time": "2026-05-13T09:00:00"},
    {"scenario": "client visit", "user_message": "Visit client Mr. Wang tomorrow", "title": "Visit client Mr. Wang", "start_time": "2026-05-09T09:00:00", "needs_location": True},
    {"scenario": "phone call", "user_message": "Phone call at 4pm", "title": "Phone call", "start_time": "2026-05-08T16:00:00", "is_online": True},
    {"scenario": "business trip", "user_message": "Business trip to Kaohsiung next week", "title": "Kaohsiung business trip", "location": "Kaohsiung", "needs_specific_date": True},
    {"scenario": "1on1", "user_message": "1on1 with manager tomorrow", "title": "1on1 with manager", "participants": ["@manager"], "needs_specific_time": True},
    {"scenario": "weekly meeting", "user_message": "Weekly meeting Monday", "title": "Weekly meeting", "start_time": "2026-05-11T09:00:00"},

    # ========================================================================
    # C. Sports & Fitness
    # ========================================================================
    {"scenario": "yoga", "user_message": "Yoga at 7am tomorrow", "title": "Yoga", "start_time": "2026-05-09T07:00:00", "needs_location": True},
    {"scenario": "running", "user_message": "Run at 6pm at Riverside Park", "title": "Run", "location": "Riverside Park", "start_time": "2026-05-08T18:00:00"},
    {"scenario": "gym", "user_message": "Gym at 8pm", "title": "Gym", "location": "Gym", "start_time": "2026-05-08T20:00:00"},
    {"scenario": "swimming", "user_message": "Swimming Saturday noon", "title": "Swimming", "start_time": "2026-05-09T12:00:00", "needs_location": True},
    {"scenario": "badminton", "user_message": "Badminton with coworkers tomorrow afternoon", "title": "Badminton with coworkers", "start_time": "2026-05-09T15:00:00", "needs_location": True},

    # ========================================================================
    # D. Entertainment
    # ========================================================================
    {"scenario": "movie", "user_message": "Movie tonight", "title": "Movie", "start_time": "2026-05-08T19:00:00", "needs_location": True},
    {"scenario": "concert", "user_message": "Jay Chou concert May 20", "title": "Jay Chou concert", "start_time": "2026-05-20T19:00:00", "needs_location": True},
    {"scenario": "shopping", "user_message": "Shopping at Xinyi tomorrow", "title": "Shopping", "location": "Xinyi", "start_time": "2026-05-09T14:00:00"},
    {"scenario": "karaoke", "user_message": "Karaoke tonight", "title": "Karaoke", "start_time": "2026-05-08T21:00:00", "needs_location": True},
    {"scenario": "hiking", "user_message": "Hiking Elephant Mountain Sunday with friends", "title": "Hiking Elephant Mountain", "location": "Elephant Mountain", "start_time": "2026-05-10T09:00:00"},
    {"scenario": "exhibition", "user_message": "Exhibition next weekend", "title": "Exhibition", "needs_specific_date": True},

    # ========================================================================
    # E. Healthcare
    # ========================================================================
    {"scenario": "dentist", "user_message": "Dentist tomorrow at 2pm", "title": "Dentist", "start_time": "2026-05-09T14:00:00", "needs_location": True},
    {"scenario": "checkup", "user_message": "Health checkup Thursday morning", "title": "Health checkup", "start_time": "2026-05-14T09:00:00", "needs_location": True},
    {"scenario": "appointment", "user_message": "Cardiology appointment Friday", "title": "Cardiology appointment", "start_time": "2026-05-15T09:00:00", "needs_location": True},

    # ========================================================================
    # F. Travel
    # ========================================================================
    {"scenario": "flight", "user_message": "Flight from Taoyuan Airport at 8am next Tuesday", "title": "Flight", "location": "Taoyuan Airport", "start_time": "2026-05-12T08:00:00"},
    {"scenario": "high speed rail", "user_message": "HSR to Taichung at 2pm tomorrow", "title": "HSR to Taichung", "start_time": "2026-05-09T14:00:00"},
    {"scenario": "vacation", "user_message": "Japan trip next month", "title": "Japan trip", "needs_specific_date": True},

    # ========================================================================
    # G. Ambiguous - must ask_user
    # ========================================================================
    {"scenario": "no info", "user_message": "Set up a schedule for me", "expected_action": "ask_user", "question": "What schedule? Please provide time, location, and activity."},
    {"scenario": "activity only", "user_message": "Want to eat", "expected_action": "ask_user", "question": "When, with whom, and where?"},
    {"scenario": "time only", "user_message": "Tomorrow afternoon", "expected_action": "ask_user", "question": "What would you like to do tomorrow afternoon?"},
    {"scenario": "location only", "user_message": "At Taipei 101", "expected_action": "ask_user", "question": "What at Taipei 101? When?"},
    {"scenario": "ambiguous time", "user_message": "Meeting later", "expected_action": "ask_user", "question": "What time?"},

    # ========================================================================
    # H. Multi-turn dialogues
    # ========================================================================
    {
        "scenario": "missing time first turn",
        "turn1_user": "Dinner with Mike tomorrow",
        "turn1_response": "What time and where?",
        "turn1_partial": {"title": "Dinner with Mike", "participants": ["@Mike"]},
        "turn2_user": "7pm at Xinyi",
        "expected_final": {"title": "Dinner with Mike", "start_time": "2026-05-09T19:00:00", "location": "Xinyi", "participants": ["@Mike"]}
    },
    {
        "scenario": "missing location first turn",
        "turn1_user": "Basketball next Friday at 6pm",
        "turn1_response": "Where do you want to play?",
        "turn1_partial": {"title": "Basketball", "start_time": "2026-05-15T18:00:00"},
        "turn2_user": "Tianmu Sports Center",
        "expected_final": {"title": "Basketball", "start_time": "2026-05-15T18:00:00", "location": "Tianmu Sports Center"}
    },
    {
        "scenario": "user changes mind",
        "turn1_user": "Meeting at 3pm tomorrow",
        "turn1_response": "OK, where?",
        "turn2_user": "Actually make it 4pm",
        "expected_action": "update_partial_data",
        "explanation": "Mid-creation time change → update partial_data, NOT update_schedule"
    },

    # ========================================================================
    # I. Forbidden patterns
    # ========================================================================
    {
        "scenario": "FORBIDDEN: copy old location to update",
        "context": {"_pending_edit_schedule_id": "abc", "_collecting": {"location": "Old Court"}},
        "user_message": "Change to 11am day after tomorrow",
        "WRONG": {"start_time": "...", "location": "Old Court"},
        "CORRECT": {"schedule_id": "abc", "start_time": "..."},
        "explanation": "Only update explicitly mentioned fields"
    },
    {
        "scenario": "FORBIDDEN: update_schedule mid-creation",
        "context": {"_collecting": {"title": "Dinner with Sam"}},
        "user_message": "10pm",
        "WRONG": {"action": "update_schedule"},
        "CORRECT": {"action": "ask_user", "partial_data": {"title": "...", "start_time": "..T22:00"}}
    },
    {
        "scenario": "FORBIDDEN: title contains location",
        "user_message": "Coffee at Starbucks tomorrow",
        "WRONG": {"title": "Coffee at Starbucks"},
        "CORRECT": {"title": "Coffee", "location": "Starbucks"}
    },
    {
        "scenario": "FORBIDDEN: contact name as location",
        "user_message": "Going to Mike's place tomorrow",
        "WRONG": {"location": "Mike's place"},
        "CORRECT": {"action": "ask_user", "question": "What's Mike's address?"}
    },
    {
        "scenario": "FORBIDDEN: guess when multiple matches",
        "user_message": "Move the one with Mike to 8pm",
        "context": {"schedule_list": [{"id": "a", "title": "Lunch with Mike"}, {"id": "b", "title": "Meeting with Mike"}]},
        "WRONG": {"action": "update_schedule", "schedule_id": "a"},
        "CORRECT": {"action": "ask_user", "options": ["1️⃣ Lunch with Mike", "2️⃣ Meeting with Mike"]}
    },

    # ========================================================================
    # J. Casual / abbreviated expressions
    # ========================================================================
    {"expression": "tmrw", "meaning": "tomorrow", "parsed": "2026-05-09"},
    {"expression": "tonite", "meaning": "tonight", "parsed": "today T19:00"},
    {"expression": "this weekend", "parsed": "2026-05-09 to 2026-05-10"},
    {"expression": "next weekend", "parsed": "2026-05-16 to 2026-05-17"},
    {"expression": "morning", "parsed": "T09:00"},
    {"expression": "EOW (end of week)", "parsed": "2026-05-08 to 2026-05-10"},
    {"expression": "EOM (end of month)", "parsed": "2026-05-31"},

    # ========================================================================
    # K. Various time formats
    # ========================================================================
    {"input": "15:00", "parsed": "T15:00:00"},
    {"input": "3:00pm", "parsed": "T15:00:00"},
    {"input": "3 PM", "parsed": "T15:00:00"},
    {"input": "3 in the afternoon", "parsed": "T15:00:00"},
    {"input": "8:30pm", "parsed": "T20:30:00"},
    {"input": "20:30", "parsed": "T20:30:00"},
    {"input": "half past 8", "parsed": "T08:30:00"},

    # ========================================================================
    # L. Duration
    # ========================================================================
    {"scenario": "explicit duration", "user_message": "Meeting from 2pm to 4pm tomorrow", "start_time": "2026-05-09T14:00:00", "end_time": "2026-05-09T16:00:00"},
    {"scenario": "half day", "user_message": "Hiking Saturday morning", "start_time": "2026-05-09T09:00:00", "end_time": "2026-05-09T12:00:00"},
    {"scenario": "all day", "user_message": "All day meeting on Monday", "start_time": "2026-05-11T09:00:00", "end_time": "2026-05-11T18:00:00"},

    # ========================================================================
    # M. Time edits - preserve original
    # ========================================================================
    {
        "scenario": "preserve original date",
        "context": {"schedule_list": [{"id": "abc", "start_time": "2027-04-09T15:00:00"}]},
        "user_message": "Change to 9am",
        "CORRECT": {"start_time": "2027-04-09T09:00:00"},
        "WRONG": {"start_time": f"{TODAY}T09:00:00"}
    },
    {
        "scenario": "preserve original time",
        "context": {"schedule_list": [{"id": "abc", "start_time": "2027-04-09T15:00:00"}]},
        "user_message": "Change to May 20",
        "CORRECT": {"start_time": "2027-05-20T15:00:00"}
    },

    # ========================================================================
    # N. Complete dialogue flows
    # ========================================================================
    {
        "dialogue_id": "complete_flow_1",
        "turns": [
            {"user": "I have a meeting tomorrow", "ai_action": "ask_user", "ai_q": "What time, with whom, where?"},
            {"user": "2pm with client Mr. Wang", "ai_partial": {"title": "Meeting with client Mr. Wang", "start_time": "2026-05-09T14:00:00", "participants": ["@Mr. Wang"]}, "ai_q": "Where?"},
            {"user": "Our office conference room", "ai_action": "create_schedule"}
        ]
    },
    {
        "dialogue_id": "edit_flow_1",
        "turns": [
            {"user": "What's on my schedule?", "ai_action": "reply_to_user"},
            {"user": "Move the meeting later", "ai_action": "ask_user", "ai_q": "What time?"},
            {"user": "4pm", "ai_action": "update_schedule"}
        ]
    },

    # ========================================================================
    # O. Out of scope - extended
    # ========================================================================
    {"out_of_scope": "Calculate 100*200", "expected": "redirect"},
    {"out_of_scope": "Translate this", "expected": "redirect"},
    {"out_of_scope": "Recommend a restaurant", "expected": "redirect"},
    {"out_of_scope": "What's your name?", "expected": "polite_then_redirect"},
    {"out_of_scope": "Thanks", "expected": "polite_short"},
    {"out_of_scope": "Bye", "expected": "polite_short"},
]


def stats():
    print(f"EN V2 Total: {len(RAG_TRAINING_DATA_EN_V2)}")


if __name__ == "__main__":
    stats()
