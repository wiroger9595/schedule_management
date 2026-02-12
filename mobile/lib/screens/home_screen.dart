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
import 'add_schedule_screen.dart';
import 'map_screen.dart';
import '../services/notification_service.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';
import '../i18n/app_localizations.dart';
import '../utils/constants.dart';
import 'dart:async';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final NotificationService notificationService = NotificationService();
  Timer? _statusCheckTimer; // Added timer

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

    // Start periodic check if not running
    _statusCheckTimer?.cancel();
    _statusCheckTimer = Timer.periodic(Duration(hours: 2), (timer) {
      print('--- Timer Tick: Checking Schedules ---');
      _checkScheduleArrivals(scheduleProvider.schedules);
    });
  }

  Future<void> _checkScheduleArrivals(List<Schedule> schedules) async {
    final now = DateTime.now();
    bool statusUpdated = false;

    // Filter pending schedules that have started or are about to start
    // Filter pending schedules that have started
    // We want to check any pending schedule that has started.
    final pendingSchedules = schedules
        .where(
          (s) =>
              s.status == ScheduleStatus.pending && s.startTime.isBefore(now),
        )
        .toList();

    if (pendingSchedules.isEmpty) return;

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

    print('Found ${pendingSchedules.length} pending started schedules.');

    for (var schedule in pendingSchedules) {
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
        // If time passed and not there...
        // Updated logic: Check every minute.
        // If > 60 mins past start time and still not there -> Not Going.
        final minutesLate = now.difference(schedule.startTime).inMinutes;
        print(
          'Schedule ${schedule.title}: $minutesLate mins late, distance ${distance.toStringAsFixed(2)}m',
        );

        if (minutesLate > 60) {
          newStatus = ScheduleStatus.notAttended;
        } else {
          print(
            'Not updating ${schedule.title}: Only $minutesLate mins late (threshold > 60)',
          );
          continue; // Still give them time
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
          title: '行程即將開始: ${schedule.title}',
          body: '您的行程將在 3 小時後開始',
          scheduledTime: reminder3h,
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
              title: Text('Filter Schedules'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Status Filter
                    DropdownButtonFormField<String>(
                      value: tempStatus,
                      decoration: InputDecoration(labelText: 'Status'),
                      items: [
                        DropdownMenuItem(value: null, child: Text('All')),
                        DropdownMenuItem(
                          value: ScheduleStatus.pending,
                          child: Text('Pending'),
                        ),
                        DropdownMenuItem(
                          value: ScheduleStatus.active,
                          child: Text('Active'),
                        ),
                        DropdownMenuItem(
                          value: ScheduleStatus.notGoing,
                          child: Text('Not Going'),
                        ),
                        DropdownMenuItem(
                          value: ScheduleStatus.cancel,
                          child: Text('Cancelled'),
                        ),
                      ],
                      onChanged: (val) => setState(() => tempStatus = val),
                    ),
                    SizedBox(height: 16),
                    // Location Filter
                    TextField(
                      controller: tempLocationController,
                      decoration: InputDecoration(
                        labelText: 'Location (contains)',
                      ),
                    ),
                    SizedBox(height: 16),
                    // Date Range Filter
                    ListTile(
                      title: Text('Date Range'),
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
                        child: Text('Clear Date Filter'),
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
                  child: Text('Reset'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: Text('Cancel'),
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
                  child: Text('Apply'),
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
        title: Text(AppLocalizations.of(context)!.mySchedules),
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
                '${AppLocalizations.of(context)!.error}: ${provider.error}',
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
              child: Text(AppLocalizations.of(context)!.noSchedules),
            );
          }

          return ListView.builder(
            itemCount: filteredSchedules.length,
            itemBuilder: (context, index) {
              final schedule = filteredSchedules[index];
              return ScheduleListTile(
                schedule: schedule,
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => MapScreen(schedule: schedule),
                    ),
                  );
                },
              );
            },
          );
        },
      ),
      floatingActionButton: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          // AI 助手按鈕
          FloatingActionButton(
            heroTag: 'ai_chat',
            onPressed: () {
              showModalBottomSheet(
                context: context,
                isScrollControlled: true,
                backgroundColor: Colors.transparent,
                builder: (context) =>
                    ChatWidget(onScheduleCreated: _refreshSchedules),
              );
            },
            child: Icon(Icons.assistant),
            backgroundColor: Colors.purple[700],
          ),
          SizedBox(height: 16),
          // 原有的新增按鈕
          FloatingActionButton(
            heroTag: 'add_schedule',
            onPressed: () async {
              await Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => AddScheduleScreen()),
              );
              _refreshSchedules();
            },
            child: Icon(Icons.add),
            backgroundColor: Colors.blue,
          ),
        ],
      ),
    );
  }
}
