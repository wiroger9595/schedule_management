# macOS Push Notifications Setup Guide

This guide walks you through enabling push notifications (FCM) on macOS for multi-device reminder support.

## Step 1: Install Firebase Pods

Run this in the `mobile/macos/` directory:

```bash
cd mobile/macos
pod install --repo-update
```

This installs the Firebase pods listed in `pubspec.yaml` (firebase_core, firebase_messaging, device_info_plus, package_info_plus).

## Step 2: Configure Entitlements

Update the following files to enable push notifications:

### `mobile/macos/Runner/DebugProfile.entitlements`

Add this key:
```xml
<key>aps-environment</key>
<string>development</string>
```

### `mobile/macos/Runner/Release.entitlements`

Add this key:
```xml
<key>aps-environment</key>
<string>production</string>
```

## Step 3: Update Info.plist

Edit `mobile/macos/Runner/Info.plist` and add:

```xml
<key>UIBackgroundModes</key>
<array>
  <string>remote-notification</string>
</array>
```

## Step 4: Enable Push Notifications in Xcode (REQUIRED)

1. Open `mobile/macos/Runner.xcodeproj` in Xcode
2. Select the "Runner" target
3. Go to **Signing & Capabilities** tab
4. Click **+ Capability**
5. Search for "Push Notifications" and add it
6. Ensure your **Team ID** is set correctly

## Step 5: Register a Separate macOS App in Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** → **Apps**
4. Click **Add App** → **macOS**
5. Use a distinct bundle ID for macOS (e.g., `com.example.scheduleManagement.macos` instead of the iOS bundle ID)
6. Download the `GoogleService-Info.plist` for the macOS app
7. Replace `mobile/macos/Runner/GoogleService-Info.plist` with this new file

## Step 6: Update Firebase Configuration

Run this in the `mobile/` directory to regenerate firebase_options.dart with the new macOS app credentials:

```bash
flutterfire configure --platforms macos
```

This updates `mobile/lib/firebase_options.dart` with the correct macOS app ID and API keys.

## Step 7: Verify Setup

Test the setup by running the app:

```bash
cd mobile
flutter run -d macos
```

You should see:
- No Firebase initialization errors in the console
- `[Startup] Reminder scheduler initialized` message from the backend (after logging in)
- FCM tokens being registered for this device

## Troubleshooting

**"No Firebase App has been created"**: Firebase.initializeApp() wasn't called. Check that `mobile/lib/main.dart` has the initialization.

**Push notifications not arriving**: 
- Verify Xcode Push Notifications capability is enabled
- Check that the Firebase app was registered separately for macOS (not reusing iOS bundle ID)
- Run `pod install --repo-update` to ensure Firebase pods are installed
- Check the backend logs for push send failures

**aps-environment not recognized**: The entitlements file may be cached. Clean Xcode build folder (Cmd+Shift+K) and rebuild.

## What This Enables

After completing these steps:
- Users can be logged into the same account on iPhone and MacBook
- When a schedule time arrives, **both devices** receive a departure reminder push notification
- The reminder time is adjusted based on the user's selected transportation mode (car, transit, walk, etc.)
- Users see a notification like: "是時候出發了 🚗 | Meeting @ 15:00 (estimated 25 min drive)"

## Note on Multi-Device Support

The backend automatically:
- Stores FCM tokens per device (via `user_devices` table)
- Computes departure reminder time when a schedule is created/updated
- Sends push notifications to ALL registered devices for that user
- Tracks device platform (iOS/macOS) for platform-specific notification handling
