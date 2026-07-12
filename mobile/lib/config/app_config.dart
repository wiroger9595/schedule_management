import 'dart:io';
import 'package:flutter/foundation.dart'; // For kIsWeb

/// Centralized app configuration constants.
class AppConfig {
  AppConfig._();

  /// Environment flag passed during compilation, e.g. --dart-define=ENV=dev
  static const String environment =
      String.fromEnvironment('ENV', defaultValue: 'local');

  /// API port number
  static const int apiPort = 7800;

  /// API base path
  static const String apiPath = '/api';

  /// Returns the appropriate API base URL based on the platform and environment.
  static String get baseUrl {
    // If environment is dev or stage, use the cloud backend
    if (environment == 'dev' ||
        environment == 'stage' ||
        environment == 'prod') {
      return 'https://schedule-backend-200440251043.asia-east1.run.app$apiPath';
    }

    // Default: local environment
    if (kIsWeb) {
      return 'http://localhost:$apiPort$apiPath';
    } else if (!kIsWeb && Platform.isAndroid) {
      // Android emulator uses 10.0.2.2 to reach host machine
      return 'http://10.0.2.2:$apiPort$apiPath';
    } else {
      // iOS physical devices can't reach the Mac via localhost.
      // Use the Mac's LAN IP instead (works for simulator too, since
      // the backend binds 0.0.0.0). Update this if your Mac's IP changes
      // (check with `ipconfig getifaddr en0`).
      return 'http://192.168.1.208:$apiPort$apiPath';
    }
  }

  /// App name used in MaterialApp title and elsewhere
  static const String appName = 'Schedule Management';
}
