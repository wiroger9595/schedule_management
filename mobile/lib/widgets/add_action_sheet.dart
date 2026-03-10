import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

import '../screens/add_schedule_screen.dart';
import '../screens/ai_chat_screen.dart';

class AddActionSheet {
  static Future<void> show(BuildContext context) async {
    return showModalBottomSheet(
      context: context,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 16),
                child: Container(
                  width: 40,
                  height: 5,
                  decoration: BoxDecoration(
                    color: Colors.grey[300],
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
              ListTile(
                leading: Container(
                  padding: EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.purple[100],
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.smart_toy, color: Colors.purple[700]),
                ),
                title: Text(
                  'AI 助手 (AI Chatbot)',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                subtitle: Text('透過對話快速建立行程'),
                onTap: () async {
                  Navigator.pop(context); // Close the bottom sheet first
                  await Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => AiChatScreen()),
                  );
                },
              ),
              Divider(indent: 72),
              ListTile(
                leading: Container(
                  padding: EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.blue[100],
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.edit_calendar, color: Colors.blue[700]),
                ),
                title: Text(
                  '手動新增 (Manual Add)',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                subtitle: Text('手動填寫行程表單'),
                onTap: () async {
                  Navigator.pop(context); // Close the bottom sheet first
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => AddScheduleScreen(),
                    ),
                  );
                },
              ),
              SizedBox(height: 16),
            ],
          ),
        );
      },
    );
  }
}
