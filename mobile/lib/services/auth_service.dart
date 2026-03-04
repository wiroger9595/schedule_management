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

  // Configure GoogleSignIn with explicit parameters
  // IMPORTANT: Use different client IDs for different platforms
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email', 'profile'],
    // iOS Client ID - only works for native iOS app
    // For web/Android, you need to create a separate OAuth client in Google Cloud Console
    clientId: !kIsWeb && Platform.isIOS
        ? '200440251043-cijriph76nsh4jrhkkdcrvlhulk5d7nf.apps.googleusercontent.com'
        : null, // For Android, client ID comes from google-services.json
    // If testing on web, create a Web Application client ID and uncomment below:
    // serverClientId: 'YOUR_WEB_CLIENT_ID.apps.googleusercontent.com',
  );

  Future<bool> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? account = await _googleSignIn.signIn();
      if (account == null) {
        print('Google sign-in cancelled by user');
        return false;
      }

      final GoogleSignInAuthentication auth = await account.authentication;

      // Validate required fields
      if (account.email.isEmpty) {
        print('Google account email is required');
        return false;
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
          print('Server did not return access_token');
          return false;
        }
      } else {
        print('Server error: ${response.statusCode} - ${response.body}');
        return false;
      }
    } catch (e, stackTrace) {
      print('Google sign-in error: $e');
      print('Stack trace: $stackTrace');
    }
    return false;
  }

  Future<bool> signInWithApple() async {
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
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
      }
    } catch (e) {
      print('Apple Error: $e');
    }
    return false;
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
