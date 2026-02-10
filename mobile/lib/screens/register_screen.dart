import 'package:flutter/material.dart';
import '../services/auth_service.dart';

class RegisterScreen extends StatefulWidget {
  @override
  _RegisterScreenState createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final AuthService _authService = AuthService();
  
  String email = '';
  String password = '';
  String fullName = '';
  bool isLoading = false;

  void _register() async {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      setState(() => isLoading = true);
      try {
        bool success = await _authService.register(email, password, fullName);
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('註冊成功，請登入')),
          );
          Navigator.pop(context);
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('註冊失敗，該信箱可能已被使用')),
          );
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('連線錯誤: $e')),
        );
      } finally {
        setState(() => isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('註冊')),
      body: Padding(
        padding: EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              TextFormField(
                decoration: InputDecoration(labelText: '全名', border: OutlineInputBorder()),
                onSaved: (value) => fullName = value ?? '',
              ),
              SizedBox(height: 16),
              TextFormField(
                decoration: InputDecoration(labelText: '電子郵件', border: OutlineInputBorder()),
                validator: (value) => value!.isEmpty ? '請輸入電子郵件' : null,
                onSaved: (value) => email = value!,
              ),
              SizedBox(height: 16),
              TextFormField(
                decoration: InputDecoration(labelText: '密碼', border: OutlineInputBorder()),
                obscureText: true,
                validator: (value) => value!.length < 6 ? '密碼長度需至少 6 位' : null,
                onSaved: (value) => password = value!,
              ),
              SizedBox(height: 24),
              if (isLoading)
                CircularProgressIndicator()
              else
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(onPressed: _register, child: Text('註冊')),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
