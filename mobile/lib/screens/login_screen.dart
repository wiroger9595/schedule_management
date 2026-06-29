import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../widgets/google_sign_in_button.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../theme/app_theme.dart';
import '../utils/form_validators.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  String email = '';
  String password = '';
  bool _obscure = true;

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
            SnackBar(content: Text('loginFailed'.tr())),
          );
        }
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('connectionError'.tr(namedArgs: {'error': e.toString()}))),
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
    final size = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: Stack(
        children: [
          // Geometric pattern background
          const _GeometricBackground(),

          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    SizedBox(height: size.height * 0.08),

                    // Logo
                    const _AppLogo(),
                    const SizedBox(height: 48),

                    // Email field
                    TextFormField(
                      decoration: InputDecoration(
                        hintText: 'email'.tr(),
                        filled: true,
                        fillColor: AppTheme.surface,
                      ),
                      keyboardType: TextInputType.emailAddress,
                      validator: (value) {
                        if (value == null || value.isEmpty) return 'enterEmail'.tr();
                        return FormValidators.validateEmail(value);
                      },
                      onSaved: (value) => email = value!,
                    ),
                    const SizedBox(height: 16),

                    // Password field
                    TextFormField(
                      decoration: InputDecoration(
                        hintText: 'password'.tr(),
                        filled: true,
                        fillColor: AppTheme.surface,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                            color: AppTheme.textMuted,
                          ),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                      obscureText: _obscure,
                      validator: (value) => value!.isEmpty ? 'enterPassword'.tr() : null,
                      onSaved: (value) => password = value!,
                    ),
                    const SizedBox(height: 28),

                    // Login button
                    if (auth.isLoading)
                      const SizedBox(height: 54, child: Center(child: CircularProgressIndicator()))
                    else
                      SizedBox(
                        width: double.infinity,
                        height: 54,
                        child: ElevatedButton(
                          onPressed: _login,
                          child: Text('login'.tr()),
                        ),
                      ),

                    const SizedBox(height: 16),
                    TextButton(
                      onPressed: () => Navigator.pushNamed(context, '/forgot_password'),
                      child: Text('forgotPassword'.tr()),
                    ),

                    const SizedBox(height: 24),

                    // Social login
                    Row(
                      children: [
                        const Expanded(child: Divider()),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: Text('quickLogin'.tr(), style: const TextStyle(color: AppTheme.textMuted, fontSize: 13)),
                        ),
                        const Expanded(child: Divider()),
                      ],
                    ),
                    const SizedBox(height: 20),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        _SocialButton(
                          onTap: _loginGoogle,
                          child: buildGoogleSignInButton(_loginGoogle),
                        ),
                        const SizedBox(width: 16),
                        _SocialButton(
                          onTap: _loginApple,
                          child: const Icon(Icons.apple, size: 30, color: Colors.black),
                        ),
                      ],
                    ),

                    const SizedBox(height: 40),
                    // Sign up link
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text('noAccount'.tr(), style: const TextStyle(color: AppTheme.textSecond)),
                        TextButton(
                          onPressed: () => Navigator.pushNamed(context, '/register'),
                          child: Text('signUp'.tr(), style: const TextStyle(fontWeight: FontWeight.w700)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
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

class _AppLogo extends StatelessWidget {
  const _AppLogo();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 90,
          height: 90,
          decoration: BoxDecoration(
            color: AppTheme.primary,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: AppTheme.primary.withOpacity(0.3),
                blurRadius: 20,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: const Icon(Icons.send_rounded, color: Colors.white, size: 42),
        ),
        const SizedBox(height: 20),
        Text(
          'appName'.tr(),
          style: const TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w800,
            color: AppTheme.textPrimary,
            letterSpacing: -0.5,
          ),
        ),
      ],
    );
  }
}

class _SocialButton extends StatelessWidget {
  final VoidCallback onTap;
  final Widget child;
  const _SocialButton({required this.onTap, required this.child});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          color: AppTheme.surface,
          shape: BoxShape.circle,
          border: Border.all(color: AppTheme.border, width: 1.5),
        ),
        child: Center(child: child),
      ),
    );
  }
}

class _GeometricBackground extends StatelessWidget {
  const _GeometricBackground();

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    return CustomPaint(
      size: size,
      painter: _GeoPainter(),
    );
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
        // Diamond shape
        final path = Path()
          ..moveTo(x, y - spacing / 2)
          ..lineTo(x + spacing / 2, y)
          ..lineTo(x, y + spacing / 2)
          ..lineTo(x - spacing / 2, y)
          ..close();
        canvas.drawPath(path, paint);

        // Cross
        canvas.drawLine(
          Offset(x - spacing * 0.2, y),
          Offset(x + spacing * 0.2, y),
          paint,
        );
        canvas.drawLine(
          Offset(x, y - spacing * 0.2),
          Offset(x, y + spacing * 0.2),
          paint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(_GeoPainter oldDelegate) => false;
}
