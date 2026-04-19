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
  List<Map<String, dynamic>> _scheduleList = [];

  void clearChat() {
    setState(() {
      _controller.clear();
      _messages.clear();
      _currentContext = null;
      _conversationHistory.clear();
      _showMentionList = false;
      _isLoading = false;
      _messages.add(ChatMessage(text: 'chatCleared'.tr(), isUser: false));
    });
    // 同步清除 server-side Redis history
    ApiService().clearChatHistory();
    _loadScheduleList();
  }

  List<dynamic> _contacts = [];
  bool _showMentionList = false;
  String _mentionQuery = '';
  int _mentionStartIndex = -1;

  @override
  void initState() {
    super.initState();
    _loadContacts();
    _loadScheduleList();
  }

  Future<void> _loadScheduleList() async {
    try {
      final apiService = ApiService();
      final schedules = await apiService.getSchedules();
      if (mounted) {
        setState(() {
          _scheduleList = schedules.map((s) => s.toJson()).toList();
        });
      }
    } catch (_) {}
  }

  Future<void> _loadContacts() async {
    try {
      final apiService = ApiService();
      final contacts = await apiService.getContacts();
      debugPrint("Loaded contacts for mention: $contacts");
      if (mounted) {
        setState(() {
          _contacts = contacts;
        });
      }
    } catch (e) {
      debugPrint("Failed to load contacts for mention: $e");
      if (mounted) {
        if (e.toString().contains('Unauthorized')) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('sessionExpiredRelogin'.tr())));
          Provider.of<AuthProvider>(context, listen: false).logout();
        } else {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('loadContactsFailed'.tr(namedArgs: {'error': e.toString()}))));
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

    // Detect duplicate nick_names in filtered results
    final nameCount = <String, int>{};
    for (final c in filteredContacts) {
      final n = (c['nick_name'] ?? '').toString();
      nameCount[n] = (nameCount[n] ?? 0) + 1;
    }
    final hasDuplicates = nameCount.values.any((v) => v > 1);
    final duplicateNames = nameCount.entries.where((e) => e.value > 1).map((e) => e.key).toSet();

    return Container(
      constraints: BoxConstraints(maxHeight: 220),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey[300]!, width: 2)),
        boxShadow: [
          BoxShadow(color: Colors.black12, blurRadius: 4, offset: Offset(0, -2)),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (hasDuplicates)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              color: Colors.orange[50],
              child: Row(
                children: [
                  Icon(Icons.info_outline, size: 15, color: Colors.orange[700]),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'duplicateContactHint'.tr(namedArgs: {'names': duplicateNames.join('、')}),
                      style: TextStyle(fontSize: 12, color: Colors.orange[800]),
                    ),
                  ),
                ],
              ),
            ),
          Flexible(
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
                final isDup = duplicateNames.contains(nickName);
                final displayInitial = nickName.isNotEmpty ? nickName[0] : '?';
                // For duplicates show phone+email to distinguish; always show at least one
                String subtitle = contact['phone'] ?? contact['email'] ?? '';
                if (isDup) {
                  final parts = [
                    if ((contact['phone'] ?? '').toString().isNotEmpty) contact['phone'].toString(),
                    if ((contact['email'] ?? '').toString().isNotEmpty) contact['email'].toString(),
                  ];
                  subtitle = parts.isNotEmpty ? parts.join(' · ') : 'noContactInfo'.tr();
                }

                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: isDup ? Colors.orange[200] : Colors.grey[300],
                    child: Text(displayInitial),
                  ),
                  title: Text(nickName),
                  subtitle: subtitle.isNotEmpty ? Text(subtitle, style: const TextStyle(fontSize: 12)) : null,
                  onTap: () => _insertMention(nickName),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _sendMessage({String? text, bool forceCreate = false, bool confirmDelete = false, bool confirmPastEdit = false, double? overrideLat, double? overrideLon}) async {
    final messageText = text ?? _controller.text.trim();
    if (messageText.isEmpty && !forceCreate && !confirmPastEdit && !confirmDelete) return;

    if (!forceCreate && !confirmPastEdit && !confirmDelete) {
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
        (forceCreate || confirmPastEdit || confirmDelete) ? 'Confirm' : messageText,
        currentContext: _currentContext,
        conversationHistory: _conversationHistory,
        forceCreate: forceCreate,
        confirmLocation: forceCreate,
        confirmDelete: confirmDelete,
        confirmPastEdit: confirmPastEdit,
        latitude: finalLat,
        longitude: finalLon,
        scheduleList: _scheduleList,
      );

      if (mounted) {
        final aiReply = data['ai_reply'] as String? ?? '';
        // Record AI turn in conversation history
        if (aiReply.isNotEmpty) {
          _conversationHistory.add({'role': 'assistant', 'content': aiReply});
        }

        setState(() {
          final isComplete = data['is_complete'] == true;
          final updatedData = data['updated_data'];
          // Clear context on completion (backend returns {} on create/delete success)
          if (isComplete && (updatedData == null || (updatedData as Map).isEmpty)) {
            _currentContext = null;
            _conversationHistory.clear(); // history stored in Redis; clear local copy
          } else if (updatedData != null) {
            _currentContext = Map<String, dynamic>.from(updatedData as Map);
          }
          // Keep schedule_id in context after edit so follow-up messages trigger update
          if (data['schedule'] != null && data['schedule']['id'] != null && !isComplete) {
            _currentContext ??= {};
            _currentContext!['schedule_id'] = data['schedule']['id'];
          }

          if (data['schedule_deleted'] == true) {
            // Schedule deleted successfully — refresh list
            if (aiReply.isNotEmpty) _messages.add(ChatMessage(text: aiReply, isUser: false));
            _currentContext = null;
            widget.onScheduleCreated();
            _loadScheduleList();
          } else if (data['confirm_delete'] != null) {
            // Backend wants user to confirm deletion
            final del = data['confirm_delete'] as Map<String, dynamic>;
            if (aiReply.isNotEmpty) _messages.add(ChatMessage(text: aiReply, isUser: false));
            _messages.add(
              DeleteConfirmMessage(
                title: del['title'] as String? ?? '',
                startTime: del['start_time'] as String?,
                onConfirm: () {
                  _currentContext ??= {};
                  _currentContext!['delete_schedule_id'] = del['id'];
                  _sendMessage(text: 'confirmDelete'.tr(), confirmDelete: true);
                },
                onCancel: () {
                  _currentContext = null;
                  setState(() {
                    _messages.add(ChatMessage(text: 'deleteCancelled'.tr(), isUser: false));
                  });
                },
              ),
            );
          } else if (data['confirm_past_edit'] != null) {
            final past = data['confirm_past_edit'] as Map<String, dynamic>;
            if (aiReply.isNotEmpty) _messages.add(ChatMessage(text: aiReply, isUser: false));
            _messages.add(
              PastEditConfirmMessage(
                title: past['title'] as String? ?? '',
                startTime: past['start_time'] as String?,
                onConfirm: () {
                  _sendMessage(confirmPastEdit: true);
                },
                onCancel: () {
                  _currentContext = null;
                  setState(() {
                    _messages.add(ChatMessage(text: 'editCancelled'.tr(), isUser: false));
                  });
                },
              ),
            );
          } else if (data['conflict'] != null) {
            // Conflict Detected
            _messages.add(
              ChatMessage(text: aiReply.isNotEmpty ? aiReply : 'timeConflict'.tr(), isUser: false),
            );
            _messages.add(
              ConflictMessage(
                onConfirm: () => _sendMessage(forceCreate: true),
                onChange: () {
                  // Let AI know
                  _sendMessage(text: 'changeTimeRequest'.tr());
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
                    _conversationHistory.add({'role': 'user', 'content': 'selectedLocation'.tr(namedArgs: {'name': name})});
                    setState(() {
                      _messages.add(ChatMessage(text: 'selectedLocation'.tr(namedArgs: {'name': name}), isUser: true));
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
                    _conversationHistory.add({'role': 'user', 'content': 'confirmLocation'.tr() + '：$detName'});
                    _sendMessage(forceCreate: true, overrideLat: detLat, overrideLon: detLon);
                  },
                  onReject: () {
                    // Clear location from context so AI asks again
                    _currentContext ??= {};
                    _currentContext!.remove('location');
                    _sendMessage(text: 'locationNotCorrect'.tr(namedArgs: {'name': detName}));
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
                  : '✅ ${scheduleTitle.isNotEmpty ? 'scheduleCreatedWithTitle'.tr(namedArgs: {'title': scheduleTitle}) : 'scheduleCreated'.tr()}';
              _messages.add(ChatMessage(text: successMsg, isUser: false));
            } else if (aiReply.isNotEmpty) {
              _messages.add(ChatMessage(text: aiReply, isUser: false));
            }
          }

          _isLoading = false;
        });

        if (data['is_complete'] == true && data['conflict'] == null) {
          widget.onScheduleCreated();
          _loadScheduleList(); // 刷新行程清單（create / edit / delete 後畫面同步）
        }

        _scrollToBottom();
      }
    } catch (e) {
      debugPrint('[ChatWidget] Error: $e');
      // Remove the dangling user turn so history stays paired (user+assistant)
      if (!forceCreate && _conversationHistory.isNotEmpty &&
          _conversationHistory.last['role'] == 'user') {
        _conversationHistory.removeLast();
      }
      setState(() {
        _messages.add(ChatMessage(text: 'systemError'.tr(), isUser: false));
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
      _conversationHistory.add({'role': 'user', 'content': 'manualSelectedLocation'.tr(namedArgs: {'address': address})});
      setState(() {
        _messages.add(ChatMessage(text: 'manualSelectedLocation'.tr(namedArgs: {'address': address}), isUser: true));
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
                          content: Text('contactsLoaded'.tr(namedArgs: {'count': _contacts.length.toString()})),
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
          ...candidates.asMap().entries.map((entry) {
            final idx = entry.key;
            final c = entry.value;
            final lat = (c['lat'] as num?)?.toDouble();
            final lon = (c['lon'] as num?)?.toDouble();
            final rawName = c['name']?.toString() ?? '';
            final rawAddr = c['address']?.toString() ?? '';
            final name = rawName.isNotEmpty ? rawName : (rawAddr.isNotEmpty ? rawAddr.split(',').first.trim() : '地點 ${idx + 1}');
            final address = rawAddr;
            return Card(
              margin: const EdgeInsets.only(bottom: 6),
              child: ListTile(
                leading: const Icon(Icons.location_on, color: Colors.black54),
                title: Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(address, maxLines: 2, overflow: TextOverflow.ellipsis),
                trailing: IconButton(
                  icon: const Icon(Icons.open_in_new, size: 18, color: Colors.blue),
                  tooltip: 'Google Maps で確認',
                  onPressed: () => _openInGoogleMaps(lat, lon, name),
                ),
                onTap: () => onSelect(c),
              ),
            );
          }),
          Card(
            margin: const EdgeInsets.only(bottom: 6),
            child: ListTile(
              leading: const Icon(Icons.map, color: Colors.black54),
              title: Text('changeLocation'.tr(), style: const TextStyle(fontWeight: FontWeight.w600)),
              onTap: onPickMap,
            ),
          ),
        ],
      ),
    );
  }
}

class DeleteConfirmMessage extends StatefulWidget {
  final String title;
  final String? startTime;
  final VoidCallback onConfirm;
  final VoidCallback onCancel;

  const DeleteConfirmMessage({
    super.key,
    required this.title,
    this.startTime,
    required this.onConfirm,
    required this.onCancel,
  });

  @override
  State<DeleteConfirmMessage> createState() => _DeleteConfirmMessageState();
}

class _DeleteConfirmMessageState extends State<DeleteConfirmMessage> {
  bool _tapped = false;

  String? _formatTime(String? iso) {
    if (iso == null) return null;
    try {
      final dt = DateTime.parse(iso);
      return DateFormat('MM/dd HH:mm').format(dt);
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final timeStr = _formatTime(widget.startTime);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Card(
        color: Colors.red[50],
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Colors.red, size: 20),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'confirmDeleteTitle'.tr(namedArgs: {'title': widget.title}),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              if (timeStr != null) ...[
                const SizedBox(height: 4),
                Text(timeStr, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _tapped ? null : () {
                        setState(() => _tapped = true);
                        widget.onCancel();
                      },
                      child: Text('cancel'.tr()),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _tapped ? null : () {
                        setState(() => _tapped = true);
                        widget.onConfirm();
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        foregroundColor: Colors.white,
                      ),
                      child: Text('confirmDelete'.tr()),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class PastEditConfirmMessage extends StatefulWidget {
  final String title;
  final String? startTime;
  final VoidCallback onConfirm;
  final VoidCallback onCancel;

  const PastEditConfirmMessage({
    super.key,
    required this.title,
    this.startTime,
    required this.onConfirm,
    required this.onCancel,
  });

  @override
  State<PastEditConfirmMessage> createState() => _PastEditConfirmMessageState();
}

class _PastEditConfirmMessageState extends State<PastEditConfirmMessage> {
  bool _tapped = false;

  String? _formatTime(String? iso) {
    if (iso == null) return null;
    try {
      final dt = DateTime.parse(iso);
      return DateFormat('MM/dd HH:mm').format(dt);
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final timeStr = _formatTime(widget.startTime);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Card(
        color: Colors.orange[50],
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const Icon(Icons.history, color: Colors.orange, size: 20),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'confirmPastEditTitle'.tr(namedArgs: {'title': widget.title}),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              if (timeStr != null) ...[
                const SizedBox(height: 4),
                Text(timeStr, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _tapped ? null : () {
                        setState(() => _tapped = true);
                        widget.onCancel();
                      },
                      child: Text('cancel'.tr()),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _tapped ? null : () {
                        setState(() => _tapped = true);
                        widget.onConfirm();
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange,
                        foregroundColor: Colors.white,
                      ),
                      child: Text('confirmPastEdit'.tr()),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
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
                      child: Text('notHere'.tr()),
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
            onPressed: _tapped ? null : () {
              setState(() => _tapped = true);
              widget.onChange();
            },
            icon: const Icon(Icons.map, size: 16),
            label: Text('changeLocation'.tr()),
            style: TextButton.styleFrom(foregroundColor: Colors.black54),
          ),
        ],
      ),
    );
  }
}
