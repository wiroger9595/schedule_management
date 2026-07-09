import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';
import 'theme/app_theme.dart';
import 'routes/app_routes.dart';
import 'providers/auth_provider.dart';
import 'providers/schedule_provider.dart';
import 'providers/settings_provider.dart';
import 'screens/main_shell.dart';
import 'screens/login_screen.dart';
import 'screens/profile_completion_screen.dart';

import 'services/notification_service.dart';
import 'services/api_service.dart';

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase (required for FCM and push notifications)
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  // Initialize Notifications
  await NotificationService().init();

  await EasyLocalization.ensureInitialized();


  runApp(
    EasyLocalization(
      supportedLocales: [Locale('en'), Locale('zh', 'TW')],
      path: 'assets/i18n',
      fallbackLocale: Locale('en'),
      child: MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthProvider()),
          ChangeNotifierProvider(create: (_) => ScheduleProvider()),
          ChangeNotifierProvider(create: (_) => SettingsProvider()),
        ],
        child: ScheduleApp(),
      ),
    ),
  );
}

class ScheduleApp extends StatefulWidget {
  @override
  _ScheduleAppState createState() => _ScheduleAppState();
}

class _ScheduleAppState extends State<ScheduleApp> {
  @override
  void initState() {
    super.initState();
    ApiService.onUnauthorized.stream.listen((_) {
      if (navigatorKey.currentState != null) {
        navigatorKey.currentState!
            .pushNamedAndRemoveUntil('/login', (route) => false);
            
        final context = navigatorKey.currentContext;
        if (context != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('loginExpired'.tr())),
          );
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: navigatorKey,
      title: 'Schedule Management'.tr(),
      theme: AppTheme.lightTheme,
      localizationsDelegates: context.localizationDelegates,
      supportedLocales: context.supportedLocales,
      locale: context.locale,
      home: _StartupWrapper(),
      routes: AppRoutes.routes,
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
        // Wait for initialization (especially GoogleSignIn on Web)
        if (!auth.isInitialized) {
          return Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        if (auth.isLoggedIn) {
          // Check profile completeness (simple heuristic)
          if (auth.user != null &&
              (auth.user!['phone'] == null ||
                  auth.user!['phone'].toString().isEmpty)) {
            return ProfileCompletionScreen();
          }
          return const MainShell();
        } else {
          return LoginScreen();
        }
      },
    );
  }
}
