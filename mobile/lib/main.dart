import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/home_screen.dart';
import 'screens/add_schedule_screen.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';
import 'screens/profile_completion_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/forgot_password_screen.dart';
import 'providers/auth_provider.dart';
import 'providers/schedule_provider.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import "l10n/app_localizations.dart";

void main() {
  WidgetsFlutterBinding.ensureInitialized();
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
      theme: ThemeData(primarySwatch: Colors.blue, useMaterial3: true),
      localizationsDelegates: [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: [
        Locale('en'),
        Locale('zh', 'TW'),
      ],
      initialRoute: '/startup',
      routes: {
        '/startup': (context) => _StartupWrapper(),
        '/': (context) => HomeScreen(),
        '/login': (context) => LoginScreen(),
        '/register': (context) => RegisterScreen(),
        '/profile_completion': (context) => ProfileCompletionScreen(),
        '/add': (context) => AddScheduleScreen(),
        '/profile': (context) => ProfileScreen(),
        '/forgot_password': (context) => ForgotPasswordScreen(),
      },
      onGenerateRoute: (settings) {
        if (settings.name == 'scheduleapp://add') {
          return MaterialPageRoute(builder: (context) => AddScheduleScreen());
        }
        return null;
      },
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
    Future.microtask(() => 
      Provider.of<AuthProvider>(context, listen: false).checkAuth()
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, auth, _) {
        if (auth.isLoggedIn) {
           // Check profile completeness (simple heuristic)
           if (auth.user != null && (auth.user!['phone'] == null || auth.user!['phone'].toString().isEmpty)) {
             return ProfileCompletionScreen();
           }
           return HomeScreen();
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
