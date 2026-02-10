import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/add_schedule_screen.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';
import 'screens/profile_completion_screen.dart';
import 'screens/profile_screen.dart';
import 'services/auth_service.dart';
import 'services/api_service.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(ScheduleApp());
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
        '/startup': (context) => _StartupScreen(),
        '/': (context) => HomeScreen(),
        '/login': (context) => LoginScreen(),
        '/register': (context) => RegisterScreen(),
        '/profile_completion': (context) => ProfileCompletionScreen(),
        '/add': (context) => AddScheduleScreen(),
        '/profile': (context) => ProfileScreen(),
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

class _StartupScreen extends StatefulWidget {
  @override
  __StartupScreenState createState() => __StartupScreenState();
}

class __StartupScreenState extends State<_StartupScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuthAndProfile();
  }

  Future<void> _checkAuthAndProfile() async {
    final authService = AuthService();
    bool isLoggedIn = await authService.isLoggedIn();
    
    if (!isLoggedIn) {
      Navigator.pushReplacementNamed(context, '/login');
      return;
    }
    
    // Check profile completion
    try {
      final apiService = ApiService();
      final headers = await apiService.getHeaders();
      final response = await http.get(
        Uri.parse('${ApiService.baseUrl}/users/me'),
        headers: headers,
      );
      
      if (response.statusCode == 200) {
        final user = jsonDecode(response.body);
        if (user['phone'] == null || user['phone'].toString().isEmpty) {
          Navigator.pushReplacementNamed(context, '/profile_completion');
          return;
        }
      }
    } catch (e) {
      print('Error checking profile: $e');
    }
    
    Navigator.pushReplacementNamed(context, '/');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: CircularProgressIndicator(),
      ),
    );
  }
}
