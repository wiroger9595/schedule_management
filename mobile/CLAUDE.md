# Mobile — CLAUDE.md

## Flutter Patterns
- State management: `Provider` (`ChangeNotifier`) — auth state in `AuthProvider`
- HTTP calls: all go through `ApiService` singleton (`lib/services/api_service.dart`)
- Localization: `easy_localization`, keys in `assets/translations/zh-TW.json` + `en.json`
- Theme: `lib/theme/` — use theme colors, not hardcoded

## Key Screens
| Screen | Path |
|--------|------|
| Home (schedule list) | `lib/screens/home_screen.dart` |
| AI Chat | `lib/widgets/chat_widget.dart` |
| Calendar | `lib/screens/calendar_screen.dart` |
| Todo | `lib/screens/todo_list_screen.dart` |
| Map / Navigation | `lib/screens/map_screen.dart` |
| Invitations (RSVP) | `lib/screens/invitations_screen.dart` |
| Location Picker | `lib/screens/location_picker_screen.dart` |
| Profile | `lib/screens/profile_screen.dart` |
| Settings | `lib/screens/settings_screen.dart` |

## Key Widgets
| Widget | Purpose |
|--------|---------|
| `chat_widget.dart` | AI chat, location confirm cards, conflict cards |
| `app_drawer.dart` | Navigation drawer with invite badge |
| `schedule_list_tile.dart` | Schedule card with attendee avatars |
| `user_avatar.dart` | Profile image with fallback initials |

## ApiService Key Methods
```dart
chatWithAI(message, {currentContext, conversationHistory, forceCreate, confirmLocation, latitude, longitude})
getSchedules() → List<Map>
searchPlaces(query, {lat, lon}) → List<Map>
updateFcmToken(token)
getMyInvitations() → List
respondToInvitation(attendId, action) // action: 'accept' | 'decline'
```

## Chat Widget State
- `_currentContext`: Map sent back to backend each turn (schedule data so far)
- `_conversationHistory`: List of {role, content} — full AI conversation
- `_isLoading`: disables input while waiting
- `forceCreate: true` + `confirmLocation: true` → tells backend to skip AI and create schedule

## Location Confirm Flow
1. Backend returns `needs_location_confirm=true`
2. If `location_candidates.length > 1` → show `LocationCandidatesMessage`
3. If single match → show `LocationConfirmMessage` with confirm/reject buttons
4. Confirm → `_sendMessage(forceCreate: true, overrideLat, overrideLon)`
5. Reject → clear `_currentContext['location']`, re-ask AI

## Dialog / IME Fix Pattern
For dialogs needing Chinese text input:
```dart
class _MyDialogState extends State<MyDialog> {
  final _focusNode = FocusNode();
  
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus(); // After frame — IME ready
    });
  }
}
```
Do NOT use `autofocus: true` in AlertDialog — breaks Chinese IME.

## Adding a New Screen
1. Create `lib/screens/new_screen.dart`
2. Add route in `lib/routes/` or `main.dart`
3. Add `ListTile` to `app_drawer.dart` if needed
4. Add localization key to both translation files

## FCM Token
- Registered after login/googleLogin/appleLogin in `AuthProvider._registerFcmToken()`
- Saved to backend via `ApiService.updateFcmToken()`
- Used by backend to send push notifications on invite
