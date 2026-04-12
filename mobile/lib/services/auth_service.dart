import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_service.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import 'package:flutter/foundation.dart';
import 'dart:io';

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  final storage = const FlutterSecureStorage(
    webOptions: WebOptions(
      dbName: 'auth_db',
      publicKey: 'auth_key',
    ),
  );

  // Injected via --dart-define during build or flutter run --dart-define-from-file=.env-local
  static const String _webClientId = String.fromEnvironment('WEB_CLIENT_ID', 
      defaultValue: '200440251043-ia6vtcvdp3ls1cp4ba681q3phs3onuds.apps.googleusercontent.com');
  static const String _androidServiceId = String.fromEnvironment('ANDROID_SERVICE_ID', 
      defaultValue: '');
  static const String _iosClientId = String.fromEnvironment('IOS_CLIENT_ID', 
      defaultValue: '200440251043-cijriph76nsh4jrhkkdcrvlhulk5d7nf.apps.googleusercontent.com');

  late final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email', 'profile'],
    clientId: kIsWeb 
        ? (_webClientId.isNotEmpty ? _webClientId : null)
        : (Platform.isIOS ? (_iosClientId.isNotEmpty ? _iosClientId : null) : (Platform.isAndroid ? (_androidServiceId.isNotEmpty ? _androidServiceId : null) : null)),
    // serverClientId is NOT supported on Web (the plugin asserts it must be null)
    // Only set it for native platforms
    serverClientId: kIsWeb ? null : (_webClientId.isNotEmpty ? _webClientId : null),
  );

  GoogleSignIn get googleSignIn => _googleSignIn;

  Future<void> initWeb() async {
    if (kIsWeb) {
      // For web, if the meta tag is removed, we MUST explicitly initialize it
      // before rendering the button or calling other methods.
      try {
        await _googleSignIn.signInSilently();
      } catch (e) {
        debugPrint('GoogleSignIn initWeb (expected if not signed in): $e');
      }
    }
  }

  Future<bool> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? account = await _googleSignIn.signIn().timeout(
        const Duration(seconds: 45),
        onTimeout: () {
          throw Exception('Google 登入超時。請確認您的瀏覽器是否阻擋了彈出視窗 (Popup Blocker)，或請重新嘗試。');
        },
      );
      if (account == null) {
        throw Exception('使用者已取消 Google 登入');
      }

      return await processGoogleAccount(account);
    } catch (e, stackTrace) {
      debugPrint('Google sign-in error: $e');
      debugPrint('Stack trace: $stackTrace');
      rethrow;
    }
  }

  Future<bool> processGoogleAccount(GoogleSignInAccount account) async {
    try {
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
    } catch (e) {
      debugPrint('Error processing Google account: $e');
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
          clientId: (!kIsWeb && Platform.isAndroid) ? _androidServiceId : _iosClientId,
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
      debugPrint('Apple Error: $e');
      rethrow;
    }
  }

  Future<void> register(String email, String password, String fullName) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        'full_name': fullName,
      }),
    );
    if (response.statusCode != 200) {
      String detail = '註冊失敗（${response.statusCode}）';
      try {
        final body = jsonDecode(response.body);
        if (body['detail'] != null) detail = body['detail'].toString();
      } catch (_) {}
      throw Exception(detail);
    }
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
      debugPrint('Login error: $e');
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
        debugPrint("Logout error: $e");
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
