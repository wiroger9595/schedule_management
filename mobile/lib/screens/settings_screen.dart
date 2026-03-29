import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/settings_provider.dart';
import '../utils/constants.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

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

  @override
  Widget build(BuildContext context) {
    final currentLocale = context.locale;
    final settings = context.watch<SettingsProvider>();

    // 已選幾個語言 / 已勾幾個狀態 → 顯示在 subtitle
    final selectedLang = _languages.firstWhere(
      (l) => (l['locale'] as Locale) == currentLocale,
      orElse: () => _languages.first,
    )['label'] as String;

    final visibleCount = _statusItems(context)
        .where((item) => settings.isVisible(item['status']!))
        .length;
    final totalCount = _statusItems(context).length;

    return Scaffold(
      appBar: AppBar(
        title: Text('settings'.tr()),
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

          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
