import 'dart:io';
import 'package:flutter/foundation.dart'; // For kIsWeb

/// Centralized app configuration constants.
class AppConfig {
  AppConfig._();

  /// Environment flag passed during compilation, e.g. --dart-define=ENV=dev
  static const String environment = String.fromEnvironment('ENV', defaultValue: 'local');

  /// API port number
  static const int apiPort = 3000;

  /// API base path
  static const String apiPath = '/api';

  /// Returns the appropriate API base URL based on the platform and environment.
  static String get baseUrl {
    // If environment is dev or stage, use the cloud backend
    if (environment == 'dev' || environment == 'stage' || environment == 'prod') {
      return 'https://schedule-backend-200440251043.asia-east1.run.app$apiPath';
    }

    // Default: local environment
    if (kIsWeb) {
      return 'http://localhost:$apiPort$apiPath';
    } else if (Platform.isAndroid) {
      // Android emulator uses 10.0.2.2 to reach host machine
      return 'http://10.0.2.2:$apiPort$apiPath';
    } else {
      // iOS simulator and others use localhost
      return 'http://localhost:$apiPort$apiPath';
    }
  }

  /// App name used in MaterialApp title and elsewhere
  static const String appName = 'Schedule Management';
}
