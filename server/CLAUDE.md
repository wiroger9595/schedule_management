# Backend — CLAUDE.md

## FastAPI Patterns
- Routes in `app/api/endpoints/`, registered in `app/api/router.py`
- DB session via `Depends(get_session)` — never create sessions manually
- Auth via `Depends(get_current_user)` — returns `User` object
- Pydantic schemas in `app/schemas/`, SQLModel models in `app/models/`
- Repository pattern: all DB queries go through `*Repository` classes in `app/repositories/`

## Adding a New Endpoint
1. Add Pydantic schema to `app/schemas/`
2. Add route to existing endpoint file (or new file in `app/api/endpoints/`)
3. Register in `app/api/router.py` if new file

## Adding a DB Column
1. Add field to SQLModel in `app/models/`
2. Add `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` to `run_migration.py`
3. Run: `python run_migration.py`

## AI Service (`ai_service.py`)
- Model: `zai-glm-4.7` via Cerebras
- `process_conversation(messages, context)` → returns dict with `is_complete`, `title`, `start_time`, `end_time`, `location`, `participants`
- Always strip markdown code fences before `json.loads()`
- Time rule: if user says "下午六點" with no date → use today's date, don't ask

## LangGraph (`schedule_graph.py`)
- `ScheduleState(TypedDict)`: input fields + output fields
- Node `collect_info_node` → calls AI
- Node `validate_location_node` → calls HERE pipeline
- Router `route_after_collect`: only goes to validate_location when `is_complete=True` AND location present
- Singleton: `schedule_graph = _build_graph()`

## HERE Service (`here_service.py`)
- `search_places_enhanced(query, lat, lon)` → 4-layer: Taiwan-wide HERE + proximity HERE + Nominatim + Google Places
- `validate_location(name, lat, lon)` → returns `(result, needs_confirm, candidates)`
- `_coords_match_address(address, lat, lon)` → city bbox sanity check
- Taiwan-wide search: `in=circle:23.9,120.9;r=250000` (NOT countryCode)
- Google Places requires `GOOGLE_PLACES_API_KEY` env var

## Push Notifications (`push_service.py`)
- `push_service.send(token, title, body, data)` → never raises, returns bool
- Firebase initialized from `FIREBASE_SERVICE_ACCOUNT_JSON` env var (JSON string) or `GOOGLE_APPLICATION_CREDENTIALS` (file path)

## Subscription / AI Quota (`billing.py`)
- free：每月 `FREE_MONTHLY_AI_QUOTA` 次（預設 5），Redis key `ai:quota:{user_id}:{YYYY-MM}`
- pro：用戶自帶 OpenAI 相容端點（BYOK），不計次
- `ai_quota_service.resolve_for_chat(user)` → chat endpoint 唯一守門員，AI 回應後才 `consume`
- `byok_service.normalize_base_url()` 擋內網位址（SSRF），存檔前 `verify_credentials()` 實打一次
- plan 由 RevenueCat 維護：`POST /billing/webhook`（即時）+ `POST /billing/sync`（對帳）
- `CANCELLATION` 不收回權益，等 `EXPIRATION`

## Environment Variables
```
DATABASE_URL, SECRET_KEY, CEREBRAS_API_KEY
HERE_API_KEY, GOOGLE_PLACES_API_KEY
FIREBASE_SERVICE_ACCOUNT_JSON (or GOOGLE_APPLICATION_CREDENTIALS)
AI_KEY_ENC_SECRET            # 加密用戶 API key，未設則退回 JWT_SECRET_KEY
FREE_MONTHLY_AI_QUOTA        # 預設 5
REVENUECAT_WEBHOOK_AUTH      # RevenueCat 後台設的 Authorization header 值
REVENUECAT_SECRET_KEY        # REST API 對帳用（sk_...）
REVENUECAT_ENTITLEMENT_ID    # 預設 pro
```
