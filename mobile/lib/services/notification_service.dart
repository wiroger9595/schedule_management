import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest.dart' as tz;
import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'dart:convert';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();

  Future<void> init() async {
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

    await flutterLocalNotificationsPlugin.initialize(initializationSettings);

    // Request permissions for Android 13+
    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

    // Set up Firebase Messaging handlers
    _setupFirebaseMessaging();
  }

  void _setupFirebaseMessaging() {
    final messaging = FirebaseMessaging.instance;

    // Handle foreground messages (app is in focus)
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      _handleForegroundMessage(message);
    });

    // Handle messages opened from terminated state
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      _handleMessageOpenedApp(message);
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
    // Handle tap on notification when app is in background or terminated
    // TODO: Navigate to relevant screen based on message.data['type']
    if (message.data['type'] == 'departure_reminder' &&
        message.data['schedule_id'] != null) {
      // Navigate to schedule detail screen
      // Example: navigatorKey.currentState?.pushNamed('/schedule-detail', arguments: message.data['schedule_id']);
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
