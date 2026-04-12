import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

class AuthProvider with ChangeNotifier {
  final AuthService _authService = AuthService();
  StreamSubscription? _unauthorizedSubscription;
  bool _isLoading = false;
  bool _isLoggedIn = false;
  bool _isInitialized = false;
  Map<String, dynamic>? _user;
  DateTime? _lastLoginTime;

  bool get isLoading => _isLoading;
  bool get isLoggedIn => _isLoggedIn;
  bool get isInitialized => _isInitialized;
  Map<String, dynamic>? get user => _user;

  AuthProvider() {
    _unauthorizedSubscription = ApiService.onUnauthorized.stream.listen((_) {
      // Guard: If we just logged in within the last 5 seconds, ignore 401
      // as it might be a race condition with a pending request or storage write.
      if (_lastLoginTime != null && 
          DateTime.now().difference(_lastLoginTime!).inSeconds < 5) {
        debugPrint('Ignoring 401 due to recent login (race condition guard)');
        return;
      }
      // Trigger logout when a 401 is encountered globally
      logout();
    });
  }

  @override
  void dispose() {
    _unauthorizedSubscription?.cancel();
    super.dispose();
  }

  Future<void> checkAuth() async {
    // Set up Google sign-in listener for Web renderButton events
    if (kIsWeb) {
      _authService.googleSignIn.onCurrentUserChanged.listen((GoogleSignInAccount? account) async {
        if (account != null) {
          _isLoading = true;
          notifyListeners();
          try {
            bool success = await _authService.processGoogleAccount(account);
            if (success) {
              _lastLoginTime = DateTime.now();
              _isLoggedIn = true;
              await fetchUserProfile();
            }
          } catch (e) {
            debugPrint('Error processing Google login from listener: $e');
          } finally {
            _isLoading = false;
            notifyListeners();
          }
        }
      });
    }

    _isLoggedIn = await _authService.isLoggedIn();
    if (_isLoggedIn) {
      await fetchUserProfile();
    }
    _isInitialized = true;
    notifyListeners();
  }

  Future<void> fetchUserProfile() async {
    try {
      final apiService = ApiService();
      final headers = await apiService.getHeaders();
      final response = await http.get(
        Uri.parse('${ApiService.baseUrl}/users/me'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        _user = jsonDecode(utf8.decode(response
            .bodyBytes)); // Properly parse UTF-8 characters like Chinese
        notifyListeners();
      } else if (response.statusCode == 401) {
        // Token is invalid or expired
        await logout();
      } else {
        debugPrint('Error fetching profile: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error fetching profile: $e');
    }
  }

  Future<bool> updateProfile(Map<String, dynamic> data) async {
    _isLoading = true;
    notifyListeners();

    try {
      final apiService = ApiService();
      final headers = await apiService.getHeaders();
      headers['Content-Type'] = 'application/json';

      final response = await http.patch(
        Uri.parse('${ApiService.baseUrl}/users/me'),
        headers: headers,
        body: jsonEncode(data),
      );

      if (response.statusCode == 200) {
        await fetchUserProfile(); // Refresh local user data
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        throw Exception('Failed to update profile: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error updating profile: $e');
      _isLoading = false;
      notifyListeners();
      throw e;
    }
  }

  Future<void> _registerFcmToken() async {
    try {
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission();
      final token = await messaging.getToken();
      if (token != null) {
        await ApiService().updateFcmToken(token);
      }
    } catch (e) {
      debugPrint('FCM token registration failed: $e');
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();

    bool success = await _authService.login(email, password);
    if (success) {
      _lastLoginTime = DateTime.now();
      _isLoggedIn = true;
      await fetchUserProfile();
      _registerFcmToken();
    }

    _isLoading = false;
    notifyListeners();
    return success;
  }

  Future<bool> register(String email, String password, String name) async {
    _isLoading = true;
    notifyListeners();

    try {
      await _authService.register(email, password, name);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (_) {
      _isLoading = false;
      notifyListeners();
      rethrow;
    }
  }

  Future<bool> googleLogin() async {
    _isLoading = true;
    notifyListeners();

    try {
      bool success = await _authService.signInWithGoogle();
      if (success) {
        _lastLoginTime = DateTime.now();
        _isLoggedIn = true;
        await fetchUserProfile();
        _registerFcmToken();
      }
      return success;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> appleLogin() async {
    _isLoading = true;
    notifyListeners();

    try {
      bool success = await _authService.signInWithApple();
      if (success) {
        _lastLoginTime = DateTime.now();
        _isLoggedIn = true;
        await fetchUserProfile();
      }
      return success;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    _isLoggedIn = false;
    _user = null;
    notifyListeners();
  }
}
