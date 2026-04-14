import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/profile_screen.dart';
import '../screens/call_log_screen.dart';
import '../screens/contact_list_screen.dart';
import '../screens/home_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/tabbed_dashboard_screen.dart';
import '../screens/invitations_screen.dart';
import '../services/api_service.dart';
import 'user_avatar.dart';

/// Reusable app drawer widget extracted from HomeScreen.
/// Displays user profile header and navigation menu items.
class AppDrawer extends StatefulWidget {
  final VoidCallback onLogout;

  const AppDrawer({Key? key, required this.onLogout}) : super(key: key);

  @override
  State<AppDrawer> createState() => _AppDrawerState();
}

class _AppDrawerState extends State<AppDrawer> {
  int _inviteCount = 0;

  @override
  void initState() {
    super.initState();
    _loadInviteCount();
  }

  Future<void> _loadInviteCount() async {
    try {
      final invites = await ApiService().getMyInvitations();
      if (mounted) setState(() => _inviteCount = invites.length);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Colors.black, Colors.grey[800]!],
              ),
            ),
            child: Consumer<AuthProvider>(
              builder: (context, auth, _) {
                final user = auth.user;
                final displayUser = user ?? {
                  'full_name': 'user'.tr(),
                  'user_id': '',
                  'profile_image_path': null,
                };

                return Row(
                  children: [
                    GestureDetector(
                      onTap: () async {
                        final result = await Navigator.pushNamed(
                          context,
                          '/profile',
                        );
                        if (result == true) {
                          auth.fetchUserProfile();
                        }
                      },
                      child: UserAvatar(
                        radius: 35,
                        imageUrl: displayUser['profile_image_path'],
                      ),
                    ),
                    SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            displayUser['full_name'] ??
                                'user'.tr(),
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
                            displayUser['user_id'] ?? '',
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
              },
            ),
          ),
          ListTile(
            leading: Icon(Icons.smart_toy_outlined, color: Colors.blueAccent),
            title: Text('aiChat'.tr()),
            onTap: () {
              Navigator.pop(context);
              Navigator.pushNamed(context, '/home');
            },
          ),
          ListTile(
            leading: Icon(Icons.list_alt, color: Colors.black87),
            title: Text('mySchedules'.tr()),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => HomeScreen()),
              );
            },
          ),
          ListTile(
            leading: Icon(Icons.calendar_month, color: Colors.orange),
            title: Text('calendar'.tr()),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => TabbedDashboardScreen(initialTabIndex: 0)),
              );
            },
          ),
          ListTile(
            leading: Icon(Icons.checklist, color: Colors.teal),
            title: Text('todoList'.tr()),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => TabbedDashboardScreen(initialTabIndex: 1)),
              );
            },
          ),
          ListTile(
            leading: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(Icons.mail_outline, color: Colors.deepPurple),
                if (_inviteCount > 0)
                  Positioned(
                    right: -6,
                    top: -4,
                    child: Container(
                      padding: const EdgeInsets.all(3),
                      decoration: const BoxDecoration(
                        color: Colors.red,
                        shape: BoxShape.circle,
                      ),
                      child: Text(
                        '$_inviteCount',
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
              ],
            ),
            title: Row(
              children: [
                Text('invitations'.tr()),
                if (_inviteCount > 0) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                        color: Colors.red,
                        borderRadius: BorderRadius.circular(10)),
                    child: Text('$_inviteCount',
                        style: const TextStyle(
                            color: Colors.white, fontSize: 11)),
                  ),
                ],
              ],
            ),
            onTap: () async {
              Navigator.pop(context);
              await Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (context) => const InvitationsScreen()),
              );
              _loadInviteCount(); // Refresh badge after returning
            },
          ),
          ListTile(
            leading: Icon(Icons.people, color: Colors.black87),
            title: Text('myContacts'.tr()),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => ContactListScreen()),
              );
            },
          ),
          ListTile(
            leading: Icon(Icons.person, color: Colors.black87),
            title: Text('profile'.tr()),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => ProfileScreen()),
              );
            },
          ),
          if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android)
            ListTile(
              leading: Icon(Icons.phone, color: Colors.green),
              title: Text('callLog'.tr()),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => CallLogScreen()),
                );
              },
            ),
          ListTile(
            leading: Icon(Icons.settings, color: Colors.black87),
            title: Text('settings'.tr()),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsScreen()),
              );
            },
          ),
          Divider(),
          ListTile(
            leading: Icon(Icons.logout, color: Colors.red),
            title: Text('logout'.tr()),
            onTap: widget.onLogout,
          ),
        ],
      ),
    );
  }
}
