"""EN RAG Training Data — all entries follow correct format: category/user_message/intent/is_complete/parsed_data"""

RAG_TRAINING_DATA_EN = [
    # ============================================================
    # create_complete — all info present, create directly
    # ============================================================
    {   'category': 'create_complete',
        'user_message': 'Meeting with John at Taipei 101 tomorrow at 3pm',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Meeting with John',
            'start_time': '2026-05-09T15:00:00',
            'end_time': '2026-05-09T17:00:00',
            'location': 'Taipei 101',
            'participants': ['@John'],
            '_correction_note': 'Time + location + person + activity all complete → is_complete=True, call create_schedule'}},
    {   'category': 'create_complete',
        'user_message': 'Dinner with friends at Xinyi District the day after tomorrow at 7pm',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Dinner with friends',
            'start_time': '2026-05-10T19:00:00',
            'end_time': '2026-05-10T21:00:00',
            'location': 'Xinyi District',
            'participants': [],
            '_correction_note': '"friends" is generic not a specific contact → put in title, participants=[], do not ask'}},
    {   'category': 'create_complete',
        'user_message': 'Morning standup at the office next Monday at 9am',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Morning standup',
            'start_time': '2026-05-11T09:00:00',
            'end_time': '2026-05-11T10:00:00',
            'location': 'office',
            'participants': [],
            '_correction_note': '"office" is a location, standup defaults to 1h'}},
    {   'category': 'create_complete',
        'user_message': 'Basketball at 4pm today',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Basketball',
            'start_time': '2026-05-08T16:00:00',
            'end_time': '2026-05-08T18:00:00',
            '_correction_note': 'Sports activities require a location → is_complete=False, ask_user for location'}},
    {   'category': 'create_complete',
        'user_message': 'Lunch with colleagues tomorrow at noon',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Lunch with colleagues',
            'start_time': '2026-05-09T12:00:00',
            'end_time': '2026-05-09T13:00:00',
            '_correction_note': 'noon → 12:00, eating requires location → ask_user for location'}},

    # ============================================================
    # create_partial — incomplete info, need to ask
    # ============================================================
    {   'category': 'create_partial',
        'user_message': 'Meeting tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Meeting',
            'start_time': '2026-05-09T09:00:00',
            '_correction_note': 'meeting defaults to 09:00, missing location → ask_user "What time and where?"'}},
    {   'category': 'create_partial',
        'user_message': 'Coffee with Mike this afternoon',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Coffee with Mike',
            'start_time': '2026-05-08T14:00:00',
            'participants': ['@Mike'],
            '_correction_note': 'afternoon → 14:00 default, missing location → ask_user "Where?"'}},
    {   'category': 'create_partial',
        'user_message': 'Family dinner on Friday',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Family dinner',
            'start_time': '2026-05-15T19:00:00',
            '_correction_note': 'dinner → 19:00 default, missing location → ask_user'}},

    # ============================================================
    # time_parsing — time expression parsing
    # ============================================================
    {   'category': 'time_parsing',
        'user_message': 'tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'TODAY+1', '_correction_note': 'tomorrow = today+1 day, compute dynamically, never hardcode'}},
    {   'category': 'time_parsing',
        'user_message': 'day after tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'TODAY+2', '_correction_note': 'day after tomorrow = today+2 days, compute dynamically'}},
    {   'category': 'time_parsing',
        'user_message': 'next Monday',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'NEXT_MONDAY', '_correction_note': 'next Monday = find the date of the next Monday, compute dynamically'}},
    {   'category': 'time_parsing',
        'user_message': 'this Saturday',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'THIS_SATURDAY', '_correction_note': 'this Saturday = the Saturday of the current week, compute dynamically'}},
    {   'category': 'time_parsing',
        'user_message': 'next Friday',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'NEXT_FRIDAY', '_correction_note': 'next Friday = the next upcoming Friday, compute dynamically'}},
    {   'category': 'time_parsing',
        'user_message': 'in 3 days',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'TODAY+3', '_correction_note': 'in 3 days = today+3, compute dynamically'}},
    {   'category': 'time_parsing',
        'user_message': '3pm',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'T15:00:00', '_correction_note': '3pm = 15:00'}},
    {   'category': 'time_parsing',
        'user_message': '7:30pm',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'T19:30:00', '_correction_note': '7:30pm = 19:30'}},
    {   'category': 'time_parsing',
        'user_message': 'evening',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'T19:00:00', '_correction_note': 'evening defaults to 19:00'}},
    {   'category': 'time_parsing',
        'user_message': 'midnight',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'T00:00:00', '_correction_note': 'midnight = 00:00'}},
    {   'category': 'time_parsing',
        'user_message': 'noon',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'T12:00:00', '_correction_note': 'noon = 12:00'}},
    {   'category': 'time_parsing',
        'user_message': 'May 20th at 4pm',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': '2026-05-20T16:00:00', '_correction_note': 'explicit date+time'}},
    {   'category': 'time_parsing',
        'user_message': 'in 2 hours',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {'start_time': 'now+2h', '_correction_note': 'relative current time +2h'}},

    # ============================================================
    # edit — modify schedule
    # ============================================================
    {   'category': 'edit',
        'user_message': 'Move the meeting to 4pm',
        'intent': 'edit',
        'is_complete': True,
        'context': {'schedule_list': [{'id': 'abc-123', 'title': 'Meeting', 'start_time': '2026-05-09T09:00:00'}]},
        'parsed_data': {
            'schedule_id': 'abc-123',
            'start_time': '2026-05-09T16:00:00',
            '_correction_note': 'Only update start_time (preserve original date), do not touch other fields'}},
    {   'category': 'edit',
        'user_message': 'Change the dinner location to Starbucks',
        'intent': 'edit',
        'is_complete': True,
        'context': {'schedule_list': [{'id': 'xyz', 'title': 'Dinner with Mike', 'location': "McDonald's"}]},
        'parsed_data': {
            'schedule_id': 'xyz',
            'location': 'Starbucks',
            '_correction_note': 'Only modify location, do not change other fields'}},
    {   'category': 'edit',
        'user_message': 'Add @Sarah',
        'intent': 'edit',
        'is_complete': True,
        'context': {
            '_pending_edit_schedule_id': 'abc',
            'schedule_list': [{'id': 'abc', 'title': 'Dinner', 'participants': ['@Mike']}]},
        'parsed_data': {
            'schedule_id': 'abc',
            'participants': ['@Sarah'],
            '_correction_note': 'Add new participant, do not replace existing list'}},
    {   'category': 'edit',
        'user_message': 'Remove @Mike',
        'intent': 'edit',
        'is_complete': True,
        'context': {'schedule_list': [{'id': 'abc', 'title': 'Dinner', 'participants': ['@Mike', '@Sarah']}]},
        'parsed_data': {
            'schedule_id': 'abc',
            'remove_participants': ['@Mike'],
            '_correction_note': 'Use remove_participants rather than participants'}},
    {   'category': 'edit',
        'user_message': 'Remove everyone',
        'intent': 'edit',
        'is_complete': True,
        'parsed_data': {
            'clear_participants': True,
            '_correction_note': 'Clear all with clear_participants=True'}},
    {   'category': 'edit',
        'user_message': 'Change it to later',
        'intent': 'edit',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': '"later" is too vague → ask_user "What time would you like to change it to?"'}},
    {   'category': 'edit',
        'user_message': 'Change to 9am',
        'intent': 'edit',
        'is_complete': True,
        'context': {'schedule_list': [{'id': 'abc', 'title': 'Meeting', 'start_time': '2026-05-09T15:00:00'}]},
        'parsed_data': {
            'schedule_id': 'abc',
            'start_time': '2026-05-09T09:00:00',
            '_correction_note': 'Keep original date 2026-05-09, only replace time with 09:00'}},

    # ============================================================
    # delete — delete schedule
    # ============================================================
    {   'category': 'delete',
        'user_message': 'Delete the meeting',
        'intent': 'delete',
        'is_complete': True,
        'context': {'schedule_list': [{'id': 'abc', 'title': 'Meeting'}]},
        'parsed_data': {
            'schedule_id': 'abc',
            '_correction_note': 'Unique match, delete directly'}},
    {   'category': 'delete',
        'user_message': "Cancel tomorrow's meeting",
        'intent': 'delete',
        'is_complete': True,
        'parsed_data': {
            '_correction_note': '"Cancel" also means delete intent'}},
    {   'category': 'delete',
        'user_message': "I'm not going",
        'intent': 'delete',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': 'Context unclear → ask_user "Which schedule do you want to cancel?"'}},
    {   'category': 'delete',
        'user_message': 'Delete all schedules with Mike',
        'intent': 'delete',
        'is_complete': False,
        'context': {'schedule_list': [{'id': 'a', 'title': 'Lunch with Mike'}, {'id': 'b', 'title': 'Meeting with Mike'}]},
        'parsed_data': {
            '_correction_note': 'Multiple matches → must list options: "1️⃣ Lunch with Mike 2️⃣ Meeting with Mike, delete all or specific?"'}},

    # ============================================================
    # query — query schedules
    # ============================================================
    {   'category': 'query',
        'user_message': "What's on my schedule",
        'intent': 'query',
        'is_complete': False,
        'parsed_data': {'_correction_note': 'Query all schedules → reply_to_user with list; query is_complete always False'}},
    {   'category': 'query',
        'user_message': "What do I have tomorrow",
        'intent': 'query',
        'is_complete': False,
        'parsed_data': {'_correction_note': 'Query schedules for specific date'}},
    {   'category': 'query',
        'user_message': "When is the meeting",
        'intent': 'query',
        'is_complete': False,
        'parsed_data': {'_correction_note': 'Query specific schedule time'}},

    # ============================================================
    # duplicate_contact — contacts with same name
    # ============================================================
    {   'category': 'duplicate_contact',
        'user_message': 'Lunch with Mike tomorrow',
        'intent': 'create',
        'is_complete': False,
        'context': {
            'duplicate_contacts': [
                {'name': 'Mike', 'comment': 'colleague', 'phone_last4': '1234'},
                {'name': 'Mike', 'comment': 'friend', 'phone_last4': '5678'}]},
        'parsed_data': {
            'title': 'Lunch with Mike',
            '_correction_note': 'Duplicate names → must ask_user: "Which Mike?\n1️⃣ Mike (colleague) last 4: 1234\n2️⃣ Mike (friend) last 4: 5678" — never guess'}},
    {   'category': 'duplicate_contact',
        'user_message': '1',
        'intent': 'create',
        'is_complete': True,
        'context': {'_pending_duplicate': 'Mike'},
        'parsed_data': {
            '_correction_note': 'User selected by number → use corresponding contact and continue creating'}},

    # ============================================================
    # online_meeting — online meetings
    # ============================================================
    {   'category': 'online_meeting',
        'user_message': 'Online meeting tomorrow at 3pm',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Online meeting',
            'start_time': '2026-05-09T15:00:00',
            'is_online': True,
            '_correction_note': 'is_online=True does not need location, call create_schedule directly'}},
    {   'category': 'online_meeting',
        'user_message': 'Zoom call with the team tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Team Zoom call',
            'is_online': True,
            '_correction_note': 'Online meeting but missing time → ask_user for time'}},

    # ============================================================
    # out_of_scope — outside service scope
    # ============================================================
    {   'category': 'out_of_scope',
        'user_message': "What's the weather today",
        'intent': 'out_of_scope',
        'is_complete': True,
        'parsed_data': {
            'reply': "I'm a schedule management assistant, specialized in helping you plan, modify and manage your schedules 📅 Do you have any schedules to plan?",
            '_correction_note': 'Not schedule-related → reply_to_user with standard redirect'}},
    {   'category': 'out_of_scope',
        'user_message': 'Recommend a song',
        'intent': 'out_of_scope',
        'is_complete': True,
        'parsed_data': {
            'reply': "I'm a schedule management assistant, specialized in helping you plan, modify and manage your schedules 📅 Do you have any schedules to plan?",
            '_correction_note': 'Not schedule-related'}},
    {   'category': 'out_of_scope',
        'user_message': 'Hello',
        'intent': 'out_of_scope',
        'is_complete': True,
        'parsed_data': {
            'reply': "Hello! I'm your schedule assistant. How can I help you plan your day?",
            '_correction_note': 'Greeting → short response + guidance'}},
    {   'category': 'out_of_scope',
        'user_message': 'Calculate 100*200',
        'intent': 'out_of_scope',
        'is_complete': True,
        'parsed_data': {'_correction_note': 'Not schedule-related → reply_to_user redirect'}},
    {   'category': 'out_of_scope',
        'user_message': 'Thank you',
        'intent': 'out_of_scope',
        'is_complete': True,
        'parsed_data': {'reply': "You're welcome! Let me know if you need anything. 😊", '_correction_note': 'Polite response, keep short'}},
    {   'category': 'out_of_scope',
        'user_message': 'Goodbye',
        'intent': 'out_of_scope',
        'is_complete': True,
        'parsed_data': {'reply': 'Goodbye! Feel free to reach out anytime 👋', '_correction_note': 'Polite farewell, keep short'}},

    # ============================================================
    # edge_case — boundary cases
    # ============================================================
    {   'category': 'edge_case',
        'user_message': 'Dinner with both Tom and Jerry tomorrow at 5pm',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Dinner with Tom and Jerry',
            'start_time': '2026-05-09T17:00:00',
            'participants': ['@Tom', '@Jerry'],
            '_correction_note': 'Still missing location → ask_user'}},
    {   'category': 'edge_case',
        'user_message': 'Go to airport next month on the 15th',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Airport',
            'start_time': '2026-06-15T09:00:00',
            '_correction_note': 'Need to ask which airport and specific time'}},
    {   'category': 'edge_case',
        'user_message': 'Change to Starbucks',
        'intent': 'edit',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': 'Missing target schedule → ask_user "Which schedule do you want to change the location for?"'}},
    {   'category': 'edge_case',
        'user_message': 'Add another one',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': 'Unclear intent → ask_user "What schedule would you like to add?"'}},

    # ============================================================
    # title_inference — title inference rules
    # ============================================================
    {   'category': 'title_inference',
        'user_message': 'Dinner tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Dinner',
            '_correction_note': 'No person name → title is simply the activity'}},
    {   'category': 'title_inference',
        'user_message': 'Dinner with Mike tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Dinner with Mike',
            'participants': ['@Mike'],
            '_correction_note': 'With person → title is "Activity with X"'}},
    {   'category': 'title_inference',
        'user_message': 'Watch a movie tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Watch movie',
            '_correction_note': 'Use activity name directly'}},
    {   'category': 'title_inference',
        'user_message': 'Client meeting at Grand Hyatt tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Client meeting',
            'location': 'Grand Hyatt',
            '_correction_note': 'title does not include location, location goes in separate field'}},
    {   'category': 'title_inference',
        'user_message': "See the doctor tomorrow",
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Doctor appointment',
            '_correction_note': '"See the doctor" → title is "Doctor appointment"'}},

    # ============================================================
    # edit — location change then follow-up time
    # ============================================================
    {   'category': 'edit',
        'user_message': 'Sure, change it to 4pm',
        'intent': 'edit',
        'is_complete': True,
        'context': {
            '_pending_edit_schedule_id': 'xyz',
            '_last_question': 'Do you also want to adjust the time?',
            'schedule_list': [{'id': 'xyz', 'title': 'Lunch with Mike', 'start_time': '2026-05-09T12:00:00', 'location': 'Starbucks'}]},
        'parsed_data': {
            'schedule_id': 'xyz',
            'start_time': '2026-05-09T16:00:00',
            '_correction_note': 'Location was already updated in previous round, this round only changes time; ⚠️ do NOT bring back location'}},
    {   'category': 'edit',
        'user_message': 'No, keep the same time',
        'intent': 'edit',
        'is_complete': True,
        'context': {
            '_pending_edit_schedule_id': 'xyz',
            '_last_question': 'Do you also want to adjust the time?',
            'schedule_list': [{'id': 'xyz', 'title': 'Lunch with Mike', 'start_time': '2026-05-09T12:00:00', 'location': 'Starbucks'}]},
        'parsed_data': {
            'reply': 'Got it, your schedule has been updated ✅',
            '_correction_note': 'User confirms time stays → reply_to_user, do not call update_schedule again'}},
    {   'category': 'edit',
        'user_message': 'Yes',
        'intent': 'edit',
        'is_complete': False,
        'context': {
            '_pending_edit_schedule_id': 'xyz',
            '_last_question': 'Do you also want to adjust the time? (that schedule is in the past)',
            'schedule_list': [{'id': 'xyz', 'title': 'Lunch with Mike', 'start_time': '2026-05-01T12:00:00', 'location': 'Starbucks'}]},
        'parsed_data': {
            '_correction_note': '⚠️ Received "Yes/Sure/OK" but missing new time value → ask_user "What time would you like to change it to?", do NOT call update_schedule, do NOT say "update complete"'}},
    {   'category': 'edit',
        'user_message': 'I want to change it',
        'intent': 'edit',
        'is_complete': False,
        'context': {
            '_pending_edit_schedule_id': 'xyz',
            '_last_question': 'Do you also want to adjust the time?',
            'schedule_list': [{'id': 'xyz', 'title': 'Meeting', 'start_time': '2026-05-01T09:00:00'}]},
        'parsed_data': {
            '_correction_note': '"I want to change it" expresses intent but no time value → keep asking "What time would you like to change it to?", do not declare complete'}},

    # ============================================================
    # multi_edit — modify multiple fields at once
    # ============================================================
    {   'category': 'multi_edit',
        'user_message': 'Change to 9am and move it to Starbucks',
        'intent': 'edit',
        'is_complete': True,
        'parsed_data': {
            'start_time': 'FILL_IN_DATE_T09:00:00',
            'location': 'Starbucks',
            '_correction_note': 'Send all changes in one update call'}},
    {   'category': 'multi_edit',
        'user_message': 'Move the meeting to next Thursday at 2pm at Taipei 101',
        'intent': 'edit',
        'is_complete': True,
        'parsed_data': {
            'start_time': '2026-05-14T14:00:00',
            'location': 'Taipei 101',
            '_correction_note': 'Time + location changed simultaneously'}},

    # ============================================================
    # chain_store — chain brand locations
    # ============================================================
    {   'category': 'chain_store',
        'user_message': 'Meeting at Starbucks tomorrow at 3pm',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Meeting',
            'start_time': '2026-05-09T15:00:00',
            'location': 'Starbucks',
            '_correction_note': 'Chain brand: use brand name directly, location system finds nearest branch; ⚠️ do NOT ask "Which branch?"'}},
    {   'category': 'chain_store',
        'user_message': "Let's go to McDonald's this afternoon",
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'location': "McDonald's",
            '_correction_note': "⚠️ Do NOT ask 'Which location?' — use brand name directly"}},

    # ============================================================
    # context_memory — multi-turn conversation context
    # ============================================================
    {   'category': 'context_memory',
        'user_message': '7pm',
        'intent': 'create',
        'is_complete': True,
        'context': {'_pending_question': 'What time?', '_collecting': {'title': 'Dinner with Mike', 'location': 'Xinyi'}},
        'parsed_data': {
            'title': 'Dinner with Mike',
            'start_time': 'FILL_IN_DATE_T19:00:00',
            'location': 'Xinyi',
            '_correction_note': 'User provides missing time, combine with collected info to create'}},
    {   'category': 'context_memory',
        'user_message': 'Yes',
        'intent': 'create',
        'is_complete': True,
        'context': {'_pending_confirmation': 'Confirm meeting at Taipei 101?'},
        'parsed_data': {
            '_correction_note': 'Affirmative response → execute pending action (create_schedule)'}},

    # ============================================================
    # cancel_action — cancel operation
    # ============================================================
    {   'category': 'cancel_action',
        'user_message': 'Never mind',
        'intent': 'out_of_scope',
        'is_complete': True,
        'context': {'_pending_action': 'create'},
        'parsed_data': {
            'reply': 'Okay, cancelled.',
            '_correction_note': 'User abandons → reply_to_user "Okay, cancelled." do not execute'}},
    {   'category': 'cancel_action',
        'user_message': "Forget it",
        'intent': 'out_of_scope',
        'is_complete': True,
        'parsed_data': {
            'reply': 'Okay, cancelled.',
            '_correction_note': 'Similar to "Never mind" → reply_to_user'}},

    # ============================================================
    # duplicate_check — time conflict confirmation
    # ============================================================
    {   'category': 'duplicate_check',
        'user_message': 'Meeting tomorrow at 3pm',
        'intent': 'create',
        'is_complete': False,
        'context': {'schedule_list': [{'id': 'abc', 'title': 'Meeting', 'start_time': '2026-05-09T15:00:00'}]},
        'parsed_data': {
            '_correction_note': 'Time conflict → ask_user "You already have a Meeting at 3pm tomorrow. Create a new one or modify the existing?"'}},

    # ============================================================
    # overnight — overnight schedule
    # ============================================================
    {   'category': 'overnight',
        'user_message': 'Karaoke from 11:30pm tomorrow to 2am the day after',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Karaoke',
            'start_time': '2026-05-09T23:30:00',
            'end_time': '2026-05-10T02:00:00',
            '_correction_note': 'Overnight schedule: end_time moves to next day; still missing location'}},

    # ============================================================
    # with_description — includes description field
    # ============================================================
    {   'category': 'with_description',
        'user_message': 'Meeting tomorrow at 3pm to discuss Q2 results',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Meeting',
            'description': 'Discuss Q2 results',
            'start_time': '2026-05-09T15:00:00',
            '_correction_note': '"to discuss X" goes in description not title; still missing location'}},

    # ============================================================
    # reminder — reminder creation
    # ============================================================
    {   'category': 'reminder',
        'user_message': 'Remind me about the meeting at 3pm tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Meeting',
            'start_time': '2026-05-09T15:00:00',
            '_correction_note': '"Remind me" also means create schedule; still missing location'}},

    # ============================================================
    # recurring — recurring schedule
    # ============================================================
    {   'category': 'recurring',
        'user_message': 'Team standup every Monday at 9am',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': "Recurring schedules not supported for auto-creation → ask_user \"Auto-repeat is not supported yet. Would you like to create next Monday's 9am standup first?\""}},

    # ============================================================
    # scenario activities — daily activity scenarios
    # ============================================================
    {   'category': 'create_partial',
        'user_message': 'Breakfast tomorrow at 8am',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Breakfast',
            'start_time': '2026-05-09T08:00:00',
            'end_time': '2026-05-09T09:30:00',
            '_correction_note': 'breakfast defaults to 08:00, duration 1.5h; still missing location → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Brunch on Saturday',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Brunch',
            'start_time': '2026-05-09T11:00:00',
            '_correction_note': 'brunch defaults to 11:00; still missing location'}},
    {   'category': 'create_partial',
        'user_message': 'Afternoon tea with Sarah',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Afternoon tea with Sarah',
            'start_time': '2026-05-08T15:00:00',
            'participants': ['@Sarah'],
            '_correction_note': 'Still missing location → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Late night snack at 10pm tonight',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Late night snack',
            'start_time': '2026-05-08T22:00:00',
            '_correction_note': 'Still missing location'}},
    {   'category': 'create_complete',
        'user_message': "New Year's Eve dinner on 12/31",
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': "New Year's Eve Dinner",
            'start_time': '2026-12-31T19:00:00',
            '_correction_note': 'Still missing location'}},
    {   'category': 'create_partial',
        'user_message': 'Company year-end party next month',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Company Year-End Party',
            '_correction_note': 'Missing specific date and location → ask_user'}},
    {   'category': 'create_partial',
        'user_message': "Mike's wedding next month on the 15th",
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            "title": "Mike's wedding",
            'start_time': '2026-06-15T12:00:00',
            '_correction_note': 'Wedding defaults to noon; still missing location'}},
    {   'category': 'create_partial',
        'user_message': 'Google interview at 3pm',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Google interview',
            'start_time': '2026-05-08T15:00:00',
            '_correction_note': 'Still missing location (venue or online link) → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Presentation on Wednesday morning',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Presentation',
            'start_time': '2026-05-13T09:00:00',
            '_correction_note': 'Still missing location'}},
    {   'category': 'create_partial',
        'user_message': 'Client visit tomorrow to meet with Mr. Wang',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Client visit - Mr. Wang',
            'start_time': '2026-05-09T09:00:00',
            '_correction_note': 'Still missing location → ask_user'}},
    {   'category': 'online_meeting',
        'user_message': 'Phone conference at 4pm',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Phone conference',
            'start_time': '2026-05-08T16:00:00',
            'is_online': True,
            '_correction_note': 'Phone/video conference is_online=True, no location needed'}},
    {   'category': 'create_partial',
        'user_message': 'Business trip to Kaohsiung next week',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Business trip to Kaohsiung',
            'location': 'Kaohsiung',
            '_correction_note': 'Missing specific date → ask_user "Which day next week?"'}},
    {   'category': 'create_partial',
        'user_message': '1-on-1 with manager tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': '1-on-1 with manager',
            'participants': ['@manager'],
            '_correction_note': 'Missing time and location → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Weekly meeting on Monday',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Weekly meeting',
            'start_time': '2026-05-11T09:00:00',
            '_correction_note': 'Still missing location; meeting defaults to 09:00'}},
    {   'category': 'create_partial',
        'user_message': 'Yoga tomorrow morning at 7am',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Yoga',
            'start_time': '2026-05-09T07:00:00',
            '_correction_note': 'Still missing location → ask_user'}},
    {   'category': 'create_complete',
        'user_message': 'Running at Riverside Park at 6pm',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Running',
            'location': 'Riverside Park',
            'start_time': '2026-05-08T18:00:00',
            'end_time': '2026-05-08T20:00:00'}},
    {   'category': 'create_complete',
        'user_message': 'Gym at 8pm tonight',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Gym',
            'location': 'gym',
            'start_time': '2026-05-08T20:00:00',
            'end_time': '2026-05-08T22:00:00'}},
    {   'category': 'create_partial',
        'user_message': 'Swimming on Saturday noon',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Swimming',
            'start_time': '2026-05-09T12:00:00',
            '_correction_note': 'Still missing location (which pool) → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Badminton with colleagues tomorrow afternoon',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Badminton with colleagues',
            'start_time': '2026-05-09T15:00:00',
            '_correction_note': 'Still missing location → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Movie tonight',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Movie',
            'start_time': '2026-05-08T19:00:00',
            '_correction_note': 'Still missing location (which cinema) → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Concert on May 20th',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Concert',
            'start_time': '2026-05-20T19:00:00',
            '_correction_note': 'Still missing location → ask_user'}},
    {   'category': 'create_complete',
        'user_message': 'Shopping at Xinyi tomorrow',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Shopping',
            'location': 'Xinyi',
            'start_time': '2026-05-09T14:00:00',
            'end_time': '2026-05-09T17:00:00'}},
    {   'category': 'create_partial',
        'user_message': 'Karaoke tonight',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Karaoke',
            'start_time': '2026-05-08T21:00:00',
            '_correction_note': 'Still missing location → ask_user'}},
    {   'category': 'create_complete',
        'user_message': 'Hiking at Elephant Mountain this Sunday',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Hiking',
            'location': 'Elephant Mountain',
            'start_time': '2026-05-10T09:00:00',
            'end_time': '2026-05-10T12:00:00'}},
    {   'category': 'create_partial',
        'user_message': 'Art exhibition next weekend',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Art exhibition',
            '_correction_note': 'Missing specific date and location → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Dentist appointment tomorrow at 2pm',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Dentist appointment',
            'start_time': '2026-05-09T14:00:00',
            '_correction_note': 'Still missing location (which clinic) → ask_user'}},
    {   'category': 'create_partial',
        'user_message': 'Health checkup next Thursday morning',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Health checkup',
            'start_time': '2026-05-14T09:00:00',
            '_correction_note': 'Still missing location → ask_user'}},
    {   'category': 'create_complete',
        'user_message': 'Flight from Taoyuan Airport next Tuesday at 8am',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Flight',
            'location': 'Taoyuan Airport',
            'start_time': '2026-05-12T08:00:00'}},
    {   'category': 'create_partial',
        'user_message': 'Trip to Japan next month',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Japan trip',
            '_correction_note': 'Missing specific date → ask_user "Which date next month are you departing?"'}},

    # ============================================================
    # missing info scenarios
    # ============================================================
    {   'category': 'create_partial',
        'user_message': 'Schedule something for me',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': 'No info at all → ask_user "What schedule would you like to create? Please provide the time, location, and activity."'}},
    {   'category': 'create_partial',
        'user_message': 'I want to eat',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': 'Only activity intent → ask_user "When, with whom, and where would you like to eat?"'}},
    {   'category': 'create_partial',
        'user_message': 'Tomorrow afternoon',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': 'Only time given → ask_user "What would you like to do tomorrow afternoon?"'}},
    {   'category': 'create_partial',
        'user_message': 'At Taipei 101',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': 'Only location given → ask_user "What are you doing at Taipei 101 and when?"'}},

    # ============================================================
    # FORBIDDEN behaviors — counter-examples for teaching
    # ============================================================
    {   'category': 'edge_case',
        'user_message': 'Change to 11am the day after tomorrow',
        'intent': 'edit',
        'is_complete': True,
        'context': {'_pending_edit_schedule_id': 'abc', '_collecting': {'location': 'Dajia Riverside Basketball Court'}},
        'parsed_data': {
            'schedule_id': 'abc',
            'start_time': 'FILL_IN_DAY_AFTER_TOMORROW_T11:00:00',
            '_correction_note': '⚠️ Only update explicitly mentioned fields → do NOT bring back location "Dajia Riverside Basketball Court"'}},
    {   'category': 'edge_case',
        'user_message': "Go to my friend's place",
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': "⚠️ Do NOT use contact's home as location: WRONG=location \"friend's place\"; CORRECT=ask_user \"What's the address?\""}},
    {   'category': 'edge_case',
        'user_message': "Change Mike's meeting to later",
        'intent': 'edit',
        'is_complete': False,
        'context': {'schedule_list': [{'id': 'a', 'title': 'Lunch with Mike'}, {'id': 'b', 'title': 'Meeting with Mike'}]},
        'parsed_data': {
            '_correction_note': '⚠️ Multiple matches: WRONG=auto-pick schedule_id=a; CORRECT=ask_user "1️⃣ Lunch with Mike 2️⃣ Meeting with Mike, which one?"'}},
    {   'category': 'title_inference',
        'user_message': 'Coffee at Starbucks tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Coffee',
            'location': 'Starbucks',
            '_correction_note': '⚠️ Title should not include location: WRONG="Coffee at Starbucks"; CORRECT=title "Coffee" + location "Starbucks"'}},

    # ============================================================
    # time_parsing — time format rules
    # ============================================================
    {   'category': 'time_parsing',
        'user_message': '2pm to 4pm meeting',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Meeting',
            'start_time': '2026-05-08T14:00:00',
            'end_time': '2026-05-08T16:00:00',
            '_correction_note': 'Explicit duration, use directly'}},
    {   'category': 'time_parsing',
        'user_message': 'Saturday morning hike',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Hike',
            'start_time': '2026-05-09T09:00:00',
            'end_time': '2026-05-09T12:00:00',
            '_correction_note': 'Half day duration → end_time = 12:00'}},
    {   'category': 'time_parsing',
        'user_message': 'All-day conference next Monday',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Conference',
            'start_time': '2026-05-11T09:00:00',
            'end_time': '2026-05-11T18:00:00',
            '_correction_note': 'All-day → 09:00-18:00'}},

    # ============================================================
    # edit — preserve original date/time rules
    # ============================================================
    {   'category': 'edit',
        'user_message': 'Change to 9am',
        'intent': 'edit',
        'is_complete': True,
        'context': {'schedule_list': [{'id': 'abc', 'start_time': '2027-04-09T15:00:00'}]},
        'parsed_data': {
            'schedule_id': 'abc',
            'start_time': '2027-04-09T09:00:00',
            "_correction_note": "⚠️ Keep original date 2027-04-09, only change time; WRONG=use today's date 2026-05-08"}},
    {   'category': 'edit',
        'user_message': 'Change to May 20th',
        'intent': 'edit',
        'is_complete': True,
        'context': {'schedule_list': [{'id': 'abc', 'start_time': '2027-04-09T15:00:00'}]},
        'parsed_data': {
            'schedule_id': 'abc',
            'start_time': '2027-05-20T15:00:00',
            '_correction_note': 'Keep original time 15:00, only change date'}},

    # ============================================================
    # FIX — is_complete correct determination
    # ============================================================
    {   'category': 'create_complete',
        'user_message': 'Meeting at Taipei 101 next Friday at 10am',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Meeting',
            'start_time': '2026-05-15T10:00:00',
            'end_time': '2026-05-15T11:00:00',
            'location': 'Taipei 101',
            'participants': [],
            '_correction_note': '⚠️ User did not mention "with whom" → personal schedule, participants=[], do NOT ask "Who is the meeting with?"'}},
    {   'category': 'create_complete',
        'user_message': 'Dinner at Xinyi tomorrow at 7pm',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Dinner',
            'start_time': '2026-05-09T19:00:00',
            'end_time': '2026-05-09T20:00:00',
            'location': 'Xinyi',
            'participants': [],
            '_correction_note': 'No person + complete time+location → create directly, no questions'}},
    {   'category': 'create_complete',
        'user_message': 'Dinner with friends in Xinyi the day after tomorrow at 7pm',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Dinner',
            'start_time': '2026-05-10T19:00:00',
            'end_time': '2026-05-10T21:00:00',
            'location': 'Xinyi',
            'participants': [],
            '_correction_note': '"friends" is generic not specific contact → put in title, participants=[], do not put in participants'}},

    # ============================================================
    # FIX — intent correct classification
    # ============================================================
    {   'category': 'edit',
        'user_message': 'Move the meeting to 4pm',
        'intent': 'edit',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': '⚠️ Verb "move/change/reschedule/update" + existing schedule type → intent=edit; WRONG=create'}},
    {   'category': 'edit',
        'user_message': 'Reschedule to tomorrow',
        'intent': 'edit',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': '"Reschedule" → edit intent, missing target → ask_user "Which schedule?"'}},
    {   'category': 'edit',
        'user_message': 'Move the location to Starbucks',
        'intent': 'edit',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': '"Move to/Change to" also edit'}},
    {   'category': 'edit',
        'user_message': 'Push the meeting back to next week',
        'intent': 'edit',
        'is_complete': False,
        'parsed_data': {'_correction_note': '"Push back" = edit'}},
    {   'category': 'edit',
        'user_message': 'Bring the dinner forward to 5pm',
        'intent': 'edit',
        'is_complete': False,
        'parsed_data': {'_correction_note': '"Bring forward" = edit'}},
    {   'category': 'delete',
        'user_message': "Cancel tomorrow's meeting",
        'intent': 'delete',
        'is_complete': True,
        'parsed_data': {'_correction_note': '"Cancel/remove/delete" → delete'}},
    {   'category': 'query',
        'user_message': 'Where is the meeting',
        'intent': 'query',
        'is_complete': False,
        'parsed_data': {
            '_correction_note': '⚠️ Question words "where/when/who/what time" + existing activity → intent=query, WRONG=create'}},
    {   'category': 'query',
        'user_message': 'When is the meeting',
        'intent': 'query',
        'is_complete': False,
        'parsed_data': {'_correction_note': 'Question → query'}},
    {   'category': 'query',
        'user_message': 'What time is dinner',
        'intent': 'query',
        'is_complete': False,
        'parsed_data': {'_correction_note': 'Question → query'}},
    {   'category': 'query',
        'user_message': 'Do I have anything tomorrow',
        'intent': 'query',
        'is_complete': False,
        'parsed_data': {'_correction_note': 'Question → query'}},
    {   'category': 'query',
        'user_message': 'What do I have this week',
        'intent': 'query',
        'is_complete': False,
        'parsed_data': {'_correction_note': 'Query this week schedules'}},

    # ============================================================
    # ambiguity priority
    # ============================================================
    {   'category': 'edit',
        'user_message': 'Move dinner with Mike to later',
        'intent': 'edit',
        'is_complete': False,
        'context': {'schedule_list': [{'title': 'Dinner with Mike'}]},
        'parsed_data': {
            '_correction_note': '(1) List has match + modify verb → edit; ask_user "What time?"'}},
    {   'category': 'create',
        'user_message': 'Lunch with Mike next Friday',
        'intent': 'create',
        'is_complete': False,
        'context': {'schedule_list': []},
        'parsed_data': {
            'title': 'Lunch with Mike',
            '_correction_note': '(2) Empty list + create verb → create'}},
    {   'category': 'create',
        'user_message': 'Schedule another lunch with Mike',
        'intent': 'create',
        'is_complete': False,
        'context': {'schedule_list': [{'title': 'Lunch with Mike'}]},
        'parsed_data': {
            'title': 'Lunch with Mike',
            '_correction_note': '"Another/one more" explicitly means create new, even if list has a match'}},

    # ============================================================
    # activity default times — fixed format
    # ============================================================
    {'category': 'time_parsing', 'user_message': 'Breakfast tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Breakfast', 'start_time': 'TODAY+1T08:00:00', 'end_time': 'TODAY+1T09:30:00',
                     '_correction_note': 'breakfast defaults to 08:00, end_time +1.5h; still missing location'}},
    {'category': 'time_parsing', 'user_message': 'Lunch tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Lunch', 'start_time': 'TODAY+1T12:00:00', 'end_time': 'TODAY+1T13:30:00',
                     '_correction_note': 'lunch defaults to 12:00, end_time +1.5h; still missing location'}},
    {'category': 'time_parsing', 'user_message': 'Afternoon tea tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Afternoon tea', 'start_time': 'TODAY+1T15:00:00', 'end_time': 'TODAY+1T16:30:00',
                     '_correction_note': 'afternoon tea defaults to 15:00, end_time +1.5h'}},
    {'category': 'time_parsing', 'user_message': 'Dinner tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Dinner', 'start_time': 'TODAY+1T19:00:00', 'end_time': 'TODAY+1T20:30:00',
                     '_correction_note': 'dinner defaults to 19:00, end_time +1.5h; still missing location'}},
    {'category': 'time_parsing', 'user_message': 'Meeting tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Meeting', 'start_time': 'TODAY+1T09:00:00', 'end_time': 'TODAY+1T10:00:00',
                     '_correction_note': 'meeting defaults to 09:00, end_time +1h; still missing location'}},
    {'category': 'time_parsing', 'user_message': 'Exercise tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Exercise', 'start_time': 'TODAY+1T15:00:00', 'end_time': 'TODAY+1T17:00:00',
                     '_correction_note': 'exercise defaults to 15:00, end_time +2h; still missing location'}},
    {'category': 'time_parsing', 'user_message': 'Movie tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Movie', 'start_time': 'TODAY+1T19:00:00', 'end_time': 'TODAY+1T21:30:00',
                     '_correction_note': 'movie defaults to 19:00, end_time +2.5h; still missing location'}},
    {'category': 'time_parsing', 'user_message': 'Class tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Class', 'start_time': 'TODAY+1T09:00:00', 'end_time': 'TODAY+1T11:00:00',
                     '_correction_note': 'class defaults to 09:00, end_time +2h; still missing location'}},
    # time period defaults
    {'category': 'time_parsing', 'user_message': 'Morning appointment',
     'intent': 'create', 'is_complete': False,
     'parsed_data': {'start_time': 'T09:00:00', '_correction_note': '"morning" defaults to 09:00'}},
    {'category': 'time_parsing', 'user_message': 'Late morning meeting',
     'intent': 'create', 'is_complete': False,
     'parsed_data': {'start_time': 'T10:00:00', '_correction_note': '"late morning" defaults to 10:00'}},
    {'category': 'time_parsing', 'user_message': 'Midday meeting',
     'intent': 'create', 'is_complete': False,
     'parsed_data': {'start_time': 'T12:00:00', '_correction_note': '"midday/noon" defaults to 12:00'}},
    {'category': 'time_parsing', 'user_message': 'Afternoon workout',
     'intent': 'create', 'is_complete': False,
     'parsed_data': {'start_time': 'T14:00:00', '_correction_note': '"afternoon" defaults to 14:00'}},
    {'category': 'time_parsing', 'user_message': 'Evening dinner',
     'intent': 'create', 'is_complete': False,
     'parsed_data': {'start_time': 'T19:00:00', '_correction_note': '"evening" defaults to 19:00'}},
    {'category': 'time_parsing', 'user_message': 'Late night party',
     'intent': 'create', 'is_complete': False,
     'parsed_data': {'start_time': 'T22:00:00', '_correction_note': '"late night" defaults to 22:00'}},
    # duration defaults
    {'category': 'time_parsing', 'user_message': 'Movie at 3pm tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Movie', 'start_time': 'TODAY+1T15:00:00', 'end_time': 'TODAY+1T17:30:00',
                     '_correction_note': 'movie defaults to 2.5h; end_time = start + 2.5h'}},
    {'category': 'time_parsing', 'user_message': 'Meeting at 3pm tomorrow at the office', 'intent': 'create', 'is_complete': True,
     'parsed_data': {'title': 'Meeting', 'start_time': 'TODAY+1T15:00:00', 'end_time': 'TODAY+1T16:00:00',
                     'location': 'office', '_correction_note': 'meeting defaults to 1h; end_time = start + 1h'}},
    {'category': 'time_parsing', 'user_message': 'Basketball at 4pm tomorrow', 'intent': 'create', 'is_complete': False,
     'parsed_data': {'title': 'Basketball', 'start_time': 'TODAY+1T16:00:00', 'end_time': 'TODAY+1T18:00:00',
                     '_correction_note': 'sports defaults to 2h; end_time = start + 2h; still missing location'}},

    # ============================================================
    # compound edits
    # ============================================================
    {   'category': 'multi_edit',
        'user_message': 'Move the meeting to next Wednesday at 3pm and change venue to Xinyi',
        'intent': 'edit',
        'is_complete': True,
        'parsed_data': {
            'start_time': '2026-05-13T15:00:00',
            'location': 'Xinyi',
            '_correction_note': 'Send all changes in one update'}},
    {   'category': 'multi_edit',
        'user_message': 'Change dinner to 5pm and add Sarah',
        'intent': 'edit',
        'is_complete': True,
        'parsed_data': {
            'start_time': 'FILL_IN_DATE_T17:00:00',
            'participants': ['@Sarah'],
            '_correction_note': 'Time + participant changed simultaneously'}},

    # ============================================================
    # is_complete supplementary scenarios
    # ============================================================
    {   'category': 'create_partial',
        'user_message': 'Meeting at 3pm tomorrow',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Meeting',
            'start_time': '2026-05-09T15:00:00',
            '_correction_note': 'Missing location → is_complete=False, ask_user'}},
    {   'category': 'create_complete',
        'user_message': 'Meeting at the office at 3pm tomorrow',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Meeting',
            'start_time': '2026-05-09T15:00:00',
            'end_time': '2026-05-09T16:00:00',
            'location': 'office',
            '_correction_note': 'office = location, meeting = activity → is_complete=True'}},
    {   'category': 'online_meeting',
        'user_message': 'Online meeting at 3pm tomorrow',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Online meeting',
            'start_time': '2026-05-09T15:00:00',
            'is_online': True,
            '_correction_note': 'Online meeting with no location is still complete → is_complete=True'}},

    # ============================================================
    # title correction rules
    # ============================================================
    {   'category': 'title_inference',
        'user_message': 'Go see a movie',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Movie',
            '_correction_note': '⚠️ Title should not include "go": WRONG="Go see a movie"; CORRECT="Movie"'}},
    {   'category': 'title_inference',
        'user_message': 'I need to have a meeting',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Meeting',
            '_correction_note': '⚠️ Title should not include "I need to": CORRECT="Meeting"'}},
    {   'category': 'title_inference',
        'user_message': 'Coffee at Starbucks',
        'intent': 'create',
        'is_complete': True,
        'parsed_data': {
            'title': 'Coffee',
            'location': 'Starbucks',
            '_correction_note': '⚠️ Title should not include specific location: WRONG="Coffee at Starbucks"; CORRECT=title "Coffee" + location "Starbucks"'}},
    {   'category': 'with_description',
        'user_message': 'Meeting at 3pm tomorrow to discuss the budget',
        'intent': 'create',
        'is_complete': False,
        'parsed_data': {
            'title': 'Meeting',
            'description': 'Discuss the budget',
            'start_time': '2026-05-09T15:00:00',
            '_correction_note': '"to discuss X" goes in description not title; still missing location'}},

    # ============================================================
    # confirmation word quick reference
    # ============================================================
    {   'category': 'context_memory', 'user_message': 'Sure',
        'intent': 'create', 'is_complete': True,
        'context': {'_pending_confirm': True},
        'parsed_data': {'_correction_note': 'Affirmative + pending confirm → execute'}},
    {   'category': 'context_memory', 'user_message': 'OK',
        'intent': 'create', 'is_complete': True,
        'context': {'_pending_confirm': True},
        'parsed_data': {'_correction_note': 'Affirmative + pending confirm → execute'}},
    {   'category': 'context_memory', 'user_message': 'Sounds good',
        'intent': 'create', 'is_complete': True,
        'context': {'_pending_confirm': True},
        'parsed_data': {'_correction_note': 'Affirmative + pending confirm → execute'}},
    {   'category': 'cancel_action', 'user_message': 'No',
        'intent': 'out_of_scope', 'is_complete': True,
        'context': {'_pending_confirm': True},
        'parsed_data': {'_correction_note': 'Negative + pending confirm → cancel'}},
    {   'category': 'cancel_action', 'user_message': 'Let me think about it',
        'intent': 'out_of_scope', 'is_complete': True,
        'context': {'_pending_confirm': True},
        'parsed_data': {'_correction_note': 'Hesitation → wait, do not execute'}},
]
