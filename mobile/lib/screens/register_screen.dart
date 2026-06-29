import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import '../theme/app_theme.dart';
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
  String confirmPassword = '';
  String fullName = '';
  String? _emailError;
  bool isLoading = false;
  bool _obscurePass = true;
  bool _obscureConfirm = true;
  bool _agreedToTerms = false;

  Future<void> _register() async {
    setState(() => _emailError = null);
    if (!_agreedToTerms) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please agree to the Terms of Service')),
      );
      return;
    }
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      setState(() => isLoading = true);
      try {
        await _authService.register(email, password, fullName);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('registerSuccess'.tr())),
          );
          Navigator.pop(context);
        }
      } catch (e) {
        final msg = e.toString().replaceFirst('Exception: ', '');
        final isEmailTaken = msg.toLowerCase().contains('already registered') || msg.toLowerCase().contains('email');
        if (isEmailTaken) {
          setState(() => _emailError = 'emailAlreadyRegistered'.tr());
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
      backgroundColor: AppTheme.background,
      body: Stack(
        children: [
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Back button
                    Padding(
                      padding: const EdgeInsets.only(top: 8, bottom: 8, left: 0),
                      child: IconButton(
                        icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 20),
                        onPressed: () => Navigator.pop(context),
                        padding: EdgeInsets.zero,
                      ),
                    ),

                    // Title
                    Text(
                      'register'.tr(),
                      style: const TextStyle(
                        fontSize: 30,
                        fontWeight: FontWeight.w900,
                        color: AppTheme.textPrimary,
                        letterSpacing: -0.8,
                      ),
                    ),
                    const SizedBox(height: 32),

                    // Full Name
                    _FieldLabel('fullName'.tr()),
                    const SizedBox(height: 8),
                    TextFormField(
                      decoration: InputDecoration(
                        hintText: 'fullName'.tr(),
                        filled: true,
                        fillColor: AppTheme.surface,
                      ),
                      textCapitalization: TextCapitalization.words,
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'enterName'.tr() : null,
                      onSaved: (value) => fullName = value ?? '',
                    ),
                    const SizedBox(height: 20),

                    // Email
                    _FieldLabel('email'.tr()),
                    const SizedBox(height: 8),
                    TextFormField(
                      decoration: InputDecoration(
                        hintText: 'email'.tr(),
                        filled: true,
                        fillColor: AppTheme.surface,
                        errorText: _emailError,
                      ),
                      keyboardType: TextInputType.emailAddress,
                      validator: (value) {
                        if (value == null || value.isEmpty) return 'enterEmail'.tr();
                        return FormValidators.validateEmail(value);
                      },
                      onChanged: (_) { if (_emailError != null) setState(() => _emailError = null); },
                      onSaved: (value) => email = value!,
                    ),
                    const SizedBox(height: 20),

                    // Password
                    _FieldLabel('password'.tr()),
                    const SizedBox(height: 8),
                    TextFormField(
                      decoration: InputDecoration(
                        hintText: 'password'.tr(),
                        filled: true,
                        fillColor: AppTheme.surface,
                        suffixIcon: IconButton(
                          icon: Icon(_obscurePass ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: AppTheme.textMuted),
                          onPressed: () => setState(() => _obscurePass = !_obscurePass),
                        ),
                      ),
                      obscureText: _obscurePass,
                      validator: (v) => (v == null || v.length < 6) ? '密碼長度需至少 6 位' : null,
                      onSaved: (value) => password = value!,
                      onChanged: (v) => password = v,
                    ),
                    const SizedBox(height: 20),

                    // Confirm Password
                    _FieldLabel('confirmNewPassword'.tr()),
                    const SizedBox(height: 8),
                    TextFormField(
                      decoration: InputDecoration(
                        hintText: 'confirmNewPassword'.tr(),
                        filled: true,
                        fillColor: AppTheme.surface,
                        suffixIcon: IconButton(
                          icon: Icon(_obscureConfirm ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: AppTheme.textMuted),
                          onPressed: () => setState(() => _obscureConfirm = !_obscureConfirm),
                        ),
                      ),
                      obscureText: _obscureConfirm,
                      validator: (v) => v != password ? 'passwordsNotMatch'.tr() : null,
                      onSaved: (v) => confirmPassword = v!,
                    ),
                    const SizedBox(height: 32),

                    // Create Account button
                    if (isLoading)
                      const SizedBox(height: 54, child: Center(child: CircularProgressIndicator()))
                    else
                      SizedBox(
                        width: double.infinity,
                        height: 54,
                        child: ElevatedButton(
                          onPressed: _register,
                          child: Text('register'.tr()),
                        ),
                      ),

                    const SizedBox(height: 16),

                    // Terms checkbox
                    Row(
                      children: [
                        Checkbox(
                          value: _agreedToTerms,
                          activeColor: AppTheme.primary,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                          onChanged: (v) => setState(() => _agreedToTerms = v ?? false),
                        ),
                        const Expanded(
                          child: Text(
                            'I agree to the Terms of Service',
                            style: TextStyle(fontSize: 13, color: AppTheme.textSecond),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 16),

                    // Login link
                    Center(
                      child: TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: Text(
                          'Already have an account? Login',
                          style: const TextStyle(color: AppTheme.textSecond, fontSize: 14),
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  final String text;
  const _FieldLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppTheme.textPrimary,
      ),
    );
  }
}
