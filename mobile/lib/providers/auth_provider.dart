import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

class AuthProvider with ChangeNotifier {
  final AuthService _authService = AuthService();
  StreamSubscription? _unauthorizedSubscription;
  bool _isLoading = false;
  bool _isLoggedIn = false;
  Map<String, dynamic>? _user;

  bool get isLoading => _isLoading;
  bool get isLoggedIn => _isLoggedIn;
  Map<String, dynamic>? get user => _user;

  AuthProvider() {
    _unauthorizedSubscription = ApiService.onUnauthorized.stream.listen((_) {
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
    _isLoggedIn = await _authService.isLoggedIn();
    if (_isLoggedIn) {
      await fetchUserProfile();
    }
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
        print('Error fetching profile: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching profile: $e');
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
      print('Error updating profile: $e');
      _isLoading = false;
      notifyListeners();
      throw e;
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();

    bool success = await _authService.login(email, password);
    if (success) {
      _isLoggedIn = true;
      await fetchUserProfile();
    }

    _isLoading = false;
    notifyListeners();
    return success;
  }

  Future<bool> register(String email, String password, String name) async {
    _isLoading = true;
    notifyListeners();

    bool success = await _authService.register(email, password, name);

    _isLoading = false;
    notifyListeners();
    return success;
  }

  Future<bool> googleLogin() async {
    _isLoading = true;
    notifyListeners();

    try {
      bool success = await _authService.signInWithGoogle();
      if (success) {
        _isLoggedIn = true;
        await fetchUserProfile();
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
