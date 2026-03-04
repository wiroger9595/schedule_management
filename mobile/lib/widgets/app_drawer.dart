import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/profile_screen.dart';
import '../screens/call_log_screen.dart';
import '../screens/contact_list_screen.dart';
import '../screens/home_screen.dart';
import '../screens/tabbed_dashboard_screen.dart';
import 'user_avatar.dart';

/// Reusable app drawer widget extracted from HomeScreen.
/// Displays user profile header and navigation menu items.
class AppDrawer extends StatelessWidget {
  final VoidCallback onLogout;

  const AppDrawer({Key? key, required this.onLogout}) : super(key: key);

  @override
  Widget build(BuildContext context) {
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
            leading: Icon(Icons.person, color: Colors.blue),
            title: Text('profile'.tr()),
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
            leading: Icon(Icons.people, color: Colors.purple),
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
            leading: Icon(Icons.list_alt, color: Colors.blue),
            title: Text('mySchedules'.tr()),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => HomeScreen()),
              );
            },
          ),
          Divider(),
          ListTile(
            leading: Icon(Icons.logout, color: Colors.red),
            title: Text('logout'.tr()),
            onTap: onLogout,
          ),
        ],
      ),
    );
  }
}
