import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
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
  Map<String, dynamic>? _currentContext;
  // Full conversation history sent to AI — keeps track of what was actually said
  final List<Map<String, String>> _conversationHistory = [];

  void clearChat() {
    setState(() {
      _controller.clear();
      _messages.clear();
      _currentContext = null;
      _conversationHistory.clear();
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
          title: Text('addContact'.tr()),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: InputDecoration(labelText: 'nameStar'.tr()),
              ),
              SizedBox(height: 10),
              TextField(
                controller: phoneController,
                decoration: InputDecoration(labelText: 'phone'.tr()),
              ),
              SizedBox(height: 10),
              TextField(
                controller: emailController,
                decoration: InputDecoration(labelText: 'email'.tr()),
              ),
              SizedBox(height: 10),
              TextField(
                controller: lineIdController,
                decoration: InputDecoration(labelText: 'lineOptional'.tr()),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('cancel'.tr()),
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
                  ).showSnackBar(SnackBar(content: Text('addFailed'.tr())));
                }
              },
              child: Text('save'.tr()),
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
        border: Border(top: BorderSide(color: Colors.grey[300]!, width: 2)),
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
              leading: Icon(Icons.person_add, color: Colors.black87),
              title: Text('➕ ${'addContact'.tr()}', style: TextStyle(color: Colors.black87)),
              onTap: _showAddContactDialog,
            );
          }
          final contact = filteredContacts[index];
          final nickName = (contact['nick_name'] ?? '').toString();
          final displayInitial = nickName.isNotEmpty ? nickName[0] : '?';

          return ListTile(
            leading: CircleAvatar(
              child: Text(displayInitial),
              backgroundColor: Colors.grey[300],
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
      // Record user turn in conversation history before sending
      _conversationHistory.add({'role': 'user', 'content': messageText});
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
      double? finalLat = overrideLat;
      double? finalLon = overrideLon;

      // Only get GPS if we don't have an explicit location override (selected place)
      if (overrideLat == null && overrideLon == null && (finalLat == null || finalLon == null)) {
        try {
          bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
          if (serviceEnabled) {
            LocationPermission permission = await Geolocator.checkPermission();
            if (permission == LocationPermission.denied) {
              permission = await Geolocator.requestPermission();
            }
            if (permission != LocationPermission.denied &&
                permission != LocationPermission.deniedForever) {
              final position = await Geolocator.getCurrentPosition(
                locationSettings: const LocationSettings(accuracy: LocationAccuracy.low),
              );
              finalLat = position.latitude;
              finalLon = position.longitude;
            }
          }
        } catch (e) {
          debugPrint('Error getting location for chat: $e');
        }
      }

      final data = await apiService.chatWithAI(
        forceCreate ? 'Confirm' : messageText,
        currentContext: _currentContext,
        conversationHistory: _conversationHistory,
        forceCreate: forceCreate,
        confirmLocation: forceCreate,
        latitude: finalLat,
        longitude: finalLon,
      );

      if (mounted) {
        final aiReply = data['ai_reply'] as String? ?? '';
        // Record AI turn in conversation history
        if (aiReply.isNotEmpty) {
          _conversationHistory.add({'role': 'assistant', 'content': aiReply});
        }

        setState(() {
          _currentContext = data['updated_data'];

          if (data['conflict'] != null) {
            // Conflict Detected
            _messages.add(
              ChatMessage(text: aiReply.isNotEmpty ? aiReply : 'timeConflict'.tr(), isUser: false),
            );
            _messages.add(
              ConflictMessage(
                onConfirm: () => _sendMessage(forceCreate: true),
                onChange: () {
                  setState(() {
                    _messages.add(ChatMessage(text: 'changeTimeRequest'.tr(), isUser: true));
                    // Let AI know
                    _sendMessage(text: 'changeTimeRequest'.tr());
                  });
                },
              ),
            );
          } else if (data['needs_location_confirm'] == true) {
            _messages.add(ChatMessage(text: aiReply, isUser: false));

            final candidates = data['location_candidates'] as List<dynamic>?;

            if (candidates != null && candidates.length > 1) {
              // Multiple candidates — show a selectable list
              _messages.add(
                LocationCandidatesMessage(
                  candidates: candidates.cast<Map<String, dynamic>>(),
                  onSelect: (candidate) {
                    final lat = (candidate['lat'] as num?)?.toDouble();
                    final lon = (candidate['lon'] as num?)?.toDouble();
                    final name = candidate['name'] as String? ?? '';
                    _conversationHistory.add({'role': 'user', 'content': '我選擇地點：$name'});
                    setState(() {
                      _messages.add(ChatMessage(text: '已選擇地點：$name', isUser: true));
                      _currentContext ??= {};
                      _currentContext!['location'] = name;
                      _currentContext!['latitude'] = lat;
                      _currentContext!['longitude'] = lon;
                    });
                    _sendMessage(forceCreate: true, overrideLat: lat, overrideLon: lon);
                  },
                  onPickMap: () => _pickFromMap(data),
                ),
              );
            } else {
              // Single high-confidence match — show card with address + confirm/reject
              final det = data['location_details'] as Map<String, dynamic>?;
              final detName = det?['name'] as String? ?? '';
              final detAddress = det?['address'] as String? ?? '';
              final detLat = (det?['lat'] as num?)?.toDouble();
              final detLon = (det?['lon'] as num?)?.toDouble();
              _messages.add(
                LocationConfirmMessage(
                  name: detName,
                  address: detAddress,
                  lat: detLat,
                  lon: detLon,
                  onConfirm: () {
                    _conversationHistory.add({'role': 'user', 'content': '確認地點：$detName'});
                    _sendMessage(forceCreate: true, overrideLat: detLat, overrideLon: detLon);
                  },
                  onReject: () {
                    // Clear location from context so AI asks again
                    _currentContext ??= {};
                    _currentContext!.remove('location');
                    _sendMessage(text: '找到的地點「$detName」不正確，請問您可以提供更詳細的地址嗎？');
                  },
                  onChange: () => _pickFromMap(data),
                ),
              );
            }
          } else {
            // Normal reply or schedule created
            if (data['schedule'] != null) {
              final scheduleTitle = (data['updated_data']?['title'] as String?) ?? '';
              final successMsg = aiReply.isNotEmpty
                  ? aiReply
                  : '✅ 行程${scheduleTitle.isNotEmpty ? "「$scheduleTitle」" : ""}已建立！';
              _messages.add(ChatMessage(text: successMsg, isUser: false));
            } else if (aiReply.isNotEmpty) {
              _messages.add(ChatMessage(text: aiReply, isUser: false));
            }
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

  Future<void> _pickFromMap(Map<String, dynamic> data) async {
    final det = data['location_details'] ?? (data['location_candidates'] as List?)?.first;
    final navigator = Navigator.of(context); // capture before async gap
    final result = await navigator.push(
      MaterialPageRoute(
        builder: (context) => LocationPickerScreen(
          initialLat: (det?['lat'] as num?)?.toDouble(),
          initialLon: (det?['lon'] as num?)?.toDouble(),
        ),
      ),
    );
    if (result != null && result is Map<String, dynamic> && mounted) {
      final lat = (result['latitude'] as num?)?.toDouble();
      final lon = (result['longitude'] as num?)?.toDouble();
      final address = result['address'] as String? ?? result['name'] as String? ?? '';
      _conversationHistory.add({'role': 'user', 'content': '我手動在地圖選擇地點：$address'});
      setState(() {
        _messages.add(ChatMessage(text: '已手動選擇地點：$address', isUser: true));
        _currentContext ??= {};
        _currentContext!['location'] = address;
        _currentContext!['latitude'] = lat;
        _currentContext!['longitude'] = lon;
      });
      _sendMessage(forceCreate: true, overrideLat: lat, overrideLon: lon);
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
                      : Colors.black,
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

  const ChatMessage({super.key, required this.text, required this.isUser});

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
              backgroundColor: Colors.grey[200],
              child: Icon(Icons.assistant, size: 16, color: Colors.black87),
            ),
            SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isUser ? Colors.black : Colors.grey[200],
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
              backgroundColor: Colors.grey[300],
              child: Icon(Icons.person, size: 16, color: Colors.black87),
            ),
          ],
        ],
      ),
    );
  }
}

class ConflictMessage extends StatefulWidget {
  final VoidCallback onConfirm;
  final VoidCallback onChange;

  const ConflictMessage({super.key, required this.onConfirm, required this.onChange});

  @override
  State<ConflictMessage> createState() => _ConflictMessageState();
}

class _ConflictMessageState extends State<ConflictMessage> {
  bool _tapped = false;

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
                onPressed: _tapped ? null : () {
                  setState(() => _tapped = true);
                  widget.onChange();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.grey[300],
                  foregroundColor: Colors.black,
                ),
                child: Text('changeTime'.tr()),
              ),
              ElevatedButton(
                onPressed: _tapped ? null : () {
                  setState(() => _tapped = true);
                  widget.onConfirm();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                ),
                child: Text('confirmBooking'.tr()),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Shows a selectable list of location candidates returned by the validation tool.
Future<void> _openInGoogleMaps(double? lat, double? lon, String? name) async {
  if (lat == null || lon == null) return;
  final query = Uri.encodeComponent(name ?? '$lat,$lon');
  final uri = Uri.parse('https://www.google.com/maps/search/?api=1&query=$query&center=$lat,$lon');
  if (await canLaunchUrl(uri)) {
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }
}

class LocationCandidatesMessage extends StatelessWidget {
  final List<Map<String, dynamic>> candidates;
  final void Function(Map<String, dynamic>) onSelect;
  final VoidCallback onPickMap;

  const LocationCandidatesMessage({
    super.key,
    required this.candidates,
    required this.onSelect,
    required this.onPickMap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ...candidates.map((c) {
            final lat = (c['lat'] as num?)?.toDouble();
            final lon = (c['lon'] as num?)?.toDouble();
            final name = c['name'] as String? ?? '';
            return Card(
              margin: const EdgeInsets.only(bottom: 6),
              child: ListTile(
                leading: const Icon(Icons.location_on, color: Colors.black54),
                title: Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(c['address'] ?? '', maxLines: 2, overflow: TextOverflow.ellipsis),
                trailing: IconButton(
                  icon: const Icon(Icons.open_in_new, size: 18, color: Colors.blue),
                  tooltip: 'Google Maps で確認',
                  onPressed: () => _openInGoogleMaps(lat, lon, name),
                ),
                onTap: () => onSelect(c),
              ),
            );
          }),
          TextButton.icon(
            onPressed: onPickMap,
            icon: const Icon(Icons.map, size: 16),
            label: Text('changeLocation'.tr()),
            style: TextButton.styleFrom(foregroundColor: Colors.black54),
          ),
        ],
      ),
    );
  }
}

class LocationConfirmMessage extends StatefulWidget {
  final VoidCallback onConfirm;
  final VoidCallback onChange;
  final VoidCallback? onReject;
  final String? name;
  final String? address;
  final double? lat;
  final double? lon;

  const LocationConfirmMessage({
    super.key,
    required this.onConfirm,
    required this.onChange,
    this.onReject,
    this.name,
    this.address,
    this.lat,
    this.lon,
  });

  @override
  State<LocationConfirmMessage> createState() => _LocationConfirmMessageState();
}

class _LocationConfirmMessageState extends State<LocationConfirmMessage> {
  bool _tapped = false;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (widget.name != null || widget.address != null)
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                leading: const Icon(Icons.location_on, color: Colors.black54),
                title: Text(widget.name ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: widget.address != null && widget.address!.isNotEmpty
                    ? Text(widget.address!, maxLines: 2, overflow: TextOverflow.ellipsis)
                    : null,
                trailing: widget.lat != null && widget.lon != null
                    ? IconButton(
                        icon: const Icon(Icons.open_in_new, size: 18, color: Colors.blue),
                        tooltip: '在 Google Maps 確認',
                        onPressed: () => _openInGoogleMaps(widget.lat, widget.lon, widget.name),
                      )
                    : null,
              ),
            ),
          Row(
            children: [
              if (widget.onReject != null)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: OutlinedButton(
                      onPressed: _tapped ? null : () {
                        setState(() => _tapped = true);
                        widget.onReject!();
                      },
                      style: OutlinedButton.styleFrom(foregroundColor: Colors.red[700]),
                      child: const Text('不是這裡'),
                    ),
                  ),
                ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(left: 4),
                  child: ElevatedButton(
                    onPressed: _tapped ? null : () {
                      setState(() => _tapped = true);
                      widget.onConfirm();
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.black,
                      foregroundColor: Colors.white,
                    ),
                    child: Text('confirmLocation'.tr()),
                  ),
                ),
              ),
            ],
          ),
          TextButton.icon(
            onPressed: _tapped ? null : widget.onChange,
            icon: const Icon(Icons.map, size: 16),
            label: Text('changeLocation'.tr()),
            style: TextButton.styleFrom(foregroundColor: Colors.black54),
          ),
        ],
      ),
    );
  }
}
