import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/profile_screen.dart';
import '../screens/call_log_screen.dart';
import '../screens/calendar_screen.dart';
import '../screens/contact_list_screen.dart';
import '../i18n/app_localizations.dart';
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
                if (user != null) {
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
                          imageUrl: user['profile_image_path'],
                        ),
                      ),
                      SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              user['full_name'] ??
                                  AppLocalizations.of(context)!.user,
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
                              user['user_id'] ?? '',
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
                return Center(
                  child: CircularProgressIndicator(color: Colors.white),
                );
              },
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
            onTap: onLogout,
          ),
        ],
      ),
    );
  }
}
