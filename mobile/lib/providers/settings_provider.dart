import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/constants.dart';

class SettingsProvider extends ChangeNotifier {
  static const _key = 'visible_schedule_statuses';

  // Default: show all statuses
  static const List<String> allStatuses = [
    ScheduleStatus.pending,
    ScheduleStatus.comingSoon,
    ScheduleStatus.active,
    ScheduleStatus.attend,
    ScheduleStatus.notGoing,
    ScheduleStatus.notAttended,
    ScheduleStatus.cancel,
  ];

  Set<String> _visibleStatuses = Set.from(allStatuses);

  Set<String> get visibleStatuses => _visibleStatuses;

  SettingsProvider() {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getStringList(_key);
    if (saved != null) {
      _visibleStatuses = Set.from(saved);
      notifyListeners();
    }
  }

  Future<void> setStatusVisible(String status, bool visible) async {
    if (visible) {
      _visibleStatuses.add(status);
    } else {
      _visibleStatuses.remove(status);
    }
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_key, _visibleStatuses.toList());
  }

  bool isVisible(String status) => _visibleStatuses.contains(status);
}
