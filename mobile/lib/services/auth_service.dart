import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_service.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import 'package:flutter/foundation.dart';
import 'dart:io';

class AuthService {
  final storage = FlutterSecureStorage();

  // Injected via --dart-define during build
  static const String _webClientId = String.fromEnvironment('WEB_CLIENT_ID', defaultValue: '');
  static const String _appleServiceId = String.fromEnvironment('APPLE_SERVICE_ID', defaultValue: '');
  static const String _androidServiceId = String.fromEnvironment('ANDROID_SERVICE_ID', defaultValue: '');
  
  // iOS Client ID - only works for native iOS app
  static const String _iosClientId = '200440251043-cijriph76nsh4jrhkkdcrvlhulk5d7nf.apps.googleusercontent.com';

  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email', 'profile'],
    clientId: kIsWeb ? _webClientId : (Platform.isIOS ? _iosClientId : null),
  );

  Future<bool> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? account = await _googleSignIn.signIn();
      if (account == null) {
        throw Exception('使用者已取消 Google 登入');
      }

      final GoogleSignInAuthentication auth = await account.authentication;

      // Validate required fields
      if (account.email.isEmpty) {
        throw Exception('無法獲取 Google 帳號的信箱');
      }

      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/auth/google'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'sub': account.id,
          'email': account.email,
          'name': account.displayName ?? account.email.split('@')[0],
          'id_token': auth.idToken ?? '',
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['access_token'] != null) {
          await storage.write(key: 'jwt_token', value: data['access_token']);
          return true;
        } else {
          throw Exception('伺服器未回傳 access_token');
        }
      } else {
        throw Exception('伺服器錯誤: ${response.statusCode} - ${response.body}');
      }
    } catch (e, stackTrace) {
      print('Google sign-in error: $e');
      print('Stack trace: $stackTrace');
      rethrow;
    }
  }

  Future<bool> signInWithApple() async {
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
        webAuthenticationOptions: WebAuthenticationOptions(
          clientId: (!kIsWeb && Platform.isAndroid) ? _androidServiceId : _appleServiceId,
          redirectUri: Uri.parse('https://schedule-management-mu.vercel.app/api/auth/apple/callback'),
        ),
      );

      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/auth/apple'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'sub': credential.userIdentifier,
          'email': credential.email,
          'name': '${credential.givenName} ${credential.familyName}',
          'identityToken': credential.identityToken,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        await storage.write(key: 'jwt_token', value: data['access_token']);
        return true;
      } else {
        throw Exception('Apple Login Server Error: ${response.statusCode}');
      }
    } catch (e) {
      print('Apple Error: $e');
      rethrow;
    }
  }

  Future<bool> register(String email, String password, String fullName) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        'full_name': fullName,
      }),
    );
    return response.statusCode == 200;
  }

  Future<bool> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['access_token'] != null) {
          await storage.write(key: 'jwt_token', value: data['access_token']);
          return true;
        }
      }
    } catch (e) {
      print('Login error: $e');
    }
    return false;
  }

  Future<void> logout() async {
    String? token = await getToken();
    if (token != null) {
      try {
        await http.post(
          Uri.parse('${ApiService.baseUrl}/auth/logout'),
          headers: {'Authorization': 'Bearer $token'},
        );
      } catch (e) {
        print("Logout error: $e");
      }
    }
    await storage.delete(key: 'jwt_token');
  }

  Future<String?> getToken() async {
    return await storage.read(key: 'jwt_token');
  }

  Future<bool> isLoggedIn() async {
    String? token = await getToken();
    return token != null;
  }
}
