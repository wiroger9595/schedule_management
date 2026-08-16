import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest.dart' as tz;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'dart:convert';
import '../screens/invitations_screen.dart';
import '../screens/main_shell.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();

  /// 由 main() 注入，避免 service 反向 import main.dart
  GlobalKey<NavigatorState>? navigatorKey;

  Future<void> init({GlobalKey<NavigatorState>? navigatorKey}) async {
    this.navigatorKey = navigatorKey;
    if (kIsWeb) return; // Web does not support these native initializations
    tz.initializeTimeZones();

    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    const DarwinInitializationSettings initializationSettingsDarwin =
        DarwinInitializationSettings(
      requestSoundPermission: true,
      requestBadgePermission: true,
      requestAlertPermission: true,
    );

    const InitializationSettings initializationSettings = InitializationSettings(
      android: initializationSettingsAndroid,
      iOS: initializationSettingsDarwin,
      macOS: initializationSettingsDarwin,
    );

    await flutterLocalNotificationsPlugin.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: (response) {
        final payload = response.payload;
        if (payload == null || payload.isEmpty) return;
        _routeFromData(Map<String, dynamic>.from(jsonDecode(payload) as Map));
      },
    );

    // Request permissions for Android 13+
    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

    // Set up Firebase Messaging handlers
    _setupFirebaseMessaging();
  }

  void _setupFirebaseMessaging() {
    // Handle foreground messages (app is in focus)
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      _handleForegroundMessage(message);
    });

    // App was in background and the user tapped the notification
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      _handleMessageOpenedApp(message);
    });

    // App was terminated and launched by a notification tap — onMessageOpenedApp
    // never fires for this case, the message is only available here once.
    FirebaseMessaging.instance.getInitialMessage().then((message) {
      if (message == null) return;
      // 延到第一個 frame 之後，此時 navigator 才掛好
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _handleMessageOpenedApp(message);
      });
    });
  }

  void _handleForegroundMessage(RemoteMessage message) {
    // When app is in foreground, show a local notification
    if (message.notification != null) {
      showLocalNotification(
        title: message.notification!.title ?? 'Notification',
        body: message.notification!.body ?? '',
        data: message.data,
      );
    }
  }

  void _handleMessageOpenedApp(RemoteMessage message) {
    _routeFromData(message.data);
  }

  /// 依推播的 type 導到對應畫面。type 由後端決定：
  /// `invitation`（notification_service.py）、`departure_reminder`
  /// （background_reminder_scheduler.py）。
  void _routeFromData(Map<String, dynamic> data) {
    final navigator = navigatorKey?.currentState;
    if (navigator == null) return;

    switch (data['type']) {
      case 'invitation':
        navigator.push(
          MaterialPageRoute(builder: (_) => const InvitationsScreen()),
        );
        break;
      case 'departure_reminder':
        // 沒有單一行程的詳細頁，退回行程列表那一個 tab
        navigator.popUntil((route) => route.isFirst);
        MainShellState.current?.switchTo(0);
        break;
    }
  }

  Future<void> showLocalNotification({
    required String title,
    required String body,
    Map<String, dynamic>? data,
  }) async {
    if (kIsWeb) return;

    final details = NotificationDetails(
      android: AndroidNotificationDetails(
        'schedule_reminders',
        'Schedule Reminders',
        channelDescription: 'Notifications for upcoming schedules',
        importance: Importance.max,
        priority: Priority.high,
      ),
      iOS: DarwinNotificationDetails(),
      macOS: DarwinNotificationDetails(),
    );

    // Use a hash of title+body as a simple notification ID to avoid duplicates
    final id = (title + body).hashCode;

    await flutterLocalNotificationsPlugin.show(
      id,
      title,
      body,
      details,
      payload: data != null ? jsonEncode(data) : null,
    );
  }

  Future<void> scheduleNotification({
    required int id,
    required String title,
    required String body,
    required DateTime scheduledTime,
  }) async {
    if (kIsWeb) return;
    await flutterLocalNotificationsPlugin.zonedSchedule(
      id,
      title,
      body,
      tz.TZDateTime.from(scheduledTime, tz.local),
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'schedule_reminders',
          'Schedule Reminders',
          channelDescription: 'Notifications for upcoming schedules',
          importance: Importance.max,
          priority: Priority.high,
        ),
        iOS: DarwinNotificationDetails(),
      ),
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
    );
  }

  Future<void> cancelAllNotifications() async {
    if (kIsWeb) return;
    await flutterLocalNotificationsPlugin.cancelAll();
  }
}
