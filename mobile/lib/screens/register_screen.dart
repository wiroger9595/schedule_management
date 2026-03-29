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
        bool success = await _authService.register(email, password, fullName);
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('註冊成功，請登入')),
          );
          Navigator.pop(context);
        } else {
             // Basic registration failed
             setState(() {
                 _emailError = '註冊失敗，該信箱可能已被使用';
             });
        }
      } catch (e) {
          // Check if error message contains "already registered" keywords if possible,
          // but usually the service just returns false or throws.
          // For now, if it throws, we might still want to show snackbar for network errors,
          // but if it's a 400 from API for duplicate email, AuthService might throw.
          // Let's assume generic error for now, but prioritize email error if likely.
          if (e.toString().contains("400") || e.toString().contains("registered")) {
               setState(() {
                 _emailError = 'emailAlreadyRegistered'.tr();
               });
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('註冊錯誤: $e')),
            );
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
