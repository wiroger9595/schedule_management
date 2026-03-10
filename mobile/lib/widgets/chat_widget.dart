import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/location_picker_screen.dart';

class ChatWidget extends StatefulWidget {
  final Function() onScheduleCreated;

  const ChatWidget({Key? key, required this.onScheduleCreated}) : super(key: key);

  @override
  ChatWidgetState createState() => ChatWidgetState();
}

class ChatWidgetState extends State<ChatWidget> {
  final TextEditingController _controller = TextEditingController();
  final List<Widget> _messages =
      []; // Changed to Widget to support different message types
  bool _isLoading = false;
  final ScrollController _scrollController = ScrollController();
  Map<String, dynamic>? _currentContext; // Persist context

  void clearChat() {
    setState(() {
      _controller.clear();
      _messages.clear();
      _currentContext = null;
      _showMentionList = false;
      _isLoading = false;
      _messages.add(ChatMessage(text: "對話與記憶已清空，請重新輸入您的行程資訊。", isUser: false));
    });
  }

  List<dynamic> _contacts = [];
  bool _showMentionList = false;
  String _mentionQuery = '';
  int _mentionStartIndex = -1;

  @override
  void initState() {
    super.initState();
    _loadContacts();
  }

  Future<void> _loadContacts() async {
    try {
      final apiService = ApiService();
      final contacts = await apiService.getContacts();
      print("Loaded contacts for mention: $contacts");
      if (mounted) {
        setState(() {
          _contacts = contacts;
        });
      }
    } catch (e) {
      print("Failed to load contacts for mention: $e");
      if (mounted) {
        if (e.toString().contains('Unauthorized')) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('登入憑證已過期，請重新登入')));
          Provider.of<AuthProvider>(context, listen: false).logout();
        } else {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('讀取聯絡人失敗: $e')));
        }
      }
    }
  }

  void _onTextChanged(String text) {
    final cursorPosition = _controller.selection.baseOffset;
    if (cursorPosition >= 0) {
      final textBeforeCursor = text.substring(0, cursorPosition);
      // Find the last occurrence of '@' or '＠' before the cursor
      int lastAtPos = textBeforeCursor.lastIndexOf('@');
      final lastFullPos = textBeforeCursor.lastIndexOf('＠'); // Full-width
      if (lastFullPos > lastAtPos) {
        lastAtPos = lastFullPos;
      }

      if (lastAtPos >= 0) {
        // A mention is valid if it's on the same line.
        final textAfterAt = textBeforeCursor.substring(lastAtPos + 1);
        if (!textAfterAt.contains('\n')) {
          setState(() {
            _showMentionList = true;
            _mentionQuery = textAfterAt; // Keep exact case, lowercase it during search
            _mentionStartIndex = lastAtPos;
          });
          return;
        }
      }

      setState(() {
        _showMentionList = false;
      });
    } else {
      setState(() {
        _showMentionList = false;
      });
    }
  }

  void _insertMention(String name) {
    if (_mentionStartIndex >= 0) {
      final text = _controller.text;
      final cursorPosition = _controller.selection.baseOffset;

      final newText =
          text.substring(0, _mentionStartIndex) +
          '@$name ' +
          text.substring(cursorPosition);

      _controller.value = TextEditingValue(
        text: newText,
        selection: TextSelection.collapsed(
          offset: _mentionStartIndex + name.length + 2,
        ),
      );
    }
    setState(() {
      _showMentionList = false;
    });
  }

  void _showAddContactDialog() {
    final nameController = TextEditingController(text: _mentionQuery);
    final phoneController = TextEditingController();
    final emailController = TextEditingController();
    final lineIdController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text('新增聯絡人'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: InputDecoration(labelText: '姓名*'),
              ),
              SizedBox(height: 10),
              TextField(
                controller: phoneController,
                decoration: InputDecoration(labelText: '電話'),
              ),
              SizedBox(height: 10),
              TextField(
                controller: emailController,
                decoration: InputDecoration(labelText: 'Email'),
              ),
              SizedBox(height: 10),
              TextField(
                controller: lineIdController,
                decoration: InputDecoration(labelText: 'Line ID (選填)'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('取消'),
            ),
            ElevatedButton(
              onPressed: () async {
                if (nameController.text.trim().isEmpty) return;
                try {
                  final apiService = ApiService();
                  await apiService.createContact(
                    nameController.text.trim(),
                    phoneController.text.trim(),
                    emailController.text.trim(),
                    lineIdController.text.trim(),
                  );
                  Navigator.pop(context); // Close dialog
                  await _loadContacts(); // Refresh
                  _insertMention(
                    nameController.text.trim(),
                  ); // Insert into text
                } catch (e) {
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(SnackBar(content: Text('新增失敗: $e')));
                }
              },
              child: Text('儲存'),
            ),
          ],
        );
      },
    );
  }

  Widget _buildMentionList() {
    final query = _mentionQuery.trim().toLowerCase();
    final filteredContacts = _contacts.where((c) {
      final name = (c['nick_name'] ?? c['name'] ?? '').toString().toLowerCase();
      return name.contains(query);
    }).toList();

    return Container(
      constraints: BoxConstraints(maxHeight: 180),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.purple[100]!, width: 2)),
        boxShadow: [
          BoxShadow(
            color: Colors.black12,
            blurRadius: 4,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: ListView.builder(
        shrinkWrap: true,
        itemCount: filteredContacts.length + 1,
        itemBuilder: (context, index) {
          if (index == filteredContacts.length) {
            return ListTile(
              leading: Icon(Icons.person_add, color: Colors.blue),
              title: Text('➕ 新增聯絡人', style: TextStyle(color: Colors.blue)),
              onTap: _showAddContactDialog,
            );
          }
          final contact = filteredContacts[index];
          final nickName = (contact['nick_name'] ?? '').toString();
          final displayInitial = nickName.isNotEmpty ? nickName[0] : '?';

          return ListTile(
            leading: CircleAvatar(
              child: Text(displayInitial),
              backgroundColor: Colors.purple[100],
            ),
            title: Text(contact['nick_name'] ?? 'Unknown'),
            subtitle: Text(contact['phone'] ?? contact['email'] ?? ''),
            onTap: () => _insertMention(contact['nick_name']),
          );
        },
      ),
    );
  }

  Future<void> _sendMessage({String? text, bool forceCreate = false, double? overrideLat, double? overrideLon}) async {
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

      // Get current location (best effort) or use overridden ones
      Position? position;
      double? finalLat = overrideLat;
      double? finalLon = overrideLon;
      
      if (finalLat == null || finalLon == null) {
        try {
          bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
          if (serviceEnabled) {
            LocationPermission permission = await Geolocator.checkPermission();
            if (permission == LocationPermission.denied) {
              permission = await Geolocator.requestPermission();
            }
            if (permission != LocationPermission.denied &&
                permission != LocationPermission.deniedForever) {
              position = await Geolocator.getCurrentPosition(
                timeLimit: Duration(seconds: 5),
              );
              finalLat = position?.latitude;
              finalLon = position?.longitude;
            }
          }
        } catch (e) {
          print("Error getting location for chat: $e");
        }
      }

      final data = await apiService.chatWithAI(
        forceCreate ? "Confirm" : messageText,
        currentContext: _currentContext,
        forceCreate: forceCreate,
        confirmLocation: forceCreate,
        latitude: finalLat,
        longitude: finalLon,
      );

      if (mounted) {
        setState(() {
          _currentContext = data['updated_data']; // Update context

          if (data['conflict'] != null) {
            // Conflict Detected
            _messages.add(
              ChatMessage(text: data['ai_reply'] ?? '時間衝突', isUser: false),
            );
            _messages.add(
              ConflictMessage(
                onConfirm: () => _sendMessage(forceCreate: true),
                onChange: () {
                  setState(() {
                    _messages.add(ChatMessage(text: "我要更改時間", isUser: true));
                    // Let AI know
                    _sendMessage(text: "我要更改時間");
                  });
                },
              ),
            );
          } else if (data['needs_location_confirm'] == true) {
            // Location confirmation required
            _messages.add(
              ChatMessage(text: data['ai_reply'] ?? '請確認地點是否正確：', isUser: false),
            );
            _messages.add(
              LocationConfirmMessage(
                onConfirm: () => _sendMessage(forceCreate: true),
                onChange: () async {
                  final result = await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) =>
                          LocationPickerScreen(
                            initialLat: data['location_details']?['lat'],
                            initialLon: data['location_details']?['lon'],
                          ),
                    ),
                  );

                  if (result != null && result is Map<String, dynamic>) {
                    final lat = result['latitude'];
                    final lon = result['longitude'];
                    final address = result['address'];

                    setState(() {
                      _messages.add(ChatMessage(text: "已手動選擇地點：$address", isUser: true));
                    });

                    // Update the context with the new address so backend uses it
                    _currentContext ??= {};
                    _currentContext!['location'] = address;
                    _currentContext!['latitude'] = lat;
                    _currentContext!['longitude'] = lon;

                    // Immediately dispatch the save request with the fixed location
                    final newPosData = {
                      'latitude': lat,
                      'longitude': lon,
                    };
                    
                    _sendMessage(
                      forceCreate: true,
                      overrideLat: newPosData['latitude'],
                      overrideLon: newPosData['longitude'],
                    );
                  }
                },
              ),
            );
          } else {
            // Normal reply
            _messages.add(
              ChatMessage(text: data['ai_reply'] ?? '', isUser: false),
            );
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
      color: Colors.transparent, // Let the parent control the background
      child: Column(
        children: [
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
                          'aiChatHint'.tr(),
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
                    'loading'.tr(),
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                ],
              ),
            ),

          // Mention List Overlay
          if (_showMentionList) _buildMentionList(),

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
                      hintText: 'aiChatHint'.tr(),
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
                    onChanged: _onTextChanged,
                    onSubmitted: (_) => _sendMessage(),
                    enabled: !_isLoading,
                  ),
                ),
                SizedBox(width: 8),
                IconButton(
                  icon: Icon(Icons.refresh),
                  onPressed: () async {
                    await _loadContacts();
                    if (_contacts.isNotEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('成功載入 ${_contacts.length} 位聯絡人！'),
                        ),
                      );
                    }
                  },
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

class LocationConfirmMessage extends StatelessWidget {
  final VoidCallback onConfirm;
  final VoidCallback onChange;

  LocationConfirmMessage({required this.onConfirm, required this.onChange});

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
                child: Text("更改地點"),
              ),
              ElevatedButton(
                onPressed: onConfirm,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.purple[700],
                  foregroundColor: Colors.white,
                ),
                child: Text("確認地點"),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
