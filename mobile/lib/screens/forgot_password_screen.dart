import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
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

  int _step = 0;
  bool _isLoading = false;
  bool _obscurePass = true;
  bool _obscureConfirm = true;

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
      await ApiService().forgotPassword(_emailController.text.trim());
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('codeSentSuccess'.tr())));
      setState(() => _step = 1);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('sendFailed'.tr(namedArgs: {'error': e.toString()}))));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _resetPassword() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);
    try {
      await ApiService().resetPassword(
        _emailController.text.trim(),
        _codeController.text.trim(),
        _passwordController.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('passwordResetSuccess'.tr())));
      Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('resetFailed'.tr(namedArgs: {'error': e.toString()}))));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: Stack(
        children: [
          const _GeometricBg(),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 8),
                    IconButton(
                      icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 20),
                      onPressed: () {
                        if (_step > 0) setState(() => _step--);
                        else Navigator.pop(context);
                      },
                      padding: EdgeInsets.zero,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'forgotPassword'.tr(),
                      style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: AppTheme.textPrimary),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _step == 0
                          ? 'Enter your email to receive a reset link.'
                          : _step == 1
                              ? 'codeSentTo'.tr(namedArgs: {'email': _emailController.text})
                              : 'enterNewPasswordDesc'.tr(),
                      style: const TextStyle(fontSize: 15, color: AppTheme.textSecond, height: 1.5),
                    ),
                    const SizedBox(height: 40),

                    // Step 0 — email
                    if (_step == 0) ...[
                      TextFormField(
                        controller: _emailController,
                        decoration: InputDecoration(
                          hintText: 'Email Address',
                          filled: true,
                          fillColor: AppTheme.surface,
                        ),
                        keyboardType: TextInputType.emailAddress,
                        validator: (v) {
                          if (v == null || v.isEmpty) return 'enterEmail'.tr();
                          return FormValidators.validateEmail(v);
                        },
                      ),
                      const SizedBox(height: 32),
                      SizedBox(
                        width: double.infinity,
                        height: 54,
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _sendCode,
                          child: _isLoading
                              ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : Text('sendCode'.tr()),
                        ),
                      ),
                    ],

                    // Step 1 — code
                    if (_step == 1) ...[
                      TextFormField(
                        controller: _codeController,
                        decoration: InputDecoration(
                          hintText: 'enterCode'.tr(),
                          filled: true,
                          fillColor: AppTheme.surface,
                        ),
                        keyboardType: TextInputType.number,
                        validator: (v) {
                          if (v == null || v.isEmpty) return 'enterCode'.tr();
                          if (v.length != 6) return '驗證碼應為6位數';
                          return null;
                        },
                      ),
                      const SizedBox(height: 32),
                      SizedBox(
                        width: double.infinity,
                        height: 54,
                        child: ElevatedButton(
                          onPressed: () { if (_formKey.currentState!.validate()) setState(() => _step = 2); },
                          child: Text('next'.tr()),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Center(child: TextButton(onPressed: () => setState(() => _step = 0), child: Text('resendOrChange'.tr()))),
                    ],

                    // Step 2 — new password
                    if (_step == 2) ...[
                      TextFormField(
                        controller: _passwordController,
                        decoration: InputDecoration(
                          hintText: 'newPassword'.tr(),
                          filled: true,
                          fillColor: AppTheme.surface,
                          suffixIcon: IconButton(
                            icon: Icon(_obscurePass ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: AppTheme.textMuted),
                            onPressed: () => setState(() => _obscurePass = !_obscurePass),
                          ),
                        ),
                        obscureText: _obscurePass,
                        validator: (v) {
                          if (v == null || v.isEmpty) return 'enterNewPassword'.tr();
                          if (v.length < 6) return '密碼長度至少6碼';
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _confirmPasswordController,
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
                        validator: (v) {
                          if (v == null || v.isEmpty) return 'reEnterNewPassword'.tr();
                          if (v != _passwordController.text) return 'passwordsNotMatch'.tr();
                          return null;
                        },
                      ),
                      const SizedBox(height: 32),
                      SizedBox(
                        width: double.infinity,
                        height: 54,
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _resetPassword,
                          child: _isLoading
                              ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : Text('resetPassword'.tr()),
                        ),
                      ),
                    ],
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

class _GeometricBg extends StatelessWidget {
  const _GeometricBg();
  @override
  Widget build(BuildContext context) {
    return CustomPaint(size: MediaQuery.of(context).size, painter: _GeoPainter());
  }
}

class _GeoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppTheme.primary.withOpacity(0.04)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    const spacing = 90.0;
    for (double y = -spacing; y < size.height + spacing * 2; y += spacing) {
      for (double x = -spacing; x < size.width + spacing * 2; x += spacing) {
        final path = Path()
          ..moveTo(x, y - spacing / 2)
          ..lineTo(x + spacing / 2, y)
          ..lineTo(x, y + spacing / 2)
          ..lineTo(x - spacing / 2, y)
          ..close();
        canvas.drawPath(path, paint);
        canvas.drawLine(Offset(x - spacing * 0.2, y), Offset(x + spacing * 0.2, y), paint);
        canvas.drawLine(Offset(x, y - spacing * 0.2), Offset(x, y + spacing * 0.2), paint);
      }
    }
  }
  @override
  bool shouldRepaint(_GeoPainter oldDelegate) => false;
}
