import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../utils/form_validators.dart';

class ForgotPasswordScreen extends StatefulWidget {
  @override
  _ForgotPasswordScreenState createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  
  int _step = 0; // 0: Input Email, 1: Input Code, 2: Input New Password & Confirm
  bool _isLoading = false;

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _sendCode() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    try {
      final api = ApiService();
      await api.forgotPassword(_emailController.text.trim());
      
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('codeSentToEmail'.tr())),
      );
      setState(() => _step = 1);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('發送失敗: $e')),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _resetPassword() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    try {
      final api = ApiService();
      await api.resetPassword(
        _emailController.text.trim(),
        _codeController.text.trim(),
        _passwordController.text,
      );
      
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('密碼重置成功，請重新登入')),
      );
      Navigator.pop(context); // Go back to login screen
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('重置失敗: $e')),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('forgotPassword'.tr())),
      body: Padding(
        padding: EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_step == 0) ...[
                Text('請輸入您的註冊信箱，我們將發送驗證碼給您。', style: TextStyle(fontSize: 16)),
                SizedBox(height: 24),
                TextFormField(
                  controller: _emailController,
                  decoration: InputDecoration(
                    labelText: 'email'.tr(),
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.email),
                  ),
                  keyboardType: TextInputType.emailAddress,
                  validator: (value) {
                    if (value == null || value.isEmpty) return 'enterEmail'.tr();
                    return FormValidators.validateEmail(value);
                  },
                ),
                SizedBox(height: 32),
                ElevatedButton(
                  onPressed: _isLoading ? null : _sendCode,
                  child: _isLoading 
                    ? CircularProgressIndicator(color: Colors.white)
                    : Text('sendCode'.tr()),
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ] else if (_step == 1) ...[
                 Text('驗證碼已發送至 ${_emailController.text}。', style: TextStyle(fontSize: 14, color: Colors.grey)),
                 SizedBox(height: 24),
                 TextFormField(
                  controller: _codeController,
                  decoration: InputDecoration(
                    labelText: 'enterCode'.tr(),
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.security),
                  ),
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value == null || value.isEmpty) return 'enterCode'.tr();
                    if (value.length != 6) return '驗證碼應為6位數';
                    return null;
                  },
                ),
                SizedBox(height: 32),
                ElevatedButton(
                  onPressed: () {
                    if (_formKey.currentState!.validate()) {
                      setState(() => _step = 2);
                    }
                  },
                  child: Text('下一步'),
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
                SizedBox(height: 16),
                TextButton(
                  onPressed: () => setState(() => _step = 0),
                  child: Text('重新發送驗證碼 / 更換信箱'),
                ),
              ] else if (_step == 2) ...[
                Text('請輸入您的新密碼。', style: TextStyle(fontSize: 16)),
                SizedBox(height: 24),
                TextFormField(
                  controller: _passwordController,
                  decoration: InputDecoration(
                    labelText: 'newPassword'.tr(),
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.lock),
                  ),
                  obscureText: true,
                  validator: (value) {
                    if (value == null || value.isEmpty) return 'enterNewPassword'.tr();
                    if (value.length < 6) return '密碼長度至少6碼';
                    return null;
                  },
                ),
                SizedBox(height: 16),
                TextFormField(
                  controller: _confirmPasswordController,
                  decoration: InputDecoration(
                    labelText: 'confirmNewPassword'.tr(),
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.lock_outline),
                  ),
                  obscureText: true,
                  validator: (value) {
                    if (value == null || value.isEmpty) return 'reEnterNewPassword'.tr();
                    if (value != _passwordController.text) return 'passwordsNotMatch'.tr();
                    return null;
                  },
                ),
                SizedBox(height: 32),
                ElevatedButton(
                  onPressed: _isLoading ? null : _resetPassword,
                  child: _isLoading 
                    ? CircularProgressIndicator(color: Colors.white)
                    : Text('resetPassword'.tr()),
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
                SizedBox(height: 16),
                TextButton(
                  onPressed: () => setState(() => _step = 1),
                  child: Text('上一步'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
