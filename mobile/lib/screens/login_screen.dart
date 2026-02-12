import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

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
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Google 登入出錯: $e')));
    }
  }

  void _loginApple() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    try {
      bool success = await auth.appleLogin();
      if (success && mounted) Navigator.pushReplacementNamed(context, '/');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Apple 登入出錯: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    
    return Scaffold(
      appBar: AppBar(title: Text('登入')),
      body: Padding(
        padding: EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              children: [
                TextFormField(
                  decoration: InputDecoration(labelText: '電子郵件', border: OutlineInputBorder()),
                  validator: (value) => value!.isEmpty ? '請輸入電子郵件' : null,
                  onSaved: (value) => email = value!,
                ),
                SizedBox(height: 16),
                TextFormField(
                  decoration: InputDecoration(labelText: '密碼', border: OutlineInputBorder()),
                  obscureText: true,
                  validator: (value) => value!.isEmpty ? '請輸入密碼' : null,
                  onSaved: (value) => password = value!,
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () => Navigator.pushNamed(context, '/forgot_password'),
                    child: Text('忘記密碼？'),
                  ),
                ),
                SizedBox(height: 16),
                if (auth.isLoading)
                  CircularProgressIndicator()
                else ...[
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(onPressed: _login, child: Text('登入')),
                  ),
                  SizedBox(height: 16),
                  TextButton(
                    onPressed: () => Navigator.pushNamed(context, '/register'),
                    child: Text('還沒有帳號？立即註冊'),
                  ),
                  Divider(),
                  Text("快速登入"),
                  SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      IconButton(
                        icon: Icon(Icons.g_mobiledata, size: 40, color: Colors.red),
                        onPressed: _loginGoogle,
                      ),
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
