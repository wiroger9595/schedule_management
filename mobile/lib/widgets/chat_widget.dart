import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'dart:convert';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../i18n/app_localizations.dart';

import 'package:geolocator/geolocator.dart';

class ChatWidget extends StatefulWidget {
  final Function() onScheduleCreated;

  ChatWidget({required this.onScheduleCreated});

  @override
  _ChatWidgetState createState() => _ChatWidgetState();
}

class _ChatWidgetState extends State<ChatWidget> {
  final TextEditingController _controller = TextEditingController();
  final List<Widget> _messages = []; // Changed to Widget to support different message types
  bool _isLoading = false;
  final ScrollController _scrollController = ScrollController();
  Map<String, dynamic>? _currentContext; // Persist context

  Future<void> _sendMessage({String? text, bool forceCreate = false}) async {
    final messageText = text ?? _controller.text.trim();
    if (messageText.isEmpty && !forceCreate) return;

    if (!forceCreate) {
      setState(() {
        _messages.add(ChatMessage(text: messageText, isUser: true));
        _isLoading = true;
      });
      _controller.clear();
      _scrollToBottom();
    } else {
       setState(() {
        _isLoading = true;
      });
    }

    try {
      final apiService = ApiService();
      
      // Get current location (best effort)
      Position? position;
      try {
        bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
        if (serviceEnabled) {
           LocationPermission permission = await Geolocator.checkPermission();
           if (permission == LocationPermission.denied) {
             permission = await Geolocator.requestPermission();
           }
           if (permission != LocationPermission.denied && permission != LocationPermission.deniedForever) {
             position = await Geolocator.getCurrentPosition(timeLimit: Duration(seconds: 5));
           }
        }
      } catch (e) {
        print("Error getting location for chat: $e");
      }

      final data = await apiService.chatWithAI(
        forceCreate ? "Confirm" : messageText, 
        currentContext: _currentContext, 
        forceCreate: forceCreate,
        latitude: position?.latitude,
        longitude: position?.longitude
      );

      if (mounted) {
        setState(() {
          _currentContext = data['updated_data']; // Update context
          
          if (data['conflict'] != null) {
            // Conflict Detected
            _messages.add(ChatMessage(text: data['ai_reply'] ?? '時間衝突', isUser: false));
            _messages.add(ConflictMessage(
              onConfirm: () => _sendMessage(forceCreate: true),
              onChange: () {
                setState(() {
                  _messages.add(ChatMessage(text: "我要更改時間", isUser: true));
                  // Let AI know
                  _sendMessage(text: "我要更改時間"); 
                });
              },
            ));
          } else {
            // Normal reply
            _messages.add(ChatMessage(text: data['ai_reply'] ?? '', isUser: false));
          }
          
          _isLoading = false;
        });

        if (data['is_complete'] == true && data['conflict'] == null) {
             widget.onScheduleCreated();
        }
        
       _scrollToBottom();
      }
    } catch (e) {
      setState(() {
        _messages.add(ChatMessage(text: '抱歉，發生錯誤：$e', isUser: false));
        _isLoading = false;
      });
    }
  }

  void _scrollToBottom() {
    Future.delayed(Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.7,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [
          BoxShadow(
            color: Colors.black26,
            blurRadius: 10,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: Column(
        children: [
          // 標題欄
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.purple[700],
              borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
            ),
            child: Row(
              children: [
                Icon(Icons.assistant, color: Colors.white),
                SizedBox(width: 8),
                Text(
                  AppLocalizations.of(context)!.aiChat,
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                Spacer(),
                IconButton(
                  icon: Icon(Icons.close, color: Colors.white),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
          ),

          // 訊息列表
          Expanded(
            child: _messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.chat_bubble_outline,
                          size: 64,
                          color: Colors.grey[300],
                        ),
                        SizedBox(height: 16),
                        Text(
                          AppLocalizations.of(context)!.aiChatHint,
                          style: TextStyle(color: Colors.grey[600]),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      return _messages[index];
                    },
                  ),
          ),

          // 載入動畫
          if (_isLoading)
            Padding(
              padding: EdgeInsets.all(8),
              child: Row(
                children: [
                  SizedBox(width: 16),
                  SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  SizedBox(width: 8),
                  Text(
                    AppLocalizations.of(context)!.loading,
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                ],
              ),
            ),

          // 輸入框
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              border: Border(top: BorderSide(color: Colors.grey[300]!)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(
                      hintText: AppLocalizations.of(context)!.aiChatHint,
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(25),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 20,
                        vertical: 12,
                      ),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                    enabled: !_isLoading,
                  ),
                ),
                SizedBox(width: 8),
                FloatingActionButton(
                  mini: true,
                  onPressed: _isLoading ? null : () => _sendMessage(),
                  child: Icon(Icons.send, size: 20),
                  backgroundColor: _isLoading
                      ? Colors.grey
                      : Colors.purple[700],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class ChatMessage extends StatelessWidget {
  final String text;
  final bool isUser;

  ChatMessage({required this.text, required this.isUser});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: isUser
            ? MainAxisAlignment.end
            : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: Colors.purple[100],
              child: Icon(Icons.assistant, size: 16, color: Colors.purple[700]),
            ),
            SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isUser ? Colors.purple[700] : Colors.grey[200],
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                text,
                style: TextStyle(
                  color: isUser ? Colors.white : Colors.black87,
                  fontSize: 15,
                ),
              ),
            ),
          ),
          if (isUser) ...[
            SizedBox(width: 8),
            CircleAvatar(
              radius: 16,
              backgroundColor: Colors.blue[100],
              child: Icon(Icons.person, size: 16, color: Colors.blue[700]),
            ),
          ],
        ],
      ),
    );
  }
}

class ConflictMessage extends StatelessWidget {
  final VoidCallback onConfirm;
  final VoidCallback onChange;

  ConflictMessage({required this.onConfirm, required this.onChange});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 40.0),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              ElevatedButton(
                onPressed: onChange,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.grey[300],
                  foregroundColor: Colors.black,
                ),
                child: Text("更改時間"),
              ),
              ElevatedButton(
                onPressed: onConfirm,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                ),
                child: Text("確定預約"),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
