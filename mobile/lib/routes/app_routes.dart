import 'package:flutter/material.dart';
import '../screens/ai_chat_screen.dart';
import '../screens/home_screen.dart';
import '../screens/add_schedule_screen.dart';
import '../screens/login_screen.dart';
import '../screens/register_screen.dart';
import '../screens/profile_completion_screen.dart';
import '../screens/profile_screen.dart';
import '../screens/forgot_password_screen.dart';

/// Centralized route definitions.
class AppRoutes {
  AppRoutes._();

  // Route name constants
  static const String startup = '/startup';
  static const String home = '/home';
  static const String login = '/login';
  static const String register = '/register';
  static const String profileCompletion = '/profile_completion';
  static const String addSchedule = '/add';
  static const String profile = '/profile';
  static const String forgotPassword = '/forgot_password';

  /// Named route map for MaterialApp
  static Map<String, WidgetBuilder> get routes {
    return {
      // Note: App startup is handled via the home property in main.dart
      home: (context) => AiChatScreen(),
      login: (context) => LoginScreen(),
      register: (context) => RegisterScreen(),
      profileCompletion: (context) => ProfileCompletionScreen(),
      addSchedule: (context) => AddScheduleScreen(),
      profile: (context) => ProfileScreen(),
      forgotPassword: (context) => ForgotPasswordScreen(),
    };
  }

  /// Handle custom URI schemes and deep links
  static Route<dynamic>? onGenerateRoute(RouteSettings settings) {
    if (settings.name == 'scheduleapp://add') {
      return MaterialPageRoute(builder: (context) => AddScheduleScreen());
    }
    return null;
  }
}
