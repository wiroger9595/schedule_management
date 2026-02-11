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
import 'contact_list_screen.dart';
import "../l10n/app_localizations.dart";
import '../utils/constants.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final NotificationService notificationService = NotificationService();

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)!.mySchedules),
        actions: [
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

          if (provider.schedules.isEmpty) {
            return Center(child: Text(AppLocalizations.of(context)!.noSchedules));
          }

          return ListView.builder(
            itemCount: provider.schedules.length,
            itemBuilder: (context, index) {
              final schedule = provider.schedules[index];
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
