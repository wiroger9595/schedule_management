import 'package:flutter/material.dart';
import '../services/auth_service.dart';

/// Global error handler for API responses
class ErrorHandler {
  static final AuthService _authService = AuthService();

  /// Handle API errors, especially 401 Unauthorized
  static Future<void> handleError(BuildContext context, dynamic error) async {
    final errorMessage = error.toString().toLowerCase();
    
    // Check if error is unauthorized (401)
    if (errorMessage.contains('unauthorized') || errorMessage.contains('401')) {
      // Clear auth token
      await _authService.logout();
      
      // Navigate to login screen and remove all previous routes
      if (context.mounted) {
        Navigator.of(context).pushNamedAndRemoveUntil(
          '/login',
          (route) => false,
        );
      }
    }
  }

  /// Check if error is unauthorized
  static bool isUnauthorized(dynamic error) {
    final errorMessage = error.toString().toLowerCase();
    return errorMessage.contains('unauthorized') || errorMessage.contains('401');
  }
}
