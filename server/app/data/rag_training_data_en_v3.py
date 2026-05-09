"""
RAG Training Dataset (English) V3 - Failure Case Fixes
85 examples targeting real failure modes.

Based on actual test failures:
1. is_complete misjudgment (asking when shouldn't)
2. intent misclassification (edit -> create)
3. query intent recognition ("where is X" is query)
4. Edit verbs identification ("change to X" must be edit)
"""

TODAY = "2026-05-08"

RAG_TRAINING_DATA_EN_V3 = [

    # ========================================================================
    # FIX 1: is_complete=True - Personal schedules don't need participants
    # ========================================================================
    {
        "scenario": "FIX: complete personal schedule shouldn't ask for participants",
        "user_message": "Meeting at Taipei 101 next Friday at 10am",
        "intent": "create",
        "is_complete": True,
        "parsed": {"title": "Meeting", "start_time": "2026-05-15T10:00:00", "end_time": "2026-05-15T11:00:00", "location": "Taipei 101", "participants": []},
        "WRONG_BEHAVIOR": "Asking 'Who are you meeting with?'",
        "CORRECT_BEHAVIOR": "Direct create_schedule, don't ask for participants",
        "rule": "If user doesn't mention 'with', it's a personal schedule. participants=[], don't ask"
    },
    {
        "scenario": "FIX: personal dinner shouldn't ask who",
        "user_message": "Dinner at Xinyi at 7pm tomorrow",
        "intent": "create",
        "is_complete": True,
        "parsed": {"title": "Dinner", "start_time": "2026-05-09T19:00:00", "end_time": "2026-05-09T20:00:00", "location": "Xinyi", "participants": []},
        "rule": "No person + complete time/location → directly create"
    },
    {
        "scenario": "FIX: complete info should be is_complete=True",
        "user_message": "Dinner with friends at Xinyi district at 7pm day after tomorrow",
        "intent": "create",
        "is_complete": True,
        "parsed": {"title": "Dinner", "start_time": "2026-05-10T19:00:00", "location": "Xinyi district", "participants": []},
        "explanation": "'friends' is generic, not specific contact, goes in title not participants",
        "rule": "Generic terms (friends/coworkers/family) go in title, not participants"
    },

    # ========================================================================
    # FIX 2: edit intent recognition - "change/move/reschedule" must be edit
    # ========================================================================
    {"scenario": "FIX: 'change to' must be edit", "user_message": "Change the meeting to 4pm", "intent": "edit", "is_complete": False, "WRONG": "create", "CORRECT": "edit"},
    {"scenario": "FIX: 'change to tomorrow' must be edit", "user_message": "Change to tomorrow", "intent": "edit", "is_complete": False, "expected_action": "ask_user", "question": "Which schedule do you want to change?"},
    {"scenario": "FIX: 'switch location' is edit", "user_message": "Switch location to Starbucks", "intent": "edit", "is_complete": False},
    {"scenario": "FIX: 'reschedule' is edit", "user_message": "Reschedule the meeting to next week", "intent": "edit", "is_complete": False},
    {"scenario": "FIX: 'move' is edit", "user_message": "Move dinner to Saturday", "intent": "edit", "is_complete": False},
    {"scenario": "FIX: 'postpone' is edit", "user_message": "Postpone the meeting by an hour", "intent": "edit", "is_complete": False},
    {"scenario": "FIX: 'bring forward' is edit", "user_message": "Bring the interview forward to morning", "intent": "edit", "is_complete": False},
    {"scenario": "FIX: 'cancel' is delete", "user_message": "Cancel tomorrow's meeting", "intent": "delete", "rule": "'cancel/drop/skip' → delete"},
    {"scenario": "FIX: 'drop' is delete", "user_message": "Drop the dinner plans", "intent": "delete"},
    {"scenario": "FIX: 'update' is edit", "user_message": "Update meeting time to 5pm", "intent": "edit", "is_complete": False},

    # ========================================================================
    # FIX 3: query intent - "where is X" / "when is X"
    # ========================================================================
    {"scenario": "FIX: 'where is X' is query", "user_message": "Where's the meeting?", "intent": "query", "is_complete": False, "WRONG": "create", "rule": "Question word + existing activity → query"},
    {"scenario": "FIX: 'when is X' is query", "user_message": "When's the meeting?", "intent": "query", "is_complete": False},
    {"scenario": "FIX: 'when X' is query", "user_message": "When are we eating?", "intent": "query", "is_complete": False},
    {"scenario": "FIX: 'who X' is query", "user_message": "Who's in tomorrow's meeting?", "intent": "query", "is_complete": False},
    {"scenario": "FIX: 'X at where' is query", "user_message": "Today's meeting at where?", "intent": "query", "is_complete": False},
    {"scenario": "FIX: 'do I have X' is query", "user_message": "Do I have a meeting tomorrow?", "intent": "query", "is_complete": False},
    {"scenario": "FIX: 'what time is X' is query", "user_message": "What time is the interview?", "intent": "query", "is_complete": False},

    # ========================================================================
    # FIX 4: query is_complete=False
    # ========================================================================
    {"scenario": "FIX: query is_complete=False", "user_message": "What's on my schedule?", "intent": "query", "is_complete": False, "WRONG_COMPLETE": True, "rule": "is_complete only matters for create. query → always False"},
    {"scenario": "FIX: weekly query", "user_message": "What's my week looking like?", "intent": "query", "is_complete": False},
    {"scenario": "FIX: specific query", "user_message": "What's tomorrow's meeting about?", "intent": "query", "is_complete": False},

    # ========================================================================
    # FIX 5: Intent priority logic
    # ========================================================================
    {"scenario": "Priority: list match + edit verb → edit", "user_message": "Move dinner with Mike later", "context": {"schedule_list": [{"title": "Dinner with Mike"}]}, "intent": "edit", "rule": "(1) list match + edit verb → edit"},
    {"scenario": "Priority: list empty + create verb → create", "user_message": "Dinner with Mike next Friday", "context": {"schedule_list": []}, "intent": "create", "rule": "(2) list empty + create verb → create"},
    {"scenario": "Priority: explicit 'another' → create", "user_message": "Schedule another lunch with Mike", "context": {"schedule_list": [{"title": "Lunch with Mike"}]}, "intent": "create", "rule": "'another/again' clearly indicates new creation"},

    # ========================================================================
    # FIX 6: Default time for activity types
    # ========================================================================
    {"user_message": "Breakfast tomorrow", "default_time": "08:00:00"},
    {"user_message": "Lunch tomorrow", "default_time": "12:00:00"},
    {"user_message": "Afternoon tea tomorrow", "default_time": "15:00:00"},
    {"user_message": "Dinner tomorrow", "default_time": "19:00:00"},
    {"user_message": "Late night snack tomorrow", "default_time": "22:00:00"},
    {"user_message": "Get-together tomorrow", "default_time": "19:00:00"},
    {"user_message": "Meeting tomorrow", "default_time": "09:00:00"},
    {"user_message": "Workout tomorrow", "default_time": "15:00:00"},
    {"user_message": "Movie tomorrow", "default_time": "19:00:00"},
    {"user_message": "Class tomorrow", "default_time": "09:00:00"},

    # ========================================================================
    # FIX 7: Time of day defaults
    # ========================================================================
    {"input": "morning", "time": "09:00:00"},
    {"input": "late morning", "time": "10:00:00"},
    {"input": "noon", "time": "12:00:00"},
    {"input": "afternoon", "time": "14:00:00"},
    {"input": "early evening", "time": "17:00:00"},
    {"input": "evening", "time": "19:00:00"},
    {"input": "late night", "time": "22:00:00"},
    {"input": "early morning", "time": "06:00:00"},

    # ========================================================================
    # FIX 8: end_time inference
    # ========================================================================
    {"scenario": "default end = start + 2h", "start": "2026-05-09T15:00:00", "end": "2026-05-09T17:00:00"},
    {"scenario": "meal 1-1.5h", "title": "Dinner", "duration": "1.5h"},
    {"scenario": "meeting default 1h", "title": "Meeting", "duration": "1h"},
    {"scenario": "sports 1-2h", "title": "Basketball", "duration": "2h"},
    {"scenario": "movie ~2.5h", "title": "Movie", "duration": "2.5h"},

    # ========================================================================
    # FIX 9: Complex intent chains
    # ========================================================================
    {"scenario": "compound edit: time+location", "user_message": "Move the meeting to next Wednesday at 3pm, change location to Xinyi", "intent": "edit", "expected_action": "update_schedule", "parsed": {"start_time": "2026-05-13T15:00:00", "location": "Xinyi"}},
    {"scenario": "compound edit: time+person", "user_message": "Move dinner to 5pm and add Sarah", "intent": "edit", "parsed": {"start_time": "...T17:00:00", "participants": ["@Sarah"]}},

    # ========================================================================
    # FIX 10: Inferred but incomplete
    # ========================================================================
    {"scenario": "implicit subject: direct create", "user_message": "Meeting at 3pm tomorrow", "intent": "create", "is_complete": False, "missing": ["location"]},
    {"scenario": "time+location+activity, no person → complete", "user_message": "Office meeting at 3pm tomorrow", "intent": "create", "is_complete": True, "rule": "office=location, meeting=activity"},
    {"scenario": "online meeting no location is complete", "user_message": "Online meeting at 3pm tomorrow", "intent": "create", "is_complete": True, "is_online": True},

    # ========================================================================
    # FIX 11: Multi-person meeting judgment
    # ========================================================================
    {"scenario": "explicit multi-person + complete = complete", "user_message": "Meeting with Mike and Sarah at Taipei 101 at 3pm tomorrow", "intent": "create", "is_complete": True, "participants": ["@Mike", "@Sarah"]},
    {"scenario": "explicit multi-person, no location = incomplete", "user_message": "Meeting with Mike and Sarah at 3pm tomorrow", "intent": "create", "is_complete": False, "missing": ["location"]},

    # ========================================================================
    # FIX 12: Common error pattern fixes
    # ========================================================================
    {"scenario": "FIX: title shouldn't have 'going to'", "input": "Going to a movie", "WRONG_TITLE": "Going to a movie", "CORRECT_TITLE": "Movie"},
    {"scenario": "FIX: title shouldn't have 'I'", "input": "I have a meeting", "WRONG_TITLE": "I have a meeting", "CORRECT_TITLE": "Meeting"},
    {"scenario": "FIX: title shouldn't have specific location", "input": "Coffee at Starbucks", "WRONG_TITLE": "Coffee at Starbucks", "CORRECT_TITLE": "Coffee", "CORRECT_LOCATION": "Starbucks"},
    {"scenario": "FIX: description usage", "input": "Meeting at 3pm tomorrow to discuss budget", "title": "Meeting", "description": "Discuss budget", "rule": "'discuss X' goes in description not title"},

    # ========================================================================
    # FIX 13: Multi-turn partial_data accumulation
    # ========================================================================
    {
        "scenario": "multi-turn info accumulation",
        "turns": [
            {"user": "I have an important meeting tomorrow", "ai_partial": {"title": "Important meeting", "start_time": "2026-05-09T09:00:00"}, "ai_question": "What time and where?"},
            {"user": "3pm", "ai_partial": {"title": "Important meeting", "start_time": "2026-05-09T15:00:00"}, "ai_question": "Where?"},
            {"user": "Xinyi 101", "ai_action": "create_schedule", "ai_data": {"title": "Important meeting", "start_time": "2026-05-09T15:00:00", "location": "Xinyi 101"}}
        ],
        "rule": "Each turn's partial_data must include all known fields"
    },

    # ========================================================================
    # FIX 14: Casual confirmation responses
    # ========================================================================
    {"user": "yes", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "yeah", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "yep", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "sure", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "ok", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "confirm", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "no", "context": {"_pending_confirm": True}, "action": "cancel"},
    {"user": "nope", "context": {"_pending_confirm": True}, "action": "cancel"},
    {"user": "never mind", "context": {"_pending_confirm": True}, "action": "cancel"},
    {"user": "let me think", "context": {"_pending_confirm": True}, "action": "wait"},

    # ========================================================================
    # FIX 15: Numeric option selection
    # ========================================================================
    {"user": "1", "context": {"_options_shown": ["A", "B", "C"]}, "action": "select_option_1"},
    {"user": "option 2", "context": {"_options_shown": ["A", "B"]}, "action": "select_option_2"},
    {"user": "the first one", "action": "select_option_1"},

    # ========================================================================
    # FIX 16: Time expression diversity
    # ========================================================================
    {"input": "day after tomorrow", "today": "2026-05-08", "result": "2026-05-10"},
    {"input": "7pm day after tomorrow", "result": "2026-05-10T19:00:00"},
    {"input": "next Friday", "today": "2026-05-08 Fri", "result": "2026-05-15"},
    {"input": "next Friday 10am", "result": "2026-05-15T10:00:00"},
    {"input": "last Wednesday", "today": "2026-05-08 Fri", "result": "2026-05-06"},
    {"input": "15th of next month", "result": "2026-06-15"},
    {"input": "8/15", "result": "2026-08-15"},
    {"input": "Jan 2027", "result": "2027-01-?"},

    # ========================================================================
    # FIX 17: Activity type boundaries
    # ========================================================================
    {"scenario": "pure activity not a schedule", "user_message": "I like to eat", "intent": "out_of_scope", "rule": "Statement without time/location/intent → guidance message"},
    {"scenario": "pure location not a schedule", "user_message": "Taipei 101 is great", "intent": "out_of_scope"},

    # ========================================================================
    # FIX 18: Implicit intent
    # ========================================================================
    {"scenario": "implicit create: date hint", "user_message": "Movie with girlfriend this weekend", "intent": "create", "title": "Movie with girlfriend", "is_complete": False, "missing": ["specific_date", "specific_time", "location"]},
    {"scenario": "implicit create: invitation", "user_message": "Invite Mike for dinner tomorrow", "intent": "create", "title": "Dinner with Mike", "is_complete": False, "missing": ["time_specific", "location"]},
    {"scenario": "implicit query: implied question", "user_message": "I think I have a meeting", "intent": "query"},
]


def stats():
    print(f"EN V3 Total: {len(RAG_TRAINING_DATA_EN_V3)}")


if __name__ == "__main__":
    stats()
