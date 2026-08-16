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
      // Use the Mac's mDNS/Bonjour hostname instead of a LAN IP — it
      // resolves on any network the Mac and device share, so it keeps
      // working after Wi-Fi changes/moves. Check with `scutil --get LocalHostName`.
      return 'http://userdeMacBook-Pro.local:$apiPort$apiPath';
    }
  }

  /// App name used in MaterialApp title and elsewhere
  static const String appName = 'Schedule Management';

  // ── RevenueCat（訂閱）─────────────────────────────────────────────────────
  // 用 --dart-define 傳入，不要寫死在 repo 裡：
  //   flutter run --dart-define=REVENUECAT_ANDROID_KEY=goog_xxx --dart-define=REVENUECAT_IOS_KEY=appl_xxx
  static const String _revenueCatIosKey =
      String.fromEnvironment('REVENUECAT_IOS_KEY');
  static const String _revenueCatAndroidKey =
      String.fromEnvironment('REVENUECAT_ANDROID_KEY');

  /// 空字串代表未設定 → 訂閱功能靜默停用（本機開發時不會擋住其他功能）
  static String get revenueCatApiKey {
    if (kIsWeb) return '';
    return Platform.isIOS ? _revenueCatIosKey : _revenueCatAndroidKey;
  }

  /// RevenueCat 後台的 entitlement identifier，要和後端 REVENUECAT_ENTITLEMENT_ID 一致
  static const String proEntitlementId =
      String.fromEnvironment('REVENUECAT_ENTITLEMENT', defaultValue: 'pro');
}
