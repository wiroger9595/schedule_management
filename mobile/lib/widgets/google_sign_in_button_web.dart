import 'package:flutter/material.dart';
import 'package:google_sign_in_web/web_only.dart' as gsi_web;

/// Web implementation - uses Google Identity Services renderButton.
/// Requires <meta name="google-signin-client_id"> in index.html.
Widget buildGoogleSignInButton(VoidCallback onPressed) {
  return gsi_web.renderButton(
    configuration: gsi_web.GSIButtonConfiguration(
      theme: gsi_web.GSIButtonTheme.outline,
      type: gsi_web.GSIButtonType.icon,
    ),
  );
}
