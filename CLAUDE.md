# Schedule Management — CLAUDE.md

## Project Overview
AI-powered schedule management app. Flutter mobile + FastAPI backend + PostgreSQL.
AI chat (LangGraph + Qwen-3-235B via Cerebras) helps users create schedules in Chinese.

## Stack
- **Backend**: FastAPI, SQLModel, PostgreSQL, LangGraph, HERE API, Firebase Admin (FCM)
- **Mobile**: Flutter, Provider, easy_localization, firebase_messaging, url_launcher, geolocator
- **AI**: Cerebras API → `qwen-3-235b-a22b-instruct-2507`, LangGraph StateGraph

## Key Files — Read These Before Editing

| File | Role |
|------|------|
| `server/app/services/ai_service.py` | System prompt, AI call, JSON extraction |
| `server/app/services/schedule_graph.py` | LangGraph: collect_info → validate_location |
| `server/app/services/here_service.py` | Location search pipeline (HERE→Nominatim→Google Places) |
| `server/app/api/endpoints/schedules.py` | Chat endpoint, schedule CRUD |
| `server/app/api/endpoints/users.py` | Auth, FCM token, invitations RSVP |
| `server/app/services/notification_service.py` | Email + FCM push notifications |
| `server/app/services/push_service.py` | Firebase FCM wrapper |
| `mobile/lib/widgets/chat_widget.dart` | AI chat UI, location confirm cards |
| `mobile/lib/screens/home_screen.dart` | Schedule list, cancel dialog |
| `mobile/lib/services/api_service.dart` | All HTTP calls to backend |
| `mobile/lib/providers/auth_provider.dart` | Auth state, FCM token registration |
| `mobile/lib/widgets/app_drawer.dart` | Navigation drawer, invite badge |
| `server/run_migration.py` | DB migrations (run after model changes) |

## Architecture: AI Chat Flow
```
User message
  → POST /schedules/chat
  → if confirm_location=True: skip graph, is_complete=True
  → else: schedule_graph.invoke()
       collect_info_node (AI → JSON)
       → if is_complete & has location: validate_location_node (HERE pipeline)
       → if needs_location_confirm: return early → Flutter shows confirm card
  → if is_complete: create Schedule in DB, return success message
```

## DB Models
- `Schedule`: schedule_id (UUID), user_id, title, meeting_start_time, meeting_end_time, meeting_location, latitude, longitude, status, is_online, contact_id
- `attend`: attend_id, schedule_id, user_id, contact_id, status (P/AT/NG)
- `Contact`: id, user_id, nick_name, phone, email, line_id, contact_user_id
- `User`: user_id, email, full_name, fcm_token, profile_image_path

## Schedule Status Values (ScheduleStatus constants)
`P`=pending, `AT`=attend, `NG`=notGoing, `A`=active, `NA`=notAttended, `C`=cancel, `CS`=comingSoon

## Conventions
- Backend migrations: add column in model → add to `run_migration.py` → run script
- API base: `ApiService.baseUrl` in `mobile/lib/services/api_service.dart`
- Localization keys: `mobile/assets/translations/zh-TW.json` and `en.json`
- Status badge colors: defined in `mobile/lib/widgets/schedule_list_tile.dart`
- No mock DB in tests — real DB only

## Cost-Saving Task Routing

### Use inline (Claude Code direct):
- Editing existing files with clear instructions
- Bug fixes in known files
- Small feature additions (<50 lines)

### Delegate to `Explore` subagent:
- "Find all places where X is used"
- "How does Y work across multiple files"
- "What files reference Z"

### Delegate to `Plan` subagent:
- New feature design spanning 3+ files
- Architecture decisions

### Offload to Gemini CLI (`gemini` command):
- Reading/summarizing long log files
- Explaining third-party library behavior
- Generating boilerplate (migration scripts, test data)
- Large file analysis that doesn't need editing

## Common Pitfalls (Do Not Repeat)
- Do NOT re-invoke `process_conversation` when `confirm_location=True` — confuses the model
- Do NOT use `autofocus: true` in AlertDialog — breaks Chinese IME; use `addPostFrameCallback` + `FocusNode`
- Do NOT use `in=countryCode:TWN` for HERE API — use `in=circle:23.9,120.9;r=250000`
- Do NOT mock DB in tests
- HERE search may return wrong city coordinates — always run `_coords_match_address()` sanity check
