import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/call_log_screen.dart';
import '../screens/contact_list_screen.dart';
import '../screens/invitations_screen.dart';
import '../screens/main_shell.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'user_avatar.dart';

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

  void _switchTab(int index) {
    Navigator.pop(context);
    MainShellState.current?.switchTo(index);
  }

  void _go(Widget screen) {
    Navigator.pop(context);
    Navigator.push(context, MaterialPageRoute(builder: (_) => screen));
  }

  @override
  Widget build(BuildContext context) {
    return Drawer(
      backgroundColor: AppTheme.surface,
      child: Column(
        children: [
          // ── Header ────────────────────────────────────────
          Consumer<AuthProvider>(
            builder: (ctx, auth, _) {
              final user = auth.user ?? {};
              final name = (user['full_name'] as String?)?.isNotEmpty == true
                  ? user['full_name'] as String
                  : 'user'.tr();
              final email = (user['email'] as String?) ?? '';
              final imageUrl = user['profile_image_path'] as String?;

              return Container(
                color: AppTheme.primary,
                padding: EdgeInsets.only(
                  top: MediaQuery.of(context).padding.top + 20,
                  left: 20,
                  right: 20,
                  bottom: 24,
                ),
                child: Row(
                  children: [
                    GestureDetector(
                      onTap: () async {
                        final ok = await Navigator.pushNamed(ctx, '/profile');
                        if (ok == true) auth.fetchUserProfile();
                      },
                      child: UserAvatar(radius: 28, imageUrl: imageUrl),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            name,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.2,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (email.isNotEmpty) ...[
                            const SizedBox(height: 2),
                            Text(
                              email,
                              style: const TextStyle(
                                color: Colors.white54,
                                fontSize: 12,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          ),

          // ── Nav items ────────────────────────────────────
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 8),
              children: [
                _NavItem(
                  icon: Icons.smart_toy_outlined,
                  label: 'aiChat'.tr(),
                  color: AppTheme.primary,
                  onTap: () => _switchTab(3),
                ),
                _NavItem(
                  icon: Icons.list_alt_rounded,
                  label: 'mySchedules'.tr(),
                  color: const Color(0xFF0EA5E9),
                  onTap: () => _switchTab(0),
                ),
                _NavItem(
                  icon: Icons.calendar_month_rounded,
                  label: 'calendar'.tr(),
                  color: const Color(0xFFF59E0B),
                  onTap: () => _switchTab(1),
                ),
                _NavItem(
                  icon: Icons.checklist_rounded,
                  label: 'todoList'.tr(),
                  color: const Color(0xFF10B981),
                  onTap: () => _switchTab(1),
                ),
                _NavItem(
                  icon: Icons.mail_outline_rounded,
                  label: 'invitations'.tr(),
                  color: const Color(0xFF8B5CF6),
                  badge: _inviteCount,
                  onTap: () async {
                    Navigator.pop(context);
                    await Navigator.push(context,
                        MaterialPageRoute(builder: (_) => const InvitationsScreen()));
                    _loadInviteCount();
                  },
                ),
                _NavItem(
                  icon: Icons.people_outline_rounded,
                  label: 'myContacts'.tr(),
                  color: const Color(0xFF64748B),
                  onTap: () => _go(ContactListScreen()),
                ),
                _NavItem(
                  icon: Icons.person_outline_rounded,
                  label: 'profile'.tr(),
                  color: const Color(0xFF64748B),
                  onTap: () => _switchTab(4),
                ),
                if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android)
                  _NavItem(
                    icon: Icons.phone_outlined,
                    label: 'callLog'.tr(),
                    color: const Color(0xFF22C55E),
                    onTap: () => _go(CallLogScreen()),
                  ),
                _NavItem(
                  icon: Icons.settings_outlined,
                  label: 'settings'.tr(),
                  color: const Color(0xFF64748B),
                  onTap: () => _switchTab(4),
                ),
              ],
            ),
          ),

          // ── Footer ───────────────────────────────────────
          const Divider(height: 1),
          _NavItem(
            icon: Icons.logout_rounded,
            label: 'logout'.tr(),
            color: AppTheme.statusC,
            onTap: widget.onLogout,
          ),
          SizedBox(height: MediaQuery.of(context).padding.bottom + 8),
        ],
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final int badge;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
    this.badge = 0,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          leading: Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: color.withOpacity(0.10),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          title: Text(
            label,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w500,
              color: AppTheme.textPrimary,
            ),
          ),
          trailing: badge > 0
              ? Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.statusC,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '$badge',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w700),
                  ),
                )
              : null,
          dense: true,
        ),
      ),
    );
  }
}
