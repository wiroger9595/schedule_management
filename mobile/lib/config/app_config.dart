import 'dart:io';

/// Centralized app configuration constants.
class AppConfig {
  AppConfig._();

  /// API port number
  static const int apiPort = 3000;

  /// API base path
  static const String apiPath = '/api';

  /// Returns the appropriate API base URL based on the platform.
  /// - Android emulator uses 10.0.2.2 to reach host machine
  /// - iOS simulator uses localhost
  /// - For real devices, change to your Mac's local IP
  static String get baseUrl {
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:$apiPort$apiPath';
    } else {
      return 'http://localhost:$apiPort$apiPath';
    }
  }

  /// App name used in MaterialApp title and elsewhere
  static const String appName = 'Schedule Management';
}
