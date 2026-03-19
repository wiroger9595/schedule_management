// Conditional import: use web version on web, stub on other platforms
export 'google_sign_in_button_stub.dart'
    if (dart.library.html) 'google_sign_in_button_web.dart';
