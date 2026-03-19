import 'package:flutter/material.dart';

/// Stub implementation for non-web platforms.
/// On iOS/Android, we use the standard IconButton with signIn().
Widget buildGoogleSignInButton(VoidCallback onPressed) {
  return IconButton(
    icon: Icon(Icons.g_mobiledata, size: 40, color: Colors.red),
    onPressed: onPressed,
  );
}
