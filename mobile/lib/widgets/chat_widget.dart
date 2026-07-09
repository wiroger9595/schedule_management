import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import '../providers/auth_provider.dart';
import '../screens/location_picker_screen.dart';
import '../utils/constants.dart';
import 'attendee_selector.dart';

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
    });
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('chatCleared'.tr())),
      );
    }
    // 同步清除 server-side Redis history
    ApiService().clearChatHistory();
    _loadScheduleList();
  }

  List<dynamic> _contacts = [];
  bool _showMentionList = false;
  String _mentionQuery = '';
  int _mentionStartIndex = -1;

  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _speechAvailable = false;
  bool _isListening = false;

  @override
  void initState() {
    super.initState();
    _loadContacts();
    _loadScheduleList();
    // Speech init is deferred until the mic button is tapped — calling it
    // here would pop the mic/speech permission dialog as soon as the chat
    // screen opens, before the user has expressed any intent to use it.
  }

  @override
  void dispose() {
    _speech.stop();
    super.dispose();
  }

  Future<void> _initSpeech() async {
    _speechAvailable = await _speech.initialize(
      onStatus: (status) {
        if ((status == 'done' || status == 'notListening') && mounted) {
          setState(() => _isListening = false);
        }
      },
      onError: (error) {
        if (mounted) setState(() => _isListening = false);
      },
    );
  }

  Future<void> _toggleListening() async {
    if (_isListening) {
      await _speech.stop();
      setState(() => _isListening = false);
      return;
    }
    if (!_speechAvailable) {
      await _initSpeech();
      if (!_speechAvailable) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('voiceNotAvailable'.tr())),
          );
        }
        return;
      }
    }
    setState(() => _isListening = true);
    final localeId = context.locale.languageCode == 'zh' ? 'zh-TW' : 'en-US';
    await _speech.listen(
      listenOptions: stt.SpeechListenOptions(
        localeId: localeId,
        listenFor: const Duration(seconds: 60),
        pauseFor: const Duration(seconds: 8),
      ),
      onResult: (result) {
        _controller.text = result.recognizedWords;
        _controller.selection = TextSelection.fromPosition(
          TextPosition(offset: _controller.text.length),
        );
        _onTextChanged(_controller.text);
        if (result.finalResult && mounted) {
          setState(() => _isListening = false);
        }
      },
    );
  }

  Future<void> _loadScheduleList() async {
    try {
      final apiService = ApiService();
      final schedules = await apiService.getSchedules();
      if (mounted) {
        setState(() {
          _scheduleList = schedules
              .where((s) => s.status != ScheduleStatus.cancel)
              .map((s) => s.toJson())
              .toList();
        });
      }
    } catch (_) {}
  }

  /// Builds an AI ChatMessage with 👍/👎 feedback wired to the backend.
  ChatMessage _buildAiMessage(String text) {
    final history = List<Map<String, String>>.from(_conversationHistory);
    final userMsg = history.isNotEmpty && history.last['role'] == 'user'
        ? (history.last['content'] ?? '')
        : (history.length >= 2 ? (history[history.length - 2]['content'] ?? '') : '');
    return ChatMessage(
      text: text,
      isUser: false,
      onFeedback: (bool isGood, String? correction) {
        ApiService().submitFeedback(
          userMessage: userMsg,
          aiReply: text,
          isGood: isGood,
          correction: correction,
          conversationJson: jsonEncode(history),
        );
      },
    );
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

  static const _kBusyPhrases = ['系統目前很忙', 'AI 處理失敗'];

  /// Calls chatWithAI and silently retries once (after 1.5 s) when:
  ///   - the HTTP call throws (e.g. 500, timeout), OR
  ///   - the backend returns a "busy" ai_reply that means all providers failed.
  Future<Map<String, dynamic>> _chatWithRetry(
    ApiService apiService, {
    required String message,
    Map<String, dynamic>? currentContext,
    List<Map<String, String>>? conversationHistory,
    bool forceCreate = false,
    bool confirmLocation = false,
    bool confirmDelete = false,
    bool confirmPastEdit = false,
    bool confirmTimeInput = false,
    String? newStartTime,
    double? latitude,
    double? longitude,
    List<Map<String, dynamic>>? scheduleList,
  }) async {
    for (int attempt = 0; attempt <= 1; attempt++) {
      if (attempt > 0) {
        await Future.delayed(const Duration(milliseconds: 1500));
      }
      try {
        final data = await apiService.chatWithAI(
          message,
          currentContext: currentContext,
          conversationHistory: conversationHistory,
          forceCreate: forceCreate,
          confirmLocation: confirmLocation,
          confirmDelete: confirmDelete,
          confirmPastEdit: confirmPastEdit,
          confirmTimeInput: confirmTimeInput,
          newStartTime: newStartTime,
          latitude: latitude,
          longitude: longitude,
          scheduleList: scheduleList,
        );
        final aiReply = data['ai_reply'] as String? ?? '';
        if (attempt == 0 && _kBusyPhrases.any((s) => aiReply.contains(s))) {
          continue; // busy reply — retry silently
        }
        return data;
      } catch (_) {
        if (attempt < 1) continue; // retry once on error
        rethrow;
      }
    }
    throw Exception('AI unavailable after retries');
  }

  Future<void> _sendMessage({String? text, bool forceCreate = false, bool confirmDelete = false, bool confirmPastEdit = false, bool confirmTimeInput = false, String? newStartTime, double? overrideLat, double? overrideLon}) async {
    final messageText = text ?? _controller.text.trim();
    if (messageText.isEmpty && !forceCreate && !confirmPastEdit && !confirmDelete && !confirmTimeInput) return;

    if (!forceCreate && !confirmPastEdit && !confirmDelete && !confirmTimeInput) {
      // Record user turn in conversation history before sending
      _conversationHistory.add({'role': 'user', 'content': messageText});
      setState(() {
        _messages.add(ChatMessage(text: messageText, isUser: true));
        _isLoading = true;
      });
      _controller.clear();
      _scrollToBottom();
    } else if (confirmTimeInput && messageText.isNotEmpty) {
      // Show picked time as user bubble; don't add to AI history (AI is bypassed)
      setState(() {
        _messages.add(ChatMessage(text: messageText, isUser: true));
        _isLoading = true;
      });
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

      final data = await _chatWithRetry(
        apiService,
        message: (forceCreate || confirmPastEdit || confirmDelete || confirmTimeInput) ? 'Confirm' : messageText,
        currentContext: _currentContext,
        conversationHistory: _conversationHistory,
        forceCreate: forceCreate,
        confirmLocation: forceCreate,
        confirmDelete: confirmDelete,
        confirmPastEdit: confirmPastEdit,
        confirmTimeInput: confirmTimeInput,
        newStartTime: newStartTime,
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
            if (aiReply.isNotEmpty) _messages.add(_buildAiMessage(aiReply));
            _currentContext = null;
            widget.onScheduleCreated();
            _loadScheduleList();
          } else if (data['confirm_delete'] != null) {
            // Backend wants user to confirm deletion (single or batch)
            final delList = (data['confirm_delete'] as List<dynamic>)
                .map((e) => Map<String, dynamic>.from(e as Map))
                .toList();
            if (aiReply.isNotEmpty) _messages.add(_buildAiMessage(aiReply));
            _messages.add(
              DeleteConfirmMessage(
                items: delList,
                onConfirm: () {
                  _currentContext ??= {};
                  _currentContext!['delete_schedule_ids'] =
                      delList.map((d) => d['id'] as String).toList();
                  if (delList.length == 1) {
                    _currentContext!['delete_schedule_id'] = delList[0]['id'];
                  }
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
          } else if (data['needs_time_input'] == true) {
            if (aiReply.isNotEmpty) _messages.add(_buildAiMessage(aiReply));
            _showTimePickerForEdit();
          } else if (data['confirm_past_edit'] != null) {
            final past = data['confirm_past_edit'] as Map<String, dynamic>;
            if (aiReply.isNotEmpty) _messages.add(_buildAiMessage(aiReply));
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
            _messages.add(_buildAiMessage(aiReply.isNotEmpty ? aiReply : 'timeConflict'.tr()));
            _messages.add(
              ConflictMessage(
                onConfirm: () => _sendMessage(forceCreate: true),
                onChange: () {
                  // Let AI know
                  _sendMessage(text: 'changeTimeRequest'.tr());
                },
              ),
            );
          } else if (data['needs_location_input'] == true) {
            if (aiReply.isNotEmpty) _messages.add(_buildAiMessage(aiReply));
            _showLocationPickerForEdit();
          } else if (data['needs_location_confirm'] == true) {
            _messages.add(_buildAiMessage(aiReply));

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
              // Fallback: if backend sent 1 candidate without location_details, use the candidate.
              final det = (data['location_details'] as Map<String, dynamic>?)
                  ?? (candidates != null && candidates.length == 1
                      ? candidates.first as Map<String, dynamic>?
                      : null);
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
          } else if (data['location_not_found'] == true) {
            // Location not found — show manual input card
            final failedLocation = (_currentContext?['location'] as String?) ?? '';
            if (aiReply.isNotEmpty) _messages.add(_buildAiMessage(aiReply));
            _messages.add(
              LocationManualInputMessage(
                initialValue: failedLocation,
                onConfirm: (String address, double? lat, double? lon) {
                  _currentContext ??= {};
                  _currentContext!['location'] = address;
                  _conversationHistory.add({'role': 'user', 'content': '手動輸入地址：$address'});
                  _sendMessage(forceCreate: true, overrideLat: lat, overrideLon: lon);
                },
              ),
            );
          } else {
            // Normal reply or schedule created
            if (data['schedule'] != null) {
              final scheduleData = data['schedule'] as Map<String, dynamic>?;
              final scheduleTitle = (data['updated_data']?['title'] as String?) ??
                  (scheduleData?['title'] as String?) ?? '';
              final successMsg = aiReply.isNotEmpty
                  ? aiReply
                  : '✅ ${scheduleTitle.isNotEmpty ? 'scheduleCreatedWithTitle'.tr(namedArgs: {'title': scheduleTitle}) : 'scheduleCreated'.tr()}';
              _messages.add(_buildAiMessage(successMsg));

              // 自動顯示邀請卡片
              final scheduleId = scheduleData?['schedule_id'] as String?;
              if (scheduleId != null) {
                _messages.add(InviteCard(
                  scheduleId: scheduleId,
                  scheduleName: scheduleTitle,
                  onDone: (int count) {
                    if (count > 0) {
                      setState(() {
                        _messages.add(_buildAiMessage(
                          'inviteSentSuccess'.tr(namedArgs: {'count': '$count'}),
                        ));
                      });
                    }
                    setState(() {});
                    _scrollToBottom();
                  },
                ));
              }
            } else if (aiReply.isNotEmpty) {
              _messages.add(_buildAiMessage(aiReply));
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

  void _showTimePickerForEdit() {
    setState(() {
      _messages.add(TimePickerMessage(
        onConfirm: (DateTime picked) {
          final hour = picked.hour;
          final period = hour < 12 ? '上午' : (hour < 14 ? '中午' : (hour < 18 ? '下午' : (hour < 22 ? '晚上' : '深夜')));
          final displayHour = hour % 12 == 0 ? 12 : hour % 12;
          final minStr = picked.minute == 0 ? '' : ':${picked.minute.toString().padLeft(2, '0')}';
          final display = '時間改到${picked.year}年${picked.month}月${picked.day}日 $period$displayHour點$minStr';
          _sendMessage(text: display, confirmTimeInput: true, newStartTime: picked.toIso8601String());
        },
        onCancel: () {
          _currentContext = null;
          setState(() => _messages.add(ChatMessage(text: 'editCancelled'.tr(), isUser: false)));
        },
      ));
    });
    _scrollToBottom();
  }

  void _showLocationPickerForEdit() {
    setState(() {
      _messages.add(LocationInputMessage(
        onConfirm: (String address, double? lat, double? lon) {
          _currentContext ??= {};
          _currentContext!['location'] = address;
          if (lat != null) _currentContext!['latitude'] = lat;
          if (lon != null) _currentContext!['longitude'] = lon;
          final isPendingEdit =
              _currentContext!.containsKey('_pending_edit_schedule_id') ||
              _currentContext!.containsKey('_pending_past_edit_id');
          if (lat != null && lon != null && isPendingEdit) {
            setState(() => _messages.add(ChatMessage(text: '地點：$address', isUser: true)));
            _conversationHistory.add({'role': 'user', 'content': '地點：$address'});
            _sendMessage(forceCreate: true, overrideLat: lat, overrideLon: lon);
          } else {
            _sendMessage(text: address);
          }
        },
        onCancel: () {
          _currentContext = null;
          setState(() => _messages.add(ChatMessage(text: 'editCancelled'.tr(), isUser: false)));
        },
      ));
    });
    _scrollToBottom();
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
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
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
                          SizedBox(height: 32),
                          Text(
                            'intentSelectHint'.tr(),
                            style: TextStyle(
                              color: Colors.grey[500],
                              fontSize: 13,
                            ),
                          ),
                          SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: _IntentButton(
                                  label: 'intentAdd'.tr(),
                                  icon: Icons.add_circle_outline,
                                  color: const Color(0xFF4CAF50),
                                  onTap: () {
                                    setState(() {
                                      _messages.add(ChatMessage(
                                        text: 'intentAddPrompt'.tr(),
                                        isUser: false,
                                      ));
                                    });
                                    _scrollToBottom();
                                  },
                                ),
                              ),
                              SizedBox(width: 10),
                              Expanded(
                                child: _IntentButton(
                                  label: 'intentEdit'.tr(),
                                  icon: Icons.edit_outlined,
                                  color: const Color(0xFFFF9800),
                                  onTap: () async {
                                    await _loadScheduleList();
                                    if (!mounted) return;
                                    setState(() {
                                      _messages.add(ChatMessage(
                                        text: 'intentEditPickPrompt'.tr(),
                                        isUser: false,
                                      ));
                                      _messages.add(SchedulePickerMessage(
                                        schedules: List.from(_scheduleList),
                                        onSelect: (schedule) {
                                          final id = schedule['id'] as String? ?? '';
                                          final title = schedule['title'] as String? ?? '';
                                          final startTimeStr = schedule['start_time'] as String?;
                                          final isPast = startTimeStr != null &&
                                              (DateTime.tryParse(startTimeStr)?.isBefore(DateTime.now()) ?? false);
                                          _currentContext = {
                                            '_pending_edit_schedule_id': id,
                                            if (isPast) '_pending_past_edit_id': id,
                                            ...schedule,
                                          };
                                          setState(() {
                                            _messages.add(ChatMessage(text: '更新行程：$title', isUser: true));
                                            if (isPast) {
                                              _messages.add(ChatMessage(
                                                text: 'scheduleExpiredEditWarning'.tr(namedArgs: {'title': title}),
                                                isUser: false,
                                              ));
                                            }
                                            _messages.add(EditOptionsMessage(
                                              onEditTime: _showTimePickerForEdit,
                                              onEditLocation: _showLocationPickerForEdit,
                                              onCancel: () {
                                                _currentContext = null;
                                                setState(() => _messages.add(ChatMessage(text: 'editCancelled'.tr(), isUser: false)));
                                              },
                                            ));
                                          });
                                          _scrollToBottom();
                                        },
                                        onCancel: () {
                                          _currentContext = null;
                                          setState(() {
                                            _messages.add(ChatMessage(text: 'editCancelled'.tr(), isUser: false));
                                          });
                                        },
                                      ));
                                    });
                                    _scrollToBottom();
                                  },
                                ),
                              ),
                              SizedBox(width: 10),
                              Expanded(
                                child: _IntentButton(
                                  label: 'intentDelete'.tr(),
                                  icon: Icons.delete_outline,
                                  color: const Color(0xFFE53935),
                                  onTap: () async {
                                    await _loadScheduleList();
                                    if (!mounted) return;
                                    setState(() {
                                      _messages.add(ChatMessage(
                                        text: 'intentDeletePickPrompt'.tr(),
                                        isUser: false,
                                      ));
                                      _messages.add(SchedulePickerMessage(
                                        schedules: List.from(_scheduleList),
                                        onSelect: (schedule) {
                                          final id = schedule['id'] as String? ?? '';
                                          final title = schedule['title'] as String? ?? '';
                                          final startTime = schedule['start_time'] as String?;
                                          setState(() {
                                            _messages.add(ChatMessage(text: '刪除行程：$title', isUser: true));
                                            _messages.add(DeleteConfirmMessage(
                                              items: [{'id': id, 'title': title, 'start_time': startTime}],
                                              onConfirm: () {
                                                _currentContext = {
                                                  'delete_schedule_ids': [id],
                                                  'delete_schedule_id': id,
                                                };
                                                _sendMessage(confirmDelete: true);
                                              },
                                              onCancel: () {
                                                _currentContext = null;
                                                setState(() {
                                                  _messages.add(ChatMessage(text: 'deleteCancelled'.tr(), isUser: false));
                                                });
                                              },
                                            ));
                                          });
                                          _scrollToBottom();
                                        },
                                        onCancel: () {
                                          _currentContext = null;
                                          setState(() {
                                            _messages.add(ChatMessage(text: 'deleteCancelled'.tr(), isUser: false));
                                          });
                                        },
                                      ));
                                    });
                                    _scrollToBottom();
                                  },
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
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
                  icon: Icon(_isListening ? Icons.mic : Icons.mic_none),
                  color: _isListening ? Colors.red : null,
                  tooltip: 'voiceInput'.tr(),
                  onPressed: _isLoading ? null : _toggleListening,
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

class ChatMessage extends StatefulWidget {
  final String text;
  final bool isUser;
  final void Function(bool isGood, String? correction)? onFeedback;

  const ChatMessage({super.key, required this.text, required this.isUser, this.onFeedback});

  @override
  State<ChatMessage> createState() => _ChatMessageState();
}

class _ChatMessageState extends State<ChatMessage> {
  bool? _feedbackGiven;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: widget.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: widget.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (!widget.isUser) ...[
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
                    color: widget.isUser ? Colors.black : Colors.grey[200],
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Text(
                    widget.text,
                    style: TextStyle(
                      color: widget.isUser ? Colors.white : Colors.black87,
                      fontSize: 15,
                    ),
                  ),
                ),
              ),
              if (widget.isUser) ...[
                SizedBox(width: 8),
                CircleAvatar(
                  radius: 16,
                  backgroundColor: Colors.grey[300],
                  child: Icon(Icons.person, size: 16, color: Colors.black87),
                ),
              ],
            ],
          ),
          if (!widget.isUser && widget.onFeedback != null)
            Padding(
              padding: const EdgeInsets.only(left: 40, top: 2),
              child: _feedbackGiven != null
                  ? Text('感謝反饋', style: TextStyle(fontSize: 11, color: Colors.grey))
                  : Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _FeedbackButton(
                          icon: Icons.thumb_up_outlined,
                          color: Colors.green,
                          onTap: () {
                            setState(() => _feedbackGiven = true);
                            widget.onFeedback!(true, null);
                          },
                        ),
                        SizedBox(width: 4),
                        _FeedbackButton(
                          icon: Icons.thumb_down_outlined,
                          color: Colors.red,
                          onTap: () => _showCorrectionDialog(context),
                        ),
                      ],
                    ),
            ),
        ],
      ),
    );
  }

  void _showCorrectionDialog(BuildContext ctx) {
    final ctrl = TextEditingController();
    showDialog(
      context: ctx,
      builder: (dCtx) => AlertDialog(
        title: const Text('AI 回答有誤？'),
        content: _CorrectionField(controller: ctrl),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dCtx), child: const Text('取消')),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(dCtx);
              setState(() => _feedbackGiven = false);
              final correction = ctrl.text.trim();
              widget.onFeedback!(false, correction.isEmpty ? null : correction);
            },
            child: const Text('送出'),
          ),
        ],
      ),
    );
  }
}

class _CorrectionField extends StatefulWidget {
  final TextEditingController controller;
  const _CorrectionField({required this.controller});

  @override
  State<_CorrectionField> createState() => _CorrectionFieldState();
}

class _CorrectionFieldState extends State<_CorrectionField> {
  final _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(milliseconds: 350), () {
      if (mounted) _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: widget.controller,
      focusNode: _focusNode,
      decoration: const InputDecoration(hintText: '正確答案是...（可不填）'),
      maxLines: 3,
    );
  }
}

class _FeedbackButton extends StatelessWidget {
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _FeedbackButton({required this.icon, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.all(4),
        child: Icon(icon, size: 16, color: color),
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
  final List<Map<String, dynamic>>? items;
  final VoidCallback onConfirm;
  final VoidCallback onCancel;

  const DeleteConfirmMessage({
    super.key,
    required this.items,
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
    final items = widget.items;
    if (items == null || items.isEmpty) return const SizedBox.shrink();
    final isBatch = items.length > 1;
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
                      isBatch
                          ? 'confirmDeleteBatch'.tr(namedArgs: {'count': '${items.length}'})
                          : 'confirmDeleteTitle'.tr(namedArgs: {'title': items[0]['title'] as String? ?? ''}),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              ...items.map((item) {
                final timeStr = _formatTime(item['start_time'] as String?);
                return Padding(
                  padding: const EdgeInsets.only(bottom: 2),
                  child: Text(
                    timeStr != null
                        ? '• ${item['title']}  $timeStr'
                        : '• ${item['title']}',
                    style: TextStyle(color: Colors.grey[700], fontSize: 13),
                  ),
                );
              }),
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

/// Reverse-geocode via Nominatim. Returns display_name or "lat, lon" on failure.
Future<String> _reverseGeocode(double lat, double lon) async {
  try {
    final uri = Uri.parse(
      'https://nominatim.openstreetmap.org/reverse'
      '?lat=$lat&lon=$lon&format=json&accept-language=zh-TW',
    );
    final resp = await http
        .get(uri, headers: {'User-Agent': 'ScheduleManagementApp/1.0'})
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode == 200) {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      return (data['display_name'] as String?) ?? '$lat, $lon';
    }
  } catch (_) {}
  return '$lat, $lon';
}

/// Card shown when the AI cannot find the location.
/// Pre-fills the original location text so the user can edit and confirm.
/// GPS button auto-fills via reverse geocoding.
class LocationManualInputMessage extends StatefulWidget {
  final String initialValue;
  // address, lat (nullable), lon (nullable)
  final void Function(String address, double? lat, double? lon) onConfirm;

  const LocationManualInputMessage({
    super.key,
    required this.initialValue,
    required this.onConfirm,
  });

  @override
  State<LocationManualInputMessage> createState() => _LocationManualInputMessageState();
}

class _LocationManualInputMessageState extends State<LocationManualInputMessage> {
  late final TextEditingController _ctrl;
  final FocusNode _focusNode = FocusNode();
  bool _submitted = false;
  bool _locating = false;
  double? _lat;
  double? _lon;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(text: widget.initialValue);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _submit() {
    final address = _ctrl.text.trim();
    if (address.isEmpty) return;
    setState(() => _submitted = true);
    widget.onConfirm(address, _lat, _lon);
  }

  Future<void> _useCurrentLocation() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('locationServiceDisabled'.tr())),
        );
      }
      return;
    }
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('locationPermissionDenied'.tr())),
        );
      }
      return;
    }

    setState(() {
      _locating = true;
      _ctrl.text = 'locating'.tr();
    });

    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      final address = await _reverseGeocode(pos.latitude, pos.longitude);
      if (mounted) {
        setState(() {
          _ctrl.text = address;
          _lat = pos.latitude;
          _lon = pos.longitude;
          _locating = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _locating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('locationFailed'.tr())),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.orange.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.orange.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.location_off, color: Colors.orange.shade700, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  'locationNotFound'.tr(),
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: Colors.orange.shade800,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _ctrl,
            focusNode: _focusNode,
            enabled: !_submitted && !_locating,
            decoration: InputDecoration(
              hintText: 'enterAddressHint'.tr(),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              isDense: true,
            ),
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: (_submitted || _locating) ? null : _useCurrentLocation,
                  icon: _locating
                      ? const SizedBox(
                          width: 14, height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.my_location, size: 15),
                  label: Text(_locating ? 'locating'.tr() : 'useCurrentLocation'.tr(),
                      style: const TextStyle(fontSize: 13)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton(
                  onPressed: (_submitted || _locating) ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: theme.colorScheme.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: Text('confirmAddress'.tr()),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class TimePickerMessage extends StatefulWidget {
  final void Function(DateTime) onConfirm;
  final VoidCallback onCancel;

  const TimePickerMessage({
    super.key,
    required this.onConfirm,
    required this.onCancel,
  });

  @override
  State<TimePickerMessage> createState() => _TimePickerMessageState();
}

class _TimePickerMessageState extends State<TimePickerMessage> {
  DateTime _selected = DateTime.now().add(const Duration(days: 1)).copyWith(
    hour: 10, minute: 0, second: 0, millisecond: 0, microsecond: 0,
  );
  bool _tapped = false;

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _selected,
      firstDate: now,
      lastDate: now.add(const Duration(days: 365 * 2)),
    );
    if (!mounted) return;
    if (picked != null) {
      setState(() {
        _selected = DateTime(picked.year, picked.month, picked.day,
            _selected.hour, _selected.minute);
      });
    }
  }

  Future<void> _pickTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: _selected.hour, minute: _selected.minute),
    );
    if (!mounted) return;
    if (picked != null) {
      setState(() {
        _selected = DateTime(_selected.year, _selected.month, _selected.day,
            picked.hour, picked.minute);
      });
    }
  }

  String _formatDate() {
    const weekdays = ['一', '二', '三', '四', '五', '六', '日'];
    final w = weekdays[_selected.weekday - 1];
    return '${_selected.month}月${_selected.day}日（$w）';
  }

  String _formatTime() {
    final h = _selected.hour;
    final period = h < 12 ? '上午' : (h < 14 ? '中午' : (h < 18 ? '下午' : (h < 22 ? '晚上' : '深夜')));
    final display = h % 12 == 0 ? 12 : h % 12;
    final min = _selected.minute.toString().padLeft(2, '0');
    return '$period $display:$min';
  }

  @override
  Widget build(BuildContext context) {
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
                  const Icon(Icons.schedule, color: Colors.orange, size: 20),
                  const SizedBox(width: 6),
                  Text('selectNewTime'.tr(),
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
              const SizedBox(height: 12),
              // Date row
              InkWell(
                onTap: _tapped ? null : _pickDate,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.orange.shade200),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.calendar_today, size: 16, color: Colors.orange),
                      const SizedBox(width: 8),
                      Text(_formatDate(),
                          style: const TextStyle(fontSize: 15)),
                      const Spacer(),
                      Icon(Icons.edit, size: 14, color: Colors.grey[400]),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 8),
              // Time row
              InkWell(
                onTap: _tapped ? null : _pickTime,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.orange.shade200),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.access_time, size: 16, color: Colors.orange),
                      const SizedBox(width: 8),
                      Text(_formatTime(),
                          style: const TextStyle(fontSize: 15)),
                      const Spacer(),
                      Icon(Icons.edit, size: 14, color: Colors.grey[400]),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
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
                        widget.onConfirm(_selected);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange,
                        foregroundColor: Colors.white,
                      ),
                      child: Text('confirmNewTime'.tr()),
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

class LocationInputMessage extends StatefulWidget {
  final void Function(String address, double? lat, double? lon) onConfirm;
  final VoidCallback onCancel;

  const LocationInputMessage({
    super.key,
    required this.onConfirm,
    required this.onCancel,
  });

  @override
  State<LocationInputMessage> createState() => _LocationInputMessageState();
}

class _LocationInputMessageState extends State<LocationInputMessage> {
  final TextEditingController _ctrl = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _submitted = false;
  bool _locating = false;
  double? _lat;
  double? _lon;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _focusNode.requestFocus());
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _submit() {
    final address = _ctrl.text.trim();
    if (address.isEmpty) return;
    setState(() => _submitted = true);
    widget.onConfirm(address, _lat, _lon);
  }

  Future<void> _useGPS() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('locationServiceDisabled'.tr())));
      return;
    }
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) permission = await Geolocator.requestPermission();
    if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('locationPermissionDenied'.tr())));
      return;
    }
    setState(() { _locating = true; _ctrl.text = 'locating'.tr(); });
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      final address = await _reverseGeocode(pos.latitude, pos.longitude);
      if (mounted) setState(() { _ctrl.text = address; _lat = pos.latitude; _lon = pos.longitude; _locating = false; });
    } catch (_) {
      if (mounted) {
        setState(() => _locating = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('locationFailed'.tr())));
      }
    }
  }

  Future<void> _pickMap() async {
    final result = await Navigator.of(context).push<Map<String, dynamic>>(
      MaterialPageRoute(builder: (_) => LocationPickerScreen()),
    );
    if (result != null && mounted) {
      final lat = (result['latitude'] as num?)?.toDouble();
      final lon = (result['longitude'] as num?)?.toDouble();
      final addr = result['address'] as String? ?? result['name'] as String? ?? '';
      setState(() { _ctrl.text = addr; _lat = lat; _lon = lon; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.location_on_outlined, color: Colors.blue.shade700, size: 16),
              const SizedBox(width: 6),
              Text(
                'selectLocation'.tr(),
                style: TextStyle(fontWeight: FontWeight.w600, color: Colors.blue.shade800, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _ctrl,
            focusNode: _focusNode,
            enabled: !_submitted && !_locating,
            decoration: InputDecoration(
              hintText: 'enterAddressHint'.tr(),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              isDense: true,
            ),
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: (_submitted || _locating) ? null : _useGPS,
                  icon: _locating
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.my_location, size: 15),
                  label: Text(_locating ? 'locating'.tr() : 'useCurrentLocation'.tr(), style: const TextStyle(fontSize: 12)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: (_submitted || _locating) ? null : _pickMap,
                  icon: const Icon(Icons.map_outlined, size: 15),
                  label: Text('selectLocation'.tr(), style: const TextStyle(fontSize: 12)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _submitted ? null : widget.onCancel,
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: Text('cancel'.tr()),
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: ElevatedButton(
                  onPressed: (_submitted || _locating) ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue.shade600,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: Text('confirmAddress'.tr()),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class EditOptionsMessage extends StatefulWidget {
  final VoidCallback onEditTime;
  final VoidCallback onEditLocation;
  final VoidCallback onCancel;

  const EditOptionsMessage({
    super.key,
    required this.onEditTime,
    required this.onEditLocation,
    required this.onCancel,
  });

  @override
  State<EditOptionsMessage> createState() => _EditOptionsMessageState();
}

class _EditOptionsMessageState extends State<EditOptionsMessage> {
  bool _tapped = false;

  void _handle(VoidCallback cb) {
    setState(() => _tapped = true);
    cb();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'editOptionsTitle'.tr(),
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _EditOptionBtn(
                      icon: Icons.schedule,
                      label: 'editTime'.tr(),
                      color: Colors.orange,
                      disabled: _tapped,
                      onTap: () => _handle(widget.onEditTime),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _EditOptionBtn(
                      icon: Icons.location_on_outlined,
                      label: 'editLocation'.tr(),
                      color: Colors.blue,
                      disabled: _tapped,
                      onTap: () => _handle(widget.onEditLocation),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              TextButton(
                onPressed: _tapped ? null : () => _handle(widget.onCancel),
                style: TextButton.styleFrom(foregroundColor: Colors.grey[600]),
                child: Text('cancel'.tr()),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EditOptionBtn extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final bool disabled;
  final VoidCallback onTap;

  const _EditOptionBtn({
    required this.icon,
    required this.label,
    required this.color,
    required this.disabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: disabled ? null : onTap,
      icon: Icon(icon, size: 16, color: disabled ? Colors.grey : color),
      label: Text(label, style: TextStyle(color: disabled ? Colors.grey : color, fontSize: 13)),
      style: OutlinedButton.styleFrom(
        side: BorderSide(color: disabled ? Colors.grey.shade300 : color.withValues(alpha: 0.5)),
        padding: const EdgeInsets.symmetric(vertical: 10),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}

class SchedulePickerMessage extends StatefulWidget {
  final List<Map<String, dynamic>> schedules;
  final void Function(Map<String, dynamic>) onSelect;
  final VoidCallback onCancel;

  const SchedulePickerMessage({
    super.key,
    required this.schedules,
    required this.onSelect,
    required this.onCancel,
  });

  @override
  State<SchedulePickerMessage> createState() => _SchedulePickerMessageState();
}

class _SchedulePickerMessageState extends State<SchedulePickerMessage> {
  bool _selected = false;

  String _formatTime(String? iso) {
    if (iso == null) return '';
    try {
      final dt = DateTime.parse(iso);
      return DateFormat('MM/dd HH:mm').format(dt);
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.schedules.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
        child: Text('noSchedules'.tr(), style: TextStyle(color: Colors.grey[500])),
      );
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ...widget.schedules.map((s) {
            final title = s['title'] as String? ?? '';
            final timeStr = _formatTime(s['start_time'] as String?);
            final location = s['location'] as String? ?? '';
            final subtitle = [timeStr, location].where((v) => v.isNotEmpty).join('  ');
            return Card(
              margin: const EdgeInsets.only(bottom: 6),
              child: ListTile(
                leading: const Icon(Icons.event, color: Colors.black54),
                title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: subtitle.isNotEmpty
                    ? Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12))
                    : null,
                onTap: _selected ? null : () {
                  setState(() => _selected = true);
                  widget.onSelect(s);
                },
              ),
            );
          }),
          TextButton(
            onPressed: _selected ? null : widget.onCancel,
            style: TextButton.styleFrom(foregroundColor: Colors.grey[600]),
            child: Text('cancel'.tr()),
          ),
        ],
      ),
    );
  }
}

class _IntentButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _IntentButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withValues(alpha: 0.35), width: 1.5),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 6),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class InviteCard extends StatefulWidget {
  final String scheduleId;
  final String scheduleName;
  final void Function(int invitedCount) onDone;

  const InviteCard({
    super.key,
    required this.scheduleId,
    required this.scheduleName,
    required this.onDone,
  });

  @override
  State<InviteCard> createState() => _InviteCardState();
}

class _InviteCardState extends State<InviteCard> {
  final _apiService = ApiService();
  List<Map<String, dynamic>> _initialAttendees = [];
  List<Map<String, dynamic>> _selectedContacts = [];
  bool _tapped = false;

  @override
  void initState() {
    super.initState();
    _loadCurrentAttendees();
  }

  // Map raw attend records to the shape AttendeeSelector expects, same
  // normalization AddScheduleScreen uses when editing (id -> contact_id).
  Future<void> _loadCurrentAttendees() async {
    try {
      final list = await _apiService.getScheduleAttends(widget.scheduleId);
      final mapped = list.map((att) {
        final m = Map<String, dynamic>.from(att as Map);
        m['attend_id'] = m['id'];
        m['id'] = m['contact_id'];
        return m;
      }).toList();
      if (mounted) {
        setState(() {
          _initialAttendees = mapped;
          _selectedContacts = List<Map<String, dynamic>>.from(mapped);
        });
      }
    } catch (_) {}
  }

  void _showAttendeeSelector() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => AttendeeSelector(
        initialSelectedContacts: _selectedContacts,
        onSelectionChanged: (contacts) {
          setState(() => _selectedContacts = contacts.cast<Map<String, dynamic>>());
        },
      ),
    );
  }

  bool get _hasChanges {
    final initialIds = _initialAttendees.map((c) => c['id']?.toString() ?? '').toSet();
    final currentIds = _selectedContacts.map((c) => c['id']?.toString() ?? '').toSet();
    return initialIds.length != currentIds.length || !initialIds.containsAll(currentIds);
  }

  void _skip() {
    if (_tapped) return;
    setState(() => _tapped = true);
    widget.onDone(0);
  }

  Future<void> _send() async {
    if (_tapped || !_hasChanges) return;
    setState(() => _tapped = true);
    try {
      final initialIds = _initialAttendees.map((c) => c['id']?.toString() ?? '').toSet();
      final addedCount = _selectedContacts
          .where((c) => !initialIds.contains(c['id']?.toString() ?? ''))
          .length;
      // Same PUT /schedules/{id} path the edit screen uses to persist attends.
      await _apiService.updateSchedule(widget.scheduleId, {
        'attends': _selectedContacts.map((c) {
          return {
            'user_id': c['contact_user_id'],
            'contact_id': c['id'] ?? c['contact_id'],
            'name': c['nick_name'] ?? c['name'] ?? c['full_name'],
            'email': c['email'],
            'phone': c['phone'],
            'line_id': c['line_id'],
            'status': c['status'] ?? 'P',
          };
        }).toList(),
      });
      widget.onDone(addedCount);
    } catch (_) {
      if (mounted) setState(() => _tapped = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 40, right: 8, top: 4, bottom: 4),
      child: Card(
        color: Colors.white,
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.person_add, size: 18, color: Colors.black54),
                  SizedBox(width: 6),
                  Text(
                    'inviteCardTitle'.tr(),
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                ],
              ),
              SizedBox(height: 10),

              // Selected attendees + entry point into the same selector edit uses
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: [
                  ..._selectedContacts.map((c) {
                    final name = (c['nick_name'] as String?)?.isNotEmpty == true
                        ? c['nick_name'] as String
                        : (c['name'] as String?) ??
                            (c['email'] as String?) ??
                            (c['contact_user_id'] as String?) ??
                            '?';
                    return Chip(
                      label: Text(name, style: TextStyle(fontSize: 12)),
                      onDeleted: _tapped
                          ? null
                          : () => setState(() => _selectedContacts.remove(c)),
                      deleteIcon: Icon(Icons.close, size: 14),
                      deleteIconColor: Colors.red[700],
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      padding: EdgeInsets.symmetric(horizontal: 4),
                    );
                  }),
                  ActionChip(
                    avatar: Icon(Icons.person_add, size: 16),
                    label: Text('selectParticipants'.tr(), style: TextStyle(fontSize: 12)),
                    onPressed: _tapped ? null : _showAttendeeSelector,
                  ),
                ],
              ),

              SizedBox(height: 12),

              // Action buttons
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: _tapped ? null : _skip,
                    child: Text('inviteSkip'.tr(),
                        style: TextStyle(color: Colors.black54)),
                  ),
                  SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: (_tapped || !_hasChanges) ? null : _send,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.black,
                      foregroundColor: Colors.white,
                      padding:
                          EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8)),
                    ),
                    child: Text(
                      _selectedContacts.isNotEmpty
                          ? '${'inviteSend'.tr()} (${_selectedContacts.length})'
                          : 'inviteSend'.tr(),
                      style: TextStyle(fontSize: 13),
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
