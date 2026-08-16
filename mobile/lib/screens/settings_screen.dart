import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/settings_provider.dart';
import '../providers/subscription_provider.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';
import '../widgets/user_avatar.dart';
import 'ai_key_screen.dart';
import 'paywall_screen.dart';
import 'profile_screen.dart';
import 'invitations_screen.dart';
import 'main_shell.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  String _defaultSending = 'line';

  static const _languages = [
    {'label': '繁體中文', 'locale': Locale('zh', 'TW')},
    {'label': 'English', 'locale': Locale('en')},
  ];

  static List<Map<String, String>> _statusItems(BuildContext context) => [
    {'status': ScheduleStatus.pending,     'label': 'statusPending'.tr()},
    {'status': ScheduleStatus.comingSoon,  'label': 'statusComingSoon'.tr()},
    {'status': ScheduleStatus.active,      'label': 'statusActive'.tr()},
    {'status': ScheduleStatus.attend,      'label': 'statusAttend'.tr()},
    {'status': ScheduleStatus.notGoing,    'label': 'statusNotGoing'.tr()},
    {'status': ScheduleStatus.notAttended, 'label': 'statusNotAttend'.tr()},
    {'status': ScheduleStatus.cancel,      'label': 'statusCancelled'.tr()},
  ];

  List<Map<String, String>> get _notificationItems => [
    {'value': 'line',  'label': 'notificationLine'.tr()},
    {'value': 'sms',   'label': 'notificationSMSShort'.tr()},
    {'value': 'email', 'label': 'notificationEmail'.tr()},
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final sending = context.read<AuthProvider>().user?['default_sending'];
      if (sending != null && sending is String) setState(() => _defaultSending = sending);
      context.read<SubscriptionProvider>().refresh();
    });
  }

  Future<void> _setNotificationMethod(String value) async {
    setState(() => _defaultSending = value);
    try {
      await context.read<AuthProvider>().updateProfile({'default_sending': value});
    } catch (_) {
      if (mounted) {
        final auth = context.read<AuthProvider>();
        setState(() => _defaultSending = auth.user?['default_sending'] ?? 'line');
      }
    }
  }

  /// pro 用自己的 key → 不限次數；free → 顯示本月還剩幾次
  String _planValue(SubscriptionProvider subscription) {
    if (subscription.usingOwnKey) return 'subscriptionProUnlimited'.tr();
    if (subscription.isPro) return 'subscriptionProNoKey'.tr();
    final remaining = subscription.remaining;
    if (remaining == null) return 'subscriptionFree'.tr();
    return 'subscriptionFreeRemaining'.tr(namedArgs: {'count': '$remaining'});
  }

  void _logout() async {
    final auth = context.read<AuthProvider>();
    // 先清方案狀態，否則下一個登入的人會先看到上一個人的額度
    context.read<SubscriptionProvider>().reset();
    await auth.logout();
    if (!mounted) return;
    Navigator.of(context).pushNamedAndRemoveUntil('/login', (_) => false);
  }

  @override
  Widget build(BuildContext context) {
    final currentLocale = context.locale;
    final settings = context.watch<SettingsProvider>();
    final subscription = context.watch<SubscriptionProvider>();

    final selectedLangLabel = _languages.firstWhere(
      (l) => (l['locale'] as Locale) == currentLocale,
      orElse: () => _languages.first,
    )['label'] as String;

    final visibleCount = _statusItems(context).where((i) => settings.isVisible(i['status']!)).length;
    final totalCount   = _statusItems(context).length;

    final currentNotifLabel = _notificationItems
        .firstWhere((n) => n['value'] == _defaultSending, orElse: () => _notificationItems.first)['label']!;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.surface,
        elevation: 0,
        automaticallyImplyLeading: false,
        leading: IconButton(
          icon: const Icon(Icons.menu_rounded),
          color: AppTheme.textSecond,
          onPressed: () => MainShellState.scaffoldKey.currentState?.openDrawer(),
        ),
        title: Text(
          'settings'.tr(),
          style: const TextStyle(
            color: AppTheme.textPrimary,
            fontWeight: FontWeight.w700,
            fontSize: 18,
          ),
        ),
      ),
      body: CustomScrollView(
        slivers: [
          // ── Profile header ────────────────────────────────
          SliverToBoxAdapter(child: _ProfileHeader()),

          // ── Account section ───────────────────────────────
          SliverToBoxAdapter(child: _SectionLabel('ACCOUNT')),
          SliverToBoxAdapter(
            child: _SettingsCard(children: [
              _SettingsTile(
                icon: Icons.language_outlined,
                label: 'language'.tr(),
                value: selectedLangLabel,
                onTap: () => _showLanguagePicker(context, currentLocale),
              ),
              const Divider(height: 1, indent: 56),
              _SettingsTile(
                icon: Icons.mail_outline_rounded,
                label: 'invitations'.tr(),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const InvitationsScreen())),
              ),
            ]),
          ),

          // ── Subscription section ──────────────────────────
          SliverToBoxAdapter(child: _SectionLabel('SUBSCRIPTION')),
          SliverToBoxAdapter(
            child: _SettingsCard(children: [
              _SettingsTile(
                icon: Icons.auto_awesome_rounded,
                label: 'subscriptionPlan'.tr(),
                value: _planValue(subscription),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PaywallScreen())),
              ),
              if (subscription.isPro) ...[
                const Divider(height: 1, indent: 56),
                _SettingsTile(
                  icon: Icons.key_rounded,
                  label: 'aiKeySettings'.tr(),
                  value: subscription.hasAiKey
                      ? subscription.aiKey['model'] as String?
                      : 'aiKeyNotSet'.tr(),
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AiKeyScreen())),
                ),
              ],
            ]),
          ),

          // ── Notifications section ─────────────────────────
          SliverToBoxAdapter(child: _SectionLabel('NOTIFICATIONS')),
          SliverToBoxAdapter(
            child: _SettingsCard(children: [
              _SettingsTile(
                icon: Icons.notifications_outlined,
                label: 'defaultNotificationMethod'.tr(),
                value: currentNotifLabel,
                onTap: () => _showNotifPicker(context),
              ),
            ]),
          ),

          // ── Privacy section ───────────────────────────────
          SliverToBoxAdapter(child: _SectionLabel('PRIVACY')),
          SliverToBoxAdapter(
            child: _SettingsCard(children: [
              _SettingsTile(
                icon: Icons.list_alt_outlined,
                label: 'mySchedules'.tr(),
                value: '$visibleCount / $totalCount',
                onTap: () => _showStatusFilter(context, settings),
              ),
            ]),
          ),

          // ── Logout ────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 24, 16, 8),
              child: SizedBox(
                width: double.infinity,
                height: 54,
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.logout_rounded),
                  label: Text('logout'.tr()),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.statusC,
                    side: const BorderSide(color: AppTheme.statusC),
                  ),
                  onPressed: _logout,
                ),
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 40)),
        ],
      ),
    );
  }

  void _showLanguagePicker(BuildContext context, Locale currentLocale) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text('language'.tr(), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
            ),
            ..._languages.map((lang) {
              final locale    = lang['locale'] as Locale;
              final isSelected = currentLocale == locale;
              return ListTile(
                title: Text(lang['label'] as String, style: TextStyle(fontWeight: isSelected ? FontWeight.w700 : FontWeight.normal)),
                trailing: isSelected ? const Icon(Icons.check_rounded, color: AppTheme.primary) : null,
                onTap: () {
                  if (!isSelected) context.setLocale(locale);
                  Navigator.pop(context);
                },
              );
            }),
          ],
        ),
      ),
    );
  }

  void _showNotifPicker(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text('defaultNotificationMethod'.tr(), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
            ),
            ..._notificationItems.map((item) {
              final isSelected = _defaultSending == item['value'];
              return ListTile(
                title: Text(item['label']!, style: TextStyle(fontWeight: isSelected ? FontWeight.w700 : FontWeight.normal)),
                trailing: isSelected ? const Icon(Icons.check_rounded, color: AppTheme.primary) : null,
                onTap: () {
                  _setNotificationMethod(item['value']!);
                  Navigator.pop(context);
                },
              );
            }),
          ],
        ),
      ),
    );
  }

  void _showStatusFilter(BuildContext context, SettingsProvider settings) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text('mySchedules'.tr(), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
            ),
            ..._statusItems(context).map((item) {
              final status    = item['status']!;
              final isChecked = settings.isVisible(status);
              return CheckboxListTile(
                value: isChecked,
                activeColor: AppTheme.primary,
                title: Text(item['label']!),
                onChanged: (val) => settings.setStatusVisible(status, val ?? false),
              );
            }),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

// ── Sub-widgets ────────────────────────────────────────────────────────────────

class _ProfileHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (_, auth, __) {
        final user  = auth.user ?? {};
        final name  = (user['full_name'] as String?)?.isNotEmpty == true ? user['full_name'] as String : 'user'.tr();
        final email = (user['email'] as String?) ?? '';
        final image = user['profile_image_path'] as String?;

        return Container(
          color: AppTheme.surface,
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
          child: Column(
            children: [
              // Avatar
              Stack(
                alignment: Alignment.center,
                children: [
                  Container(
                    width: 90,
                    height: 90,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: AppTheme.primary, width: 3),
                    ),
                    child: GestureDetector(
                      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ProfileScreen())),
                      child: UserAvatar(radius: 43, imageUrl: image),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                name,
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppTheme.textPrimary),
              ),
              const SizedBox(height: 4),
              Text(email, style: const TextStyle(fontSize: 14, color: AppTheme.textSecond)),
              const SizedBox(height: 16),
              OutlinedButton(
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ProfileScreen())),
                child: Text('edit'.tr()),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String label;
  const _SectionLabel(this.label);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 8),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w800,
          color: AppTheme.primary,
          letterSpacing: 1.2,
        ),
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  final List<Widget> children;
  const _SettingsCard({required this.children});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Material(
        color: AppTheme.surface,
        clipBehavior: Clip.antiAlias,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: AppTheme.border),
        ),
        child: Column(children: children),
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? value;
  final VoidCallback onTap;
  const _SettingsTile({required this.icon, required this.label, this.value, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
      leading: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: AppTheme.primaryLight,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: AppTheme.primary, size: 20),
      ),
      title: Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: AppTheme.textPrimary)),
      subtitle: value != null ? Text(value!, style: const TextStyle(fontSize: 13, color: AppTheme.textSecond)) : null,
      trailing: const Icon(Icons.chevron_right_rounded, color: AppTheme.textMuted, size: 20),
      onTap: onTap,
    );
  }
}
