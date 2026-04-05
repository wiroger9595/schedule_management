import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import '../utils/form_validators.dart';

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
  String? _emailError;
  bool isLoading = false;

  Future<void> _register() async {
    setState(() => _emailError = null); // Reset error
    
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      setState(() => isLoading = true);
      try {
        await _authService.register(email, password, fullName);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('註冊成功，請登入')),
          );
          Navigator.pop(context);
        }
      } catch (e) {
        final msg = e.toString().replaceFirst('Exception: ', '');
        final isEmailTaken = msg.toLowerCase().contains('already registered') ||
            msg.toLowerCase().contains('email');
        if (isEmailTaken) {
          setState(() => _emailError = '此信箱已被註冊，請直接登入');
        } else {
          setState(() => _emailError = msg);
        }
      } finally {
        setState(() => isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('register'.tr())),
      body: Padding(
        padding: EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              TextFormField(
                decoration: InputDecoration(labelText: 'fullName'.tr(), border: OutlineInputBorder()),
                onSaved: (value) => fullName = value ?? '',
              ),
              SizedBox(height: 16),
              SizedBox(height: 16),
              TextFormField(
                decoration: InputDecoration(
                    labelText: 'email'.tr(),
                    border: OutlineInputBorder(),
                    errorText: _emailError, // Field-level error
                ),
                validator: (value) {
                    if (value == null || value.isEmpty) return 'enterEmail'.tr();
                    return FormValidators.validateEmail(value);
                },
                onChanged: (_) {
                    if (_emailError != null) {
                        setState(() => _emailError = null); // Clear error on edit
                    }
                },
                onSaved: (value) => email = value!,
              ),
              SizedBox(height: 16),
              TextFormField(
                decoration: InputDecoration(labelText: 'password'.tr(), border: OutlineInputBorder()),
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
                  child: ElevatedButton(onPressed: _register, child: Text('register'.tr())),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
