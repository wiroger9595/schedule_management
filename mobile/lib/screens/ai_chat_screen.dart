import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../i18n/app_localizations.dart';
import '../widgets/app_drawer.dart';
import '../widgets/chat_widget.dart';

class AiChatScreen extends StatefulWidget {
  @override
  _AiChatScreenState createState() => _AiChatScreenState();
}

class _AiChatScreenState extends State<AiChatScreen> {
  final ApiService _apiService = ApiService();
  final GlobalKey<ChatWidgetState> _chatWidgetKey = GlobalKey<ChatWidgetState>();

  Future<void> _handleLogout() async {
    await Provider.of<AuthProvider>(context, listen: false).logout();
    if (!mounted) return;
    Navigator.of(context).pushNamedAndRemoveUntil('/login', (route) => false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)!.aiChat),
        flexibleSpace: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [Colors.purple[700]!, Colors.blue[700]!],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.delete_outline, color: Colors.white),
            onPressed: () {
              _chatWidgetKey.currentState?.clearChat();
            },
            tooltip: '清空對話',
          ),
        ],
      ),
      drawer: AppDrawer(onLogout: _handleLogout),
      // We wrap ChatWidget in a container that fills the screen. 
      // The original ChatWidget has a hardcoded height of 0.7 screen. We'll need to remove or override it.
      // Since ChatWidget internally defines its Container height, let's use it directly but 
      // maybe it'll look better if we pass a parameter or just let it expand.
      body: SafeArea(
        child: Container(
          color: Colors.grey[100],
          // Wrap in a Column/Expanded to handle internal constrained heights naturally
          child: Column(
            children: [
              Expanded(
                child: ChatWidget(
                  key: _chatWidgetKey,
                  onScheduleCreated: () {
                    // When a schedule is created, we can show a snackbar or navigate to My Schedules
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('行程已成功建立！(Schedule Created!)')),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
