import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../widgets/google_sign_in_button.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../utils/form_validators.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  
  String email = '';
  String password = '';

  void _login() async {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      final auth = Provider.of<AuthProvider>(context, listen: false);
      
      try {
        bool success = await auth.login(email, password);
        if (success) {
          Navigator.pushReplacementNamed(context, '/');
        } else {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('登入失敗，請檢查帳號密碼')),
          );
        }
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('連線錯誤: $e')),
        );
      }
    }
  }

  void _loginGoogle() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    try {
      bool success = await auth.googleLogin();
      if (success && mounted) Navigator.pushReplacementNamed(context, '/');
    } catch (e) {
      if (!mounted) return;
      String errorMessage = e.toString().replaceFirst('Exception: ', '');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Google 登入出錯: $errorMessage')));
    }
  }

  void _loginApple() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    try {
      bool success = await auth.appleLogin();
      if (success && mounted) Navigator.pushReplacementNamed(context, '/');
    } catch (e) {
      if (!mounted) return;
      String errorMessage = e.toString().replaceFirst('Exception: ', '');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Apple 登入出錯: $errorMessage')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    
    return Scaffold(
      appBar: AppBar(title: Text('login'.tr())),
      body: Padding(
        padding: EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              children: [
                TextFormField(
                  decoration: InputDecoration(labelText: 'email'.tr(), border: OutlineInputBorder()),
                  validator: (value) {
                      if (value == null || value.isEmpty) return 'enterEmail'.tr();
                      return FormValidators.validateEmail(value);
                  },
                  onSaved: (value) => email = value!,
                ),
                SizedBox(height: 16),
                TextFormField(
                  decoration: InputDecoration(labelText: 'password'.tr(), border: OutlineInputBorder()),
                  obscureText: true,
                  validator: (value) => value!.isEmpty ? 'enterPassword'.tr() : null,
                  onSaved: (value) => password = value!,
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () => Navigator.pushNamed(context, '/forgot_password'),
                    child: Text('forgotPassword'.tr()),
                  ),
                ),
                SizedBox(height: 16),
                if (auth.isLoading)
                  CircularProgressIndicator()
                else ...[
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(onPressed: _login, child: Text('login'.tr())),
                  ),
                  SizedBox(height: 16),
                  TextButton(
                    onPressed: () => Navigator.pushNamed(context, '/register'),
                    child: Text('還沒有帳號？立即註冊'),
                  ),
                  Divider(),
                  Text('quickLogin'.tr()),
                  SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      buildGoogleSignInButton(_loginGoogle),
                      SizedBox(width: 20),
                      IconButton(
                        icon: Icon(Icons.apple, size: 40, color: Colors.black),
                        onPressed: _loginApple,
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
