import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/schedule_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/chat_widget.dart';
import 'main_shell.dart';

class AiChatScreen extends StatefulWidget {
  @override
  AiChatScreenState createState() => AiChatScreenState();
}

class AiChatScreenState extends State<AiChatScreen> {
  final GlobalKey<ChatWidgetState> _chatWidgetKey = GlobalKey<ChatWidgetState>();

  void clearChat() => _chatWidgetKey.currentState?.clearChat();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF0F4FF),
      appBar: _ConciergeAppBar(onClear: clearChat),
      body: Column(
        children: [
          Expanded(
            child: ChatWidget(
              key: _chatWidgetKey,
              onScheduleCreated: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('scheduleCreatedSuccess'.tr())),
                );
                Provider.of<ScheduleProvider>(context, listen: false).fetchSchedules();
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _ConciergeAppBar extends StatelessWidget implements PreferredSizeWidget {
  final VoidCallback onClear;
  const _ConciergeAppBar({required this.onClear});

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.surface,
      padding: EdgeInsets.only(top: MediaQuery.of(context).padding.top),
      child: SizedBox(
        height: 64,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              // Menu icon (hamburger style) — opens MainShell drawer
              GestureDetector(
                onTap: () => MainShellState.scaffoldKey.currentState?.openDrawer(),
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.menu_rounded, color: AppTheme.textSecond, size: 22),
                ),
              ),

              const Spacer(),

              // Title (center)
              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'aiChat'.tr(),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  Text(
                    'aiChatHint'.tr(),
                    style: const TextStyle(fontSize: 10, color: AppTheme.textMuted),
                  ),
                ],
              ),

              const Spacer(),

              // Clear chat button
              GestureDetector(
                onTap: onClear,
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.delete_sweep_rounded, color: AppTheme.textSecond, size: 22),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
