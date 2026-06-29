import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/schedule.dart';
import '../providers/auth_provider.dart';
import '../providers/schedule_provider.dart';
import '../widgets/schedule_list_tile.dart';
import 'map_screen.dart';
import '../services/notification_service.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';
import '../providers/settings_provider.dart';
import '../theme/app_theme.dart';
import 'main_shell.dart';
import 'dart:async';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final NotificationService notificationService = NotificationService();
  Timer? _statusCheckTimer; // Added timer
  final Set<String> _alertedScheduleIds =
      {}; // Track which schedules we've shown in-app alerts for

  // Filter State
  String? _filterStatus;
  String? _filterLocation;
  DateTime? _filterStartDate;
  DateTime? _filterEndDate;

  @override
  void initState() {
    super.initState();
    notificationService.init();
    // Fetch data on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _refreshSchedules();
      Provider.of<AuthProvider>(context, listen: false).fetchUserProfile();
    });
  }

  @override
  void dispose() {
    _statusCheckTimer?.cancel();
    super.dispose();
  }

  Future<void> _refreshSchedules() async {
    final scheduleProvider = Provider.of<ScheduleProvider>(
      context,
      listen: false,
    );
    await scheduleProvider.fetchSchedules();
    _scheduleReminders(scheduleProvider.schedules);
    _checkScheduleArrivals(scheduleProvider.schedules);
    _checkComingSoon(scheduleProvider.schedules);

    // Start periodic check if not running
    _statusCheckTimer?.cancel();
    _statusCheckTimer = Timer.periodic(Duration(minutes: 1), (timer) {
      debugPrint('--- Timer Tick: Checking Schedules (Every 1 Min) ---');
      _checkScheduleArrivals(scheduleProvider.schedules);
      _checkComingSoon(scheduleProvider.schedules);
      _checkUpcomingReminders(scheduleProvider.schedules);
    });

    // Check initially as well
    _checkUpcomingReminders(scheduleProvider.schedules);
  }

  void _checkUpcomingReminders(List<Schedule> schedules) {
    if (!mounted) return;
    final now = DateTime.now();

    for (var schedule in schedules) {
      if (schedule.status == ScheduleStatus.cancel ||
          schedule.status == ScheduleStatus.notGoing) continue;

      final diff = schedule.startTime.difference(now);
      final minutesUntilStart = diff.inMinutes;

      // If the schedule is upcoming within 30 minutes and we haven't alerted yet
      if (minutesUntilStart <= 30 && minutesUntilStart >= 0) {
        if (!_alertedScheduleIds.contains(schedule.id)) {
          _alertedScheduleIds.add(schedule.id);
          _showUpcomingReminderDialog(schedule, minutesUntilStart);
        }
      }
    }
  }

  void _showUpcomingReminderDialog(Schedule schedule, int minutesUntilStart) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.notifications_active, color: Colors.amber, size: 28),
            SizedBox(width: 8),
            Text('upcomingScheduleTitle'.tr()),
          ],
        ),
        content: Text(
          'upcomingScheduleBody'.tr(namedArgs: {'title': schedule.title, 'minutes': minutesUntilStart.toString()}),
          style: TextStyle(fontSize: 16),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('gotIt'.tr(), style: TextStyle(fontWeight: FontWeight.bold)),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (context) => MapScreen(schedule: schedule)),
              );
            },
            child: Text('viewMap'.tr()),
          ),
        ],
      ),
    );
  }

  Future<void> _checkComingSoon(List<Schedule> schedules) async {
    final now = DateTime.now();
    bool statusUpdated = false;
    final apiService = ApiService();

    final comingSoonSchedules = schedules.where((s) {
      if (s.status != ScheduleStatus.pending) return false;

      final diff = s.startTime.difference(now);
      final minutes = diff.inMinutes;

      // Range: -60 mins (late) to +120 mins (coming soon)
      // If it's more than 60 mins late, _checkScheduleArrivals handles it (NotAttended)
      // If it's more than 120 mins future, it's just Pending
      final inWindow = minutes > -60 && minutes < 120;

      if (inWindow) {
        debugPrint('Check ComingSoon match: ${s.title} | Diff: ${minutes}m');
      }

      return inWindow;
    }).toList();

    debugPrint(
        'Found ${comingSoonSchedules.length} schedules to update to Coming Soon');

    for (var schedule in comingSoonSchedules) {
      debugPrint('Updating status to Coming Soon for ${schedule.title}');
      try {
        await apiService.updateStatus(schedule.id, ScheduleStatus.comingSoon);
        statusUpdated = true;
      } catch (e) {
        debugPrint('Failed to auto-update status: $e');
      }
    }

    if (statusUpdated) {
      final scheduleProvider = Provider.of<ScheduleProvider>(
        context,
        listen: false,
      );
      await scheduleProvider.fetchSchedules();
    }
  }

  Future<void> _checkScheduleArrivals(List<Schedule> schedules) async {
    final now = DateTime.now();
    bool statusUpdated = false;

    // Filter pending/comingSoon schedules that have started
    final targetSchedules = schedules
        .where(
          (s) =>
              (s.status == ScheduleStatus.pending ||
                  s.status == ScheduleStatus.comingSoon) &&
              s.startTime.isBefore(now),
        )
        .toList();

    if (targetSchedules.isEmpty) return;

    // Get current location
    Position? position;
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (serviceEnabled) {
        LocationPermission permission = await Geolocator.checkPermission();
        if (permission == LocationPermission.denied) {
          permission = await Geolocator.requestPermission();
        }
        if (permission == LocationPermission.whileInUse ||
            permission == LocationPermission.always) {
          position = await Geolocator.getCurrentPosition();
        }
      }
    } catch (e) {
      debugPrint('Location error: $e');
    }

    if (position == null) return;

    final apiService = ApiService();

    debugPrint('Found ${targetSchedules.length} started schedules to check.');

    for (var schedule in targetSchedules) {
      if (schedule.latitude == null || schedule.longitude == null) {
        debugPrint('Skipping ${schedule.title}: No location data (lat/lon is null)');
        continue;
      }

      final distance = Geolocator.distanceBetween(
        position.latitude,
        position.longitude,
        schedule.latitude!,
        schedule.longitude!,
      );

      String newStatus;
      // If within 500 meters, consider attended
      if (distance <= 500) {
        newStatus = ScheduleStatus.attend;
      } else {
        // Dynamic Late Check: Estimate travel time
        final referenceTime = schedule.startTime;
        final mode = schedule.transportMode ?? 'car';

        try {
          // Fetch travel time estimate
          final estimateData = await apiService.estimateTravelTime(
              position.latitude,
              position.longitude,
              schedule.latitude!,
              schedule.longitude!,
              mode);

          final int travelMinutes = (estimateData['duration'] as num).round();
          final estimatedArrivalTime =
              now.add(Duration(minutes: travelMinutes));

          // If estimated arrival > start time + 15 mins grace period, mark as Not Attended
          final latestAllowedTime = referenceTime.add(Duration(minutes: 15));

          if (estimatedArrivalTime.isAfter(latestAllowedTime)) {
            debugPrint(
                'Schedule ${schedule.title}: Estimated arrival $estimatedArrivalTime is past allowed time $latestAllowedTime. Marking Not Attended.');
            newStatus = ScheduleStatus.notAttended;
          } else {
            debugPrint(
                'Schedule ${schedule.title}: Can still make it. Est arrival $estimatedArrivalTime.');
            continue; // Still give them time
          }
        } catch (e) {
          debugPrint('Failed to get travel estimate for ${schedule.title}: $e');
          // Fallback to strict 30-minute rule if API fails
          final minutesLate = now.difference(referenceTime).inMinutes;
          if (minutesLate > 30) {
            newStatus = ScheduleStatus.notAttended;
          } else {
            continue;
          }
        }
      }

      debugPrint('Updating status to $newStatus for ${schedule.title}');
      try {
        await apiService.updateStatus(schedule.id, newStatus);
        statusUpdated = true;
      } catch (e) {
        debugPrint('Failed to auto-update status: $e');
      }
    }

    if (statusUpdated) {
      final scheduleProvider = Provider.of<ScheduleProvider>(
        context,
        listen: false,
      );
      // Refresh without loop
      await scheduleProvider.fetchSchedules();
    }
  }

  void _scheduleReminders(List<Schedule> schedules) async {
    await notificationService.cancelAllNotifications();
    for (var schedule in schedules) {
      if (schedule.status == ScheduleStatus.cancel) continue;

      final now = DateTime.now();
      final startTime = schedule.startTime;
      final args = {'title': schedule.title};

      // 2 hours before
      final reminder2h = startTime.subtract(Duration(hours: 2));
      if (reminder2h.isAfter(now)) {
        await notificationService.scheduleNotification(
          id: schedule.id.hashCode,
          title: 'reminder2hTitle'.tr(namedArgs: args),
          body: 'reminder2hBody'.tr(namedArgs: args),
          scheduledTime: reminder2h,
        );
      }

      // 1 hour before
      final reminder1h = startTime.subtract(Duration(hours: 1));
      if (reminder1h.isAfter(now)) {
        await notificationService.scheduleNotification(
          id: schedule.id.hashCode + 1,
          title: 'reminder1hTitle'.tr(namedArgs: args),
          body: 'reminder1hBody'.tr(namedArgs: args),
          scheduledTime: reminder1h,
        );
      }
    }
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) {
        String? tempStatus = _filterStatus;
        TextEditingController tempLocationController = TextEditingController(
          text: _filterLocation,
        );
        DateTime? tempStartDate = _filterStartDate;
        DateTime? tempEndDate = _filterEndDate;

        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: Text('filterSchedules'.tr()),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Status Filter
                    DropdownButtonFormField<String>(
                      value: tempStatus,
                      decoration: InputDecoration(labelText: 'Status'),
                      items: [
                        DropdownMenuItem(value: null, child: Text('all'.tr())),
                        DropdownMenuItem(
                          value: ScheduleStatus.pending,
                          child: Text('statusPending'.tr()),
                        ),
                        DropdownMenuItem(
                          value: ScheduleStatus.comingSoon,
                          child: Text('statusComingSoon'.tr()),
                        ),
                        DropdownMenuItem(
                          value: ScheduleStatus.active,
                          child: Text('statusActive'.tr()),
                        ),
                        DropdownMenuItem(
                          value: ScheduleStatus.notGoing,
                          child: Text('statusNotGoing'.tr()),
                        ),
                        DropdownMenuItem(
                          value: ScheduleStatus.cancel,
                          child: Text('statusCancelled'.tr()),
                        ),
                      ],
                      onChanged: (val) => setState(() => tempStatus = val),
                    ),
                    SizedBox(height: 16),
                    // Location Filter
                    TextField(
                      controller: tempLocationController,
                      decoration: InputDecoration(
                        labelText: 'location'.tr(),
                      ),
                    ),
                    SizedBox(height: 16),
                    // Date Range Filter
                    ListTile(
                      title: Text('dateRange'.tr()),
                      subtitle: Text(
                        tempStartDate != null && tempEndDate != null
                            ? '${DateFormat('yyyy-MM-dd').format(tempStartDate!)} - ${DateFormat('yyyy-MM-dd').format(tempEndDate!)}'
                            : 'All Time',
                      ),
                      trailing: Icon(Icons.calendar_today),
                      onTap: () async {
                        final picked = await showDateRangePicker(
                          context: context,
                          firstDate: DateTime(2000),
                          lastDate: DateTime(2101),
                          initialDateRange:
                              tempStartDate != null && tempEndDate != null
                                  ? DateTimeRange(
                                      start: tempStartDate!,
                                      end: tempEndDate!,
                                    )
                                  : null,
                        );
                        if (picked != null) {
                          setState(() {
                            tempStartDate = picked.start;
                            tempEndDate = picked.end;
                          });
                        }
                      },
                    ),
                    if (tempStartDate != null)
                      TextButton(
                        onPressed: () {
                          setState(() {
                            tempStartDate = null;
                            tempEndDate = null;
                          });
                        },
                        child: Text('clearDateFilter'.tr()),
                      ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    // Clear all
                    setState(() {
                      tempStatus = null;
                      tempLocationController.clear();
                      tempStartDate = null;
                      tempEndDate = null;
                    });
                  },
                  child: Text('reset'.tr()),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: Text('cancel'.tr()),
                ),
                ElevatedButton(
                  onPressed: () {
                    this.setState(() {
                      _filterStatus = tempStatus;
                      _filterLocation = tempLocationController.text.isEmpty
                          ? null
                          : tempLocationController.text;
                      _filterStartDate = tempStartDate;
                      _filterEndDate = tempEndDate;
                    });
                    Navigator.pop(context);
                  },
                  child: Text('apply'.tr()),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
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
        title: const Text(
          'Schedulo',
          style: TextStyle(
            color: AppTheme.primary,
            fontWeight: FontWeight.w800,
            fontSize: 20,
            letterSpacing: -0.5,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.tune_rounded, color: AppTheme.textSecond),
            onPressed: _showFilterDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: AppTheme.textSecond),
            onPressed: _refreshSchedules,
          ),
        ],
      ),
      body: CustomScrollView(
        slivers: [
          // ── Greeting header ──────────────────────────────
          SliverToBoxAdapter(child: _GreetingHeader()),

          // ── Schedule list ────────────────────────────────
          Consumer2<ScheduleProvider, SettingsProvider>(
            builder: (context, provider, settings, _) {
              if (provider.isLoading) {
                return const SliverFillRemaining(child: Center(child: CircularProgressIndicator()));
              }
              if (provider.error != null) {
                return SliverFillRemaining(
                  child: Center(child: Text('${'error'.tr()}: ${provider.error}')),
                );
              }

              final filtered = provider.schedules.where((s) {
                if (!settings.isVisible(s.status)) return false;
                if (_filterStatus != null && s.status != _filterStatus) return false;
                if (_filterLocation != null && _filterLocation!.isNotEmpty) {
                  if (s.location == null ||
                      !s.location!.toLowerCase().contains(_filterLocation!.toLowerCase())) return false;
                }
                if (_filterStartDate != null && _filterEndDate != null) {
                  final endOfDay = _filterEndDate!.add(const Duration(days: 1)).subtract(const Duration(milliseconds: 1));
                  if (s.startTime.isBefore(_filterStartDate!) || s.startTime.isAfter(endOfDay)) return false;
                }
                return true;
              }).toList();

              if (filtered.isEmpty) {
                return SliverFillRemaining(
                  child: _EmptyState(),
                );
              }

              return SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, i) {
                    final schedule = filtered[i];
                    return GestureDetector(
                      onLongPress: () => _confirmDeleteSchedule(schedule),
                      child: ScheduleListTile(
                        schedule: schedule,
                        onTap: () {
                          if (schedule.status == ScheduleStatus.cancel) return;
                          final now = DateTime.now();
                          if (schedule.startTime.isBefore(now) && schedule.status != ScheduleStatus.attend) {
                            _showPastScheduleActionDialog(schedule);
                          } else {
                            Navigator.push(context, MaterialPageRoute(builder: (_) => MapScreen(schedule: schedule)))
                                .then((_) => _refreshSchedules());
                          }
                        },
                      ),
                    );
                  },
                  childCount: filtered.length,
                ),
              );
            },
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 80)),
        ],
      ),
    );
  }

  void _showPastScheduleActionDialog(Schedule schedule) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
                child:
                    Text('${schedule.title}', overflow: TextOverflow.ellipsis)),
            IconButton(
              icon: Icon(Icons.close),
              onPressed: () => Navigator.pop(context),
              padding: EdgeInsets.zero,
              constraints: BoxConstraints(),
            ),
          ],
        ),
        content: Text('pastScheduleAction'.tr()),
        actions: [
          TextButton(
            onPressed: () async {
              Navigator.pop(context); // Close dialog
              await _handleCancelSchedule(schedule);
            },
            child: Text('cancelSchedule'.tr(), style: TextStyle(color: Colors.red)),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              _showReschedulePicker(schedule);
            },
            child: Text('changeTime'.tr()),
          ),
        ],
      ),
    );
  }

  Future<void> _handleCancelSchedule(Schedule schedule) async {
    final confirmed = await showDialog<String>(
      context: context,
      builder: (ctx) => _CancelDialog(scheduleTitle: schedule.title),
    );

    if (confirmed == null || !mounted) return;

    try {
      final apiService = ApiService();
      await apiService.updateStatus(
        schedule.id,
        ScheduleStatus.cancel,
        cancelReason: confirmed,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('scheduleCancelled'.tr())),
        );
        _refreshSchedules();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('cancelFailed'.tr(namedArgs: {'error': e.toString()}))),
        );
      }
    }
  }

  Future<void> _confirmDeleteSchedule(Schedule schedule) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('deleteSchedule'.tr()),
        content: Text('confirmDeleteSchedule'.tr(namedArgs: {'title': schedule.title})),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text('cancel'.tr()),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: Text('delete'.tr()),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    try {
      await ApiService().deleteSchedule(schedule.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('scheduleDeleted'.tr(namedArgs: {'title': schedule.title}))),
        );
        _refreshSchedules();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('deleteScheduleFailed'.tr(namedArgs: {'error': e.toString()}))),
        );
      }
    }
  }

  void _showReschedulePicker(Schedule schedule) async {
    final now = DateTime.now();
    final firstDate = now;

    // 1. Pick Start Date
    final DateTime? pickedStartDate = await showDatePicker(
      context: context,
      initialDate: now.add(Duration(minutes: 5)),
      firstDate: firstDate,
      lastDate: DateTime(2101),
      helpText: 'selectStartDate'.tr(),
    );

    if (pickedStartDate != null) {
      // 2. Pick Start Time
      if (!mounted) return;
      final TimeOfDay? pickedStartTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(now.add(Duration(minutes: 30))),
        helpText: 'selectStartTime'.tr(),
      );

      if (pickedStartTime != null) {
        final newStartDateTime = DateTime(
          pickedStartDate.year,
          pickedStartDate.month,
          pickedStartDate.day,
          pickedStartTime.hour,
          pickedStartTime.minute,
        );

        if (newStartDateTime.isBefore(now)) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('pleaseEnterFutureTime'.tr())),
            );
          }
          return;
        }

        // Calculate initial end time based on original duration
        Duration originalDuration = Duration(hours: 1); // Default
        if (schedule.endTime != null) {
          originalDuration = schedule.endTime!.difference(schedule.startTime);
        }
        DateTime initialEndDateTime = newStartDateTime.add(originalDuration);

        // 3. Pick End Date (Default to Start Date or calculated End Date)
        if (!mounted) return;
        final DateTime? pickedEndDate = await showDatePicker(
          context: context,
          initialDate: initialEndDateTime,
          firstDate: newStartDateTime, // End date cannot be before start date
          lastDate: DateTime(2101),
          helpText: 'selectEndDate'.tr(),
        );

        if (pickedEndDate != null) {
          // 4. Pick End Time
          if (!mounted) return;
          final TimeOfDay? pickedEndTime = await showTimePicker(
            context: context,
            initialTime: TimeOfDay.fromDateTime(initialEndDateTime),
            helpText: 'selectEndTime'.tr(),
          );

          if (pickedEndTime != null) {
            final newEndDateTime = DateTime(
              pickedEndDate.year,
              pickedEndDate.month,
              pickedEndDate.day,
              pickedEndTime.hour,
              pickedEndTime.minute,
            );

            if (newEndDateTime.isBefore(newStartDateTime)) {
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('endTimeMustBeAfterStartTime'.tr())),
                );
              }
              return;
            }

            await _handleReschedule(schedule, newStartDateTime, newEndDateTime);
          }
        }
      }
    }
  }

  Future<void> _handleReschedule(
      Schedule schedule, DateTime newStartTime, DateTime newEndTime) async {
    // Show loading dialog
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => Center(child: CircularProgressIndicator()),
    );

    try {
      final apiService = ApiService();
      await apiService.updateSchedule(schedule.id, {
        'start_time': newStartTime.toIso8601String(),
        'end_time': newEndTime.toIso8601String(),
        'status': ScheduleStatus.pending
      });

      if (mounted) {
        Navigator.of(context).pop(); // Close loading dialog
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('scheduleTimeUpdated'.tr()),
            duration: Duration(seconds: 3),
            backgroundColor: Colors.green,
          ),
        );
        _refreshSchedules();
      }
    } catch (e) {
      if (mounted) {
        Navigator.of(context).pop(); // Close loading dialog
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('updateScheduleFailed'.tr(namedArgs: {'error': e.toString()})),
            duration: Duration(seconds: 4),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}

// ── Greeting header widget ────────────────────────────────────────────────────

class _GreetingHeader extends StatelessWidget {
  const _GreetingHeader();

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'greetingMorning'.tr();
    if (h < 18) return 'greetingAfternoon'.tr();
    return 'greetingEvening'.tr();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.surface,
      padding: const EdgeInsets.fromLTRB(20, 20, 16, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Greeting + date
          Consumer<AuthProvider>(
            builder: (_, auth, __) {
              final name = (auth.user?['full_name'] as String?)?.split(' ').first ?? '';
              return Text(
                name.isNotEmpty ? '${_greeting()}, $name' : _greeting(),
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.textPrimary,
                  letterSpacing: -0.5,
                ),
              );
            },
          ),
          const SizedBox(height: 4),
          Text(
            DateFormat('EEEE, d MMMM').format(DateTime.now()),
            style: const TextStyle(fontSize: 14, color: AppTheme.textSecond),
          ),
          const SizedBox(height: 16),
          Text(
            'mySchedules'.tr(),
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: AppTheme.textSecond,
              letterSpacing: 0.8,
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: AppTheme.primaryLight,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.event_note_outlined, size: 40, color: AppTheme.primary),
          ),
          const SizedBox(height: 20),
          Text(
            'noSchedules'.tr(),
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
          ),
          const SizedBox(height: 8),
          Text(
            'noSchedulesHint'.tr(),
            style: const TextStyle(fontSize: 14, color: AppTheme.textSecond),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

/// Separate StatefulWidget dialog so the FocusNode is requested AFTER
/// the dialog is fully mounted — fixes Chinese IME input on iOS/Android.
class _CancelDialog extends StatefulWidget {
  final String scheduleTitle;
  const _CancelDialog({required this.scheduleTitle});

  @override
  State<_CancelDialog> createState() => _CancelDialogState();
}

class _CancelDialogState extends State<_CancelDialog> {
  final _formKey = GlobalKey<FormState>();
  final _reasonController = TextEditingController();
  final _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    // Request focus after the dialog is fully rendered so IME initializes correctly
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _reasonController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('cancelSchedule'.tr()),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.scheduleTitle,
                style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextFormField(
              controller: _reasonController,
              focusNode: _focusNode,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: 'cancelReason'.tr(),
                hintText: 'cancelReasonHint'.tr(),
                border: const OutlineInputBorder(),
              ),
              validator: (v) =>
                  (v == null || v.trim().isEmpty)
                      ? 'cancelReasonRequired'.tr()
                      : null,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('cancel'.tr()),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red, foregroundColor: Colors.white),
          onPressed: () {
            if (!_formKey.currentState!.validate()) return;
            Navigator.pop(context, _reasonController.text.trim());
          },
          child: Text('confirm'.tr()),
        ),
      ],
    );
  }
}
