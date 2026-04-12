import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/settings_provider.dart';
import '../utils/constants.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // Local state — avoids watching AuthProvider in build (prevents ExpansionTile collapse on rebuild)
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
    // Use post-frame callback so the widget tree is fully built before reading providers
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final sending = context.read<AuthProvider>().user?['default_sending'];
      if (sending != null && sending is String) {
        setState(() => _defaultSending = sending);
      }
    });
  }

  Future<void> _setNotificationMethod(String value) async {
    // Optimistic local update — UI responds immediately, no rebuild from auth
    setState(() => _defaultSending = value);
    try {
      await context.read<AuthProvider>().updateProfile({'default_sending': value});
    } catch (_) {
      // Revert on failure
      if (mounted) {
        final auth = context.read<AuthProvider>();
        setState(() => _defaultSending = auth.user?['default_sending'] ?? 'line');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentLocale = context.locale;
    final settings = context.watch<SettingsProvider>();
    // Do NOT watch AuthProvider here — use local _defaultSending instead

    final selectedLang = _languages.firstWhere(
      (l) => (l['locale'] as Locale) == currentLocale,
      orElse: () => _languages.first,
    )['label'] as String;

    final visibleCount = _statusItems(context)
        .where((item) => settings.isVisible(item['status']!))
        .length;
    final totalCount = _statusItems(context).length;

    final currentNotifLabel = _notificationItems
        .firstWhere((n) => n['value'] == _defaultSending,
            orElse: () => _notificationItems.first)['label']!;

    return Scaffold(
      appBar: AppBar(
        title: Text('settings'.tr()),
      ),
      floatingActionButton: FloatingActionButton(
        heroTag: 'ai_chat',
        onPressed: () => Navigator.pushNamed(context, '/home'),
        backgroundColor: Colors.black,
        child: const Icon(Icons.smart_toy_outlined, color: Colors.white),
      ),
      body: ListView(
        children: [
          // ── Language section ──
          ExpansionTile(
            leading: const Icon(Icons.language),
            title: Text(
              'language'.tr(),
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text(
              selectedLang,
              style: TextStyle(fontSize: 13, color: Colors.grey[600]),
            ),
            iconColor: Colors.black,
            collapsedIconColor: Colors.black54,
            childrenPadding: EdgeInsets.zero,
            children: _languages.map((lang) {
              final locale = lang['locale'] as Locale;
              final isSelected = currentLocale == locale;
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 32),
                leading: Icon(
                  Icons.circle,
                  size: 10,
                  color: isSelected ? Colors.black : Colors.transparent,
                ),
                title: Text(
                  lang['label'] as String,
                  style: TextStyle(
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
                trailing:
                    isSelected ? const Icon(Icons.check, color: Colors.black) : null,
                onTap: () {
                  if (!isSelected) context.setLocale(locale);
                },
              );
            }).toList(),
          ),

          const Divider(height: 1),

          // ── My Schedules status section ──
          ExpansionTile(
            leading: const Icon(Icons.list_alt),
            title: Text(
              'mySchedules'.tr(),
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text(
              '$visibleCount / $totalCount',
              style: TextStyle(fontSize: 13, color: Colors.grey[600]),
            ),
            iconColor: Colors.black,
            collapsedIconColor: Colors.black54,
            childrenPadding: EdgeInsets.zero,
            children: _statusItems(context).map((item) {
              final status = item['status']!;
              final isChecked = settings.isVisible(status);
              return CheckboxListTile(
                value: isChecked,
                activeColor: Colors.black,
                checkColor: Colors.white,
                contentPadding: const EdgeInsets.symmetric(horizontal: 32),
                title: Text(item['label']!),
                controlAffinity: ListTileControlAffinity.leading,
                onChanged: (val) =>
                    settings.setStatusVisible(status, val ?? false),
              );
            }).toList(),
          ),

          const Divider(height: 1),

          // ── Default Notification Method section ──
          ExpansionTile(
            leading: const Icon(Icons.notifications_outlined),
            title: Text(
              'defaultNotificationMethod'.tr(),
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text(
              currentNotifLabel,
              style: TextStyle(fontSize: 13, color: Colors.grey[600]),
            ),
            iconColor: Colors.black,
            collapsedIconColor: Colors.black54,
            childrenPadding: EdgeInsets.zero,
            children: _notificationItems.map((item) {
              final isSelected = _defaultSending == item['value'];
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 32),
                leading: Icon(
                  Icons.circle,
                  size: 10,
                  color: isSelected ? Colors.black : Colors.transparent,
                ),
                title: Text(
                  item['label']!,
                  style: TextStyle(
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
                trailing: isSelected
                    ? const Icon(Icons.check, color: Colors.black)
                    : null,
                onTap: () => _setNotificationMethod(item['value']!),
              );
            }).toList(),
          ),

          const Divider(height: 1),

          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
