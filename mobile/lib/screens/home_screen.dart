import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/schedule.dart';
import '../providers/auth_provider.dart';
import '../providers/schedule_provider.dart';
import '../widgets/chat_widget.dart';
import '../utils/error_handler.dart';
import 'add_schedule_screen.dart';
import 'map_screen.dart';
import 'profile_screen.dart';
import 'call_log_screen.dart';
import 'calendar_screen.dart';
import '../services/notification_service.dart';
import 'package:geolocator/geolocator.dart'; // Added
import '../services/api_service.dart'; // Added
import 'contact_list_screen.dart';
import "../l10n/app_localizations.dart";
import '../utils/constants.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final NotificationService notificationService = NotificationService();

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

  void _logout() async {
    await Provider.of<AuthProvider>(context, listen: false).logout();
    Navigator.pushReplacementNamed(context, '/login');
  }

  Future<void> _refreshSchedules() async {
    final scheduleProvider = Provider.of<ScheduleProvider>(context, listen: false);
    await scheduleProvider.fetchSchedules();
    _scheduleReminders(scheduleProvider.schedules);
    _checkScheduleArrivals(scheduleProvider.schedules);
  }

  Future<void> _checkScheduleArrivals(List<Schedule> schedules) async {
    final now = DateTime.now();
    bool statusUpdated = false;

    // Filter pending schedules that have started or are about to start
    final pendingSchedules = schedules.where((s) => 
      s.status == ScheduleStatus.pending && 
      s.startTime.isBefore(now.add(Duration(minutes: 15))) // Check if start time is passed or within 15 mins? 
      // User requirement: "No arrival at time -> pending, cancel... Over time -> attend, not attend"
      // So if time is passed, we check.
      && s.startTime.isBefore(now)
    ).toList();

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
        if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
          position = await Geolocator.getCurrentPosition();
        }
      }
    } catch (e) {
      print('Location error: $e');
    }

    if (position == null) return;

    final apiService = ApiService();

    for (var schedule in pendingSchedules) {
      if (schedule.latitude == null || schedule.longitude == null) continue;

      final distance = Geolocator.distanceBetween(
        position.latitude, 
        position.longitude, 
        schedule.latitude!, 
        schedule.longitude!
      );

      String newStatus;
      // If within 500 meters, consider attended
      if (distance <= 500) {
        newStatus = ScheduleStatus.active; // Map "active" to "Attend" in UI text? 
        // Constants: active='A', pending='P', notGoing='N', cancel='C'.
        // User said: "attend, not attend". 
        // existing 'active' (A) probably means Attended/Going.
        // existing 'notGoing' (N) means Not Attended.
      } else {
        // If time passed and not there...
        // Maybe give a buffer? e.g. 30 mins after start time?
        // User: "Over time state change to attend, not attend".
        // Let's say if > 15 mins past start time and still not there.
        if (now.difference(schedule.startTime).inMinutes > 30) {
           newStatus = ScheduleStatus.notGoing;
        } else {
          continue; // Still give them time
        }
      }

      try {
        await apiService.updateStatus(schedule.id, newStatus);
        statusUpdated = true;
      } catch (e) {
        print('Failed to auto-update status: $e');
      }
    }

    if (statusUpdated) {
      final scheduleProvider = Provider.of<ScheduleProvider>(context, listen: false);
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
        TextEditingController tempLocationController = TextEditingController(text: _filterLocation);
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
                        DropdownMenuItem(value: ScheduleStatus.pending, child: Text('Pending')),
                        DropdownMenuItem(value: ScheduleStatus.active, child: Text('Active')),
                        DropdownMenuItem(value: ScheduleStatus.notGoing, child: Text('Not Going')),
                        DropdownMenuItem(value: ScheduleStatus.cancel, child: Text('Cancelled')),
                      ],
                      onChanged: (val) => setState(() => tempStatus = val),
                    ),
                    SizedBox(height: 16),
                    // Location Filter
                    TextField(
                      controller: tempLocationController,
                      decoration: InputDecoration(labelText: 'Location (contains)'),
                    ),
                    SizedBox(height: 16),
                    // Date Range Filter
                    ListTile(
                      title: Text('Date Range'),
                      subtitle: Text(
                        tempStartDate != null && tempEndDate != null
                            ? '${DateFormat('yyyy-MM-dd').format(tempStartDate!)} - ${DateFormat('yyyy-MM-dd').format(tempEndDate!)}'
                            : 'All Time'
                      ),
                      trailing: Icon(Icons.calendar_today),
                      onTap: () async {
                        final picked = await showDateRangePicker(
                          context: context,
                          firstDate: DateTime(2000),
                          lastDate: DateTime(2101),
                          initialDateRange: tempStartDate != null && tempEndDate != null
                              ? DateTimeRange(start: tempStartDate!, end: tempEndDate!)
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
                      _filterLocation = tempLocationController.text.isEmpty ? null : tempLocationController.text;
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
      drawer: _buildDrawer(),
      body: Consumer<ScheduleProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return Center(child: CircularProgressIndicator());
          }
          
          if (provider.error != null) {
             // Handle unauthorized via ErrorHandler if needed, basically same logic
             // But simpler here: just show text
             return Center(child: Text('${AppLocalizations.of(context)!.error}: ${provider.error}'));
          }

          // Apply filters
          final filteredSchedules = provider.schedules.where((s) {
            // Status Filter
            if (_filterStatus != null && s.status != _filterStatus) {
              return false;
            }
            // Location Filter
            if (_filterLocation != null && _filterLocation!.isNotEmpty) {
              if (s.location == null || !s.location!.toLowerCase().contains(_filterLocation!.toLowerCase())) {
                return false;
              }
            }
            // Date Range Filter
            if (_filterStartDate != null && _filterEndDate != null) {
              // Check if schedule overlaps or is within range? Usually just check start time.
              // Let's check if start time is within the range [start, end + 1 day (exclusive)] to include end date fully.
              final endOfDay = _filterEndDate!.add(Duration(days: 1)).subtract(Duration(milliseconds: 1));
              if (s.startTime.isBefore(_filterStartDate!) || s.startTime.isAfter(endOfDay)) {
                return false;
              }
            }
            return true;
          }).toList();

          if (filteredSchedules.isEmpty) {
            return Center(child: Text(AppLocalizations.of(context)!.noSchedules));
          }

          return ListView.builder(
            itemCount: filteredSchedules.length,
            itemBuilder: (context, index) {
              final schedule = filteredSchedules[index];
              return Card(
                margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                elevation: 4,
                child: ListTile(
                  contentPadding: EdgeInsets.all(16),
                  title: Text(
                    schedule.title,
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(height: 8),
                      Row(
                        children: [
                          Icon(Icons.access_time, size: 16, color: Colors.grey),
                          SizedBox(width: 8),
                          Text(
                            DateFormat(
                              'yyyy-MM-dd HH:mm',
                            ).format(schedule.startTime),
                          ),
                        ],
                      ),
                      if (schedule.location != null) ...[
                        SizedBox(height: 4),
                        Row(
                          children: [
                            Icon(
                              Icons.location_on,
                              size: 16,
                              color: Colors.grey,
                            ),
                            SizedBox(width: 8),
                            Text(schedule.location!),
                          ],
                        ),
                      ],
                      SizedBox(height: 8),
                      Container(
                        padding: EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: _getStatusColor(schedule.status),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          _getStatusText(context, schedule.status),
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MapScreen(schedule: schedule),
                      ),
                    );
                  },
                ),
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
                builder: (context) => ChatWidget(
                  onScheduleCreated: _refreshSchedules,
                ),
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


  Widget _buildDrawer() {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Colors.purple[700]!, Colors.blue[700]!],
              ),
            ),
            child: Consumer<AuthProvider>(
              builder: (context, auth, _) {
                 final user = auth.user;
                 if (user != null) {
                    return Row(
                        children: [
                          GestureDetector(
                            onTap: () async {
                              final result = await Navigator.pushNamed(context, '/profile');
                              if (result == true) {
                                auth.fetchUserProfile();
                              }
                            },
                            child: CircleAvatar(
                              radius: 35,
                              backgroundImage: user['profile_image_path'] != null
                                  ? NetworkImage(user['profile_image_path'])
                                  : null,
                              backgroundColor: Colors.white,
                              child: user['profile_image_path'] == null
                                  ? Icon(Icons.person, size: 40, color: Colors.purple[700])
                                  : null,
                            ),
                          ),
                          SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  user['full_name'] ?? AppLocalizations.of(context)!.user,
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                SizedBox(height: 4),
                                Text(
                                  user['account_number'] ?? '',
                                  style: TextStyle(
                                    color: Colors.white70,
                                    fontSize: 14,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      );
                 }
                 return Center(child: CircularProgressIndicator(color: Colors.white));
              }
            ),
          ),
          ListTile(
            leading: Icon(Icons.person, color: Colors.blue),
            title: Text(AppLocalizations.of(context)!.profile),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => ProfileScreen()),
              );
            },
          ),
          ListTile(
            leading: Icon(Icons.phone, color: Colors.green),
            title: Text(AppLocalizations.of(context)!.callLog),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => CallLogScreen()),
              );
            },
          ),
          ListTile(
            leading: Icon(Icons.calendar_month, color: Colors.orange),
            title: Text(AppLocalizations.of(context)!.calendar),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => CalendarScreen()),
              );
            },
          ),
          ListTile(
            leading: Icon(Icons.people, color: Colors.purple),
            title: Text(AppLocalizations.of(context)!.myContacts),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => ContactListScreen()),
              );
            },
          ),
          Divider(),
          ListTile(
            leading: Icon(Icons.logout, color: Colors.red),
            title: Text(AppLocalizations.of(context)!.logout),
            onTap: _logout,
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case ScheduleStatus.pending:
        return Colors.orange;
      case ScheduleStatus.active:
        return Colors.green;
      case ScheduleStatus.notGoing:
        return Colors.grey;
      case ScheduleStatus.cancel:
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _getStatusText(BuildContext context, String status) {
    switch (status) {
      case ScheduleStatus.pending:
        return AppLocalizations.of(context)!.statusPending;
      case ScheduleStatus.active:
        return AppLocalizations.of(context)!.statusActive;
      case ScheduleStatus.notGoing:
        return AppLocalizations.of(context)!.statusNotGoing;
      case ScheduleStatus.cancel:
        return AppLocalizations.of(context)!.statusCancelled;
      default:
        return status;
    }
  }
}
