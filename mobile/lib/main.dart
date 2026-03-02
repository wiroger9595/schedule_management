import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'i18n/app_localizations.dart';
import 'theme/app_theme.dart';
import 'routes/app_routes.dart';
import 'providers/auth_provider.dart';
import 'providers/schedule_provider.dart';
import 'screens/ai_chat_screen.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/profile_completion_screen.dart';

import 'services/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Notifications
  await NotificationService().init();
  
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => ScheduleProvider()),
      ],
      child: ScheduleApp(),
    ),
  );
}

class ScheduleApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Schedule Management',
      theme: AppTheme.lightTheme,
      localizationsDelegates: [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: [Locale('en'), Locale('zh', 'TW')],
      initialRoute: '/startup',
      routes: {
        '/startup': (context) => _StartupWrapper(),
        ...AppRoutes.routes,
      },
      onGenerateRoute: AppRoutes.onGenerateRoute,
    );
  }
}

class _StartupWrapper extends StatefulWidget {
  @override
  _StartupWrapperState createState() => _StartupWrapperState();
}

class _StartupWrapperState extends State<_StartupWrapper> {
  @override
  void initState() {
    super.initState();
    // Defer checkAuth to next frame to allow Provider to be ready
    Future.microtask(
      () => Provider.of<AuthProvider>(context, listen: false).checkAuth(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, auth, _) {
        if (auth.isLoggedIn) {
          // Check profile completeness (simple heuristic)
          if (auth.user != null &&
              (auth.user!['phone'] == null ||
                  auth.user!['phone'].toString().isEmpty)) {
            return ProfileCompletionScreen();
          }
          return AiChatScreen();
        } else {
          // If we are still loading/checking, show loading?
          // Since checkAuth defaults isLoggedIn to false initially, we might flash login.
          // Ideally AuthProvider should have an 'isInitialized' flag.
          // For now, let's assume if not logged in, go to Login.
          return LoginScreen();
        }
      },
    );
  }
}
