import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/schedule.dart';
import '../providers/auth_provider.dart';
import '../providers/schedule_provider.dart';
import '../widgets/chat_widget.dart';
import '../widgets/app_drawer.dart';
import '../widgets/schedule_list_tile.dart';
import '../utils/error_handler.dart';
import '../widgets/add_action_sheet.dart';
import 'add_schedule_screen.dart';
import 'map_screen.dart';
import '../services/notification_service.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';
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

  void _logout() async {
    await Provider.of<AuthProvider>(context, listen: false).logout();
    Navigator.pushReplacementNamed(context, '/login');
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
      print('--- Timer Tick: Checking Schedules (Every 1 Min) ---');
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
            Text('活動快到囉！'),
          ],
        ),
        content: Text(
          '您的行程「${schedule.title}」將在 $minutesUntilStart 分鐘後開始！',
          style: TextStyle(fontSize: 16),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('知道了', style: TextStyle(fontWeight: FontWeight.bold)),
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
            child: Text('查看地圖'),
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
        print('Check ComingSoon match: ${s.title} | Diff: ${minutes}m');
      }

      return inWindow;
    }).toList();

    print(
        'Found ${comingSoonSchedules.length} schedules to update to Coming Soon');

    for (var schedule in comingSoonSchedules) {
      print('Updating status to Coming Soon for ${schedule.title}');
      try {
        await apiService.updateStatus(schedule.id, ScheduleStatus.comingSoon);
        statusUpdated = true;
      } catch (e) {
        print('Failed to auto-update status: $e');
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
      print('Location error: $e');
    }

    if (position == null) return;

    final apiService = ApiService();

    print('Found ${targetSchedules.length} started schedules to check.');

    for (var schedule in targetSchedules) {
      if (schedule.latitude == null || schedule.longitude == null) {
        print('Skipping ${schedule.title}: No location data (lat/lon is null)');
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
            print(
                'Schedule ${schedule.title}: Estimated arrival $estimatedArrivalTime is past allowed time $latestAllowedTime. Marking Not Attended.');
            newStatus = ScheduleStatus.notAttended;
          } else {
            print(
                'Schedule ${schedule.title}: Can still make it. Est arrival $estimatedArrivalTime.');
            continue; // Still give them time
          }
        } catch (e) {
          print('Failed to get travel estimate for ${schedule.title}: $e');
          // Fallback to strict 30-minute rule if API fails
          final minutesLate = now.difference(referenceTime).inMinutes;
          if (minutesLate > 30) {
            newStatus = ScheduleStatus.notAttended;
          } else {
            continue;
          }
        }
      }

      print('Updating status to $newStatus for ${schedule.title}');
      try {
        await apiService.updateStatus(schedule.id, newStatus);
        statusUpdated = true;
      } catch (e) {
        print('Failed to auto-update status: $e');
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

      // 24 hours before
      final reminder24h = startTime.subtract(Duration(hours: 24));
      if (reminder24h.isAfter(now)) {
        await notificationService.scheduleNotification(
          id: schedule.id.hashCode,
          title: '行程提醒: ${schedule.title}',
          body: '您的行程將在 24 小時後開始',
          scheduledTime: reminder24h,
        );
      }

      // 3 hours before
      final reminder3h = startTime.subtract(Duration(hours: 3));
      if (reminder3h.isAfter(now)) {
        await notificationService.scheduleNotification(
          id: schedule.id.hashCode + 1,
          title: '行程準備: ${schedule.title}',
          body: '您的行程將在 3 小時後開始',
          scheduledTime: reminder3h,
        );
      }

      // 2 hours before - Attend / Cancel Prompt
      final reminder2h = startTime.subtract(Duration(hours: 2));
      if (reminder2h.isAfter(now)) {
        await notificationService.scheduleNotification(
          id: schedule.id.hashCode + 3, // Unique ID offset
          title: '行程即將開始: ${schedule.title}',
          body: '您的行程將在 2 小時後開始，請問是否確定出席？請開啟 App 確認或取消。',
          scheduledTime: reminder2h,
        );
      }

      // 30 minutes before
      final reminder30m = startTime.subtract(Duration(minutes: 30));
      if (reminder30m.isAfter(now)) {
        await notificationService.scheduleNotification(
          id: schedule.id.hashCode + 2,
          title: '行程即將開始: ${schedule.title}',
          body: '您的行程將在 30 分鐘後開始，請準備出發！',
          scheduledTime: reminder30m,
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
      appBar: AppBar(
        title: Text('mySchedules'.tr()),
        actions: [
          IconButton(
            icon: Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
            tooltip: 'Filter',
          ),
          IconButton(icon: Icon(Icons.refresh), onPressed: _refreshSchedules),
        ],
      ),
      drawer: AppDrawer(onLogout: _logout),
      body: Consumer<ScheduleProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return Center(child: CircularProgressIndicator());
          }

          if (provider.error != null) {
            // Handle unauthorized via ErrorHandler if needed, basically same logic
            // But simpler here: just show text
            return Center(
              child: Text(
                '${'error'.tr()}: ${provider.error}',
              ),
            );
          }

          // Apply filters
          final filteredSchedules = provider.schedules.where((s) {
            // Status Filter
            if (_filterStatus != null && s.status != _filterStatus) {
              return false;
            }
            // Location Filter
            if (_filterLocation != null && _filterLocation!.isNotEmpty) {
              if (s.location == null ||
                  !s.location!.toLowerCase().contains(
                        _filterLocation!.toLowerCase(),
                      )) {
                return false;
              }
            }
            // Date Range Filter
            if (_filterStartDate != null && _filterEndDate != null) {
              // Check if schedule overlaps or is within range? Usually just check start time.
              // Let's check if start time is within the range [start, end + 1 day (exclusive)] to include end date fully.
              final endOfDay = _filterEndDate!
                  .add(Duration(days: 1))
                  .subtract(Duration(milliseconds: 1));
              if (s.startTime.isBefore(_filterStartDate!) ||
                  s.startTime.isAfter(endOfDay)) {
                return false;
              }
            }
            return true;
          }).toList();

          if (filteredSchedules.isEmpty) {
            return Center(
              child: Text('noSchedules'.tr()),
            );
          }

          return ListView.builder(
            itemCount: filteredSchedules.length,
            itemBuilder: (context, index) {
              final schedule = filteredSchedules[index];
              return ScheduleListTile(
                schedule: schedule,
                onTap: () {
                  if (schedule.status == ScheduleStatus.cancel) {
                    // Do nothing for cancelled schedules
                    return;
                  }

                  final now = DateTime.now();
                  if (schedule.startTime.isBefore(now) &&
                      schedule.status != ScheduleStatus.attend) {
                    // Past schedule interaction (Pending, ComingSoon, NotAttended)
                    _showPastScheduleActionDialog(schedule);
                  } else {
                    // Normal navigation
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MapScreen(schedule: schedule),
                      ),
                    ).then((_) {
                      // Refresh schedules in case they were edited in the MapScreen
                      _refreshSchedules();
                    });
                  }
                },
              );
            },
          );
        },
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      floatingActionButton: FloatingActionButton(
        heroTag: 'add_schedule',
        onPressed: () async {
          await AddActionSheet.show(context);
          _refreshSchedules();
        },
        child: Icon(Icons.add),
        backgroundColor: Colors.blue,
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
        content: Text('此行程時間已過，您想要？'),
        actions: [
          TextButton(
            onPressed: () async {
              Navigator.pop(context); // Close dialog
              await _handleCancelSchedule(schedule);
            },
            child: Text('取消行程', style: TextStyle(color: Colors.red)),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              _showReschedulePicker(schedule);
            },
            child: Text('更改時間'),
          ),
        ],
      ),
    );
  }

  Future<void> _handleCancelSchedule(Schedule schedule) async {
    try {
      final apiService = ApiService();
      await apiService.updateStatus(schedule.id, ScheduleStatus.cancel);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('行程已取消')),
        );
        _refreshSchedules();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('取消失敗: $e')),
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
      helpText: '選擇開始日期',
    );

    if (pickedStartDate != null) {
      // 2. Pick Start Time
      final TimeOfDay? pickedStartTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(now.add(Duration(minutes: 30))),
        helpText: '選擇開始時間',
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
              SnackBar(content: Text('請選擇未來的開始時間')),
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
        final DateTime? pickedEndDate = await showDatePicker(
          context: context,
          initialDate: initialEndDateTime,
          firstDate: newStartDateTime, // End date cannot be before start date
          lastDate: DateTime(2101),
          helpText: '選擇結束日期',
        );

        if (pickedEndDate != null) {
          // 4. Pick End Time
          final TimeOfDay? pickedEndTime = await showTimePicker(
            context: context,
            initialTime: TimeOfDay.fromDateTime(initialEndDateTime),
            helpText: '選擇結束時間',
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
                  SnackBar(content: Text('結束時間必須晚於開始時間')),
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
            content: Text('✅ 行程時間已更新'),
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
            content: Text('❌ 更新失敗: $e'),
            duration: Duration(seconds: 4),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
