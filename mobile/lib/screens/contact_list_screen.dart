import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:url_launcher/url_launcher.dart';
import 'dart:async';
import '../services/api_service.dart';
import '../utils/form_validators.dart';
import 'contact_history_screen.dart';

class ContactListScreen extends StatefulWidget {
  @override
  _ContactListScreenState createState() => _ContactListScreenState();
}

class _ContactListScreenState extends State<ContactListScreen> {
  final ApiService apiService = ApiService();
  List<dynamic> contacts = [];
  bool isLoading = true;
  bool isSelectionMode = false;
  Set<int> selectedContactIds = {};

  Future<void> _inviteFriend(String contactInfo) async {
    final String inviteSubject = 'Join me on Schedule Management App!';
    final String inviteBody = 'Hey! I use this app to manage my schedules. Join me here: https://example.com/download';

    Uri? launchUri;
    
    // Simple check for email
    if (contactInfo.contains('@')) {
      final Uri emailLaunchUri = Uri(
        scheme: 'mailto',
        path: contactInfo,
        query: encodeQueryParameters(<String, String>{
          'subject': inviteSubject,
          'body': inviteBody,
        }),
      );
      launchUri = emailLaunchUri;
    } else {
      // Assume phone for SMS
      final Uri smsLaunchUri = Uri(
        scheme: 'sms',
        path: contactInfo,
        queryParameters: <String, String>{
          'body': inviteBody,
        },
      );
      launchUri = smsLaunchUri;
    }

    try {
      if (await canLaunchUrl(launchUri)) {
        await launchUrl(launchUri);
      } else {
        throw 'Could not launch $launchUri';
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not launch invite: $e')),
        );
      }
    }
  }

  String? encodeQueryParameters(Map<String, String> params) {
    return params.entries
        .map((e) => '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}')
        .join('&');
  }

  @override
  void initState() {
    super.initState();
    fetchContacts();
  }

  Future<void> fetchContacts() async {
    setState(() => isLoading = true);
    try {
      final headers = await apiService.getHeaders();
      final response = await http.get(
        Uri.parse('${ApiService.baseUrl}/contacts/'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        if (!mounted) return;
        setState(() {
          contacts = jsonDecode(response.body);
          isLoading = false;
        });
      } else {
        throw Exception('Failed to load contacts');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => isLoading = false);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  Future<void> addContact(
    String name,
    String phone,
    String email,
    String lineId, {
    String? contactUserId,
    String? defaultNotificationMethod,
  }) async {
    try {
      final headers = await apiService.getHeaders();
      final body = {
        'nick_name': name,
        'phone': phone,
        'email': email,
        'line_id': lineId,
        'contact_user_id': contactUserId,
        'default_notification_method': defaultNotificationMethod ?? 'mobile',
      };

      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/contacts/'),
        headers: headers,
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        if (!mounted) return;
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Contact added successfully')));
        fetchContacts(); // Refresh list
      } else {
        if (!mounted) return;
        final error = jsonDecode(response.body)['detail'];
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed: $error')));
      }
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  Future<void> updateContact(
    String id,
    String name,
    String phone,
    String email,
    String lineId,
    String? defaultNotificationMethod,
  ) async {
    try {
      final headers = await apiService.getHeaders();
      final body = {
        'nick_name': name,
        'phone': phone,
        'email': email,
        'line_id': lineId,
        'default_notification_method': defaultNotificationMethod ?? 'mobile',
      };

      final response = await http.put(
        Uri.parse('${ApiService.baseUrl}/contacts/$id/'),
        headers: headers,
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        if (!mounted) return;
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Contact updated successfully')));
        fetchContacts(); // Refresh list
      } else {
        if (!mounted) return;
        final error = jsonDecode(response.body)['detail'];
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed: $error')));
      }
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  void _showEditDialog(Map<String, dynamic> contact) {
    final nameController = TextEditingController(text: contact['nick_name']);
    final phoneController = TextEditingController(text: contact['phone']);
    final emailController = TextEditingController(text: contact['email']);
    final lineIdController = TextEditingController(text: contact['line_id']);
    String selectedNotificationMethod = contact['default_notification_method'] ?? 'mobile';

    final formKey = GlobalKey<FormState>();

    // Helper for cross-field validation
    String? validateContactMethod(String? value) {
      if (phoneController.text.trim().isEmpty &&
          emailController.text.trim().isEmpty &&
          lineIdController.text.trim().isEmpty) {
        return '請至少填寫一項';
      }
      return null;
    }

    showDialog(
      context: context,
      builder: (context) {
        Timer? debounceTimer;
        String? phoneError;
        String? emailError;
        String? lineError;

        return StatefulBuilder(
          builder: (context, setState) {
            void validateRealTime() {
              setState(() {
                phoneError = null;
                emailError = null;
                lineError = null;
              });

              if (debounceTimer?.isActive ?? false) debounceTimer!.cancel();
              debounceTimer = Timer(const Duration(milliseconds: 500), () async {
                final phone = phoneController.text.trim();
                final email = emailController.text.trim();
                final lineId = lineIdController.text.trim();
                
                if (phone.isEmpty && email.isEmpty && lineId.isEmpty) return;
                
                try {
                  final result = await apiService.validateContact(
                    phone, email, lineId, 
                    excludeContactId: contact['id']
                  );
                  
                  if (context.mounted && result['is_valid'] == false) {
                     setState(() {
                        final dup = result['duplicate_field'];
                        if (dup == 'phone') phoneError = '此號碼已存在';
                        else if (dup == 'email') emailError = '此Email已存在';
                        else if (dup == 'line') lineError = '此Line ID已存在';
                     });
                  }
                } catch (e) {
                  // ignore
                }
              });
            }

            return AlertDialog(
              title: Text('編輯聯絡人'),
              content: SingleChildScrollView(
                child: Form(
                  key: formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextFormField(
                        controller: nameController,
                        decoration: InputDecoration(labelText: '姓名/暱稱 *'),
                        validator: (v) => v?.trim().isEmpty == true ? '請輸入姓名' : null,
                      ),
                      SizedBox(height: 24),
                      TextFormField(
                        controller: phoneController,
                        decoration: InputDecoration(
                          labelText: '電話',
                          errorText: phoneError,
                        ),
                        keyboardType: TextInputType.phone,
                        validator: validateContactMethod,
                        onChanged: (_) => validateRealTime(),
                      ),
                      SizedBox(height: 24),
                      TextFormField(
                        controller: emailController,
                        decoration: InputDecoration(
                          labelText: 'Email (選填)',
                          errorText: emailError,
                        ),
                        keyboardType: TextInputType.emailAddress,
                        validator: (v) {
                          final emailErrorStr = FormValidators.validateEmail(v);
                          if (emailErrorStr != null) return emailErrorStr;
                          return validateContactMethod(v);
                        },
                        onChanged: (_) => validateRealTime(),
                      ),
                      SizedBox(height: 24),
                      TextFormField(
                        controller: lineIdController,
                        decoration: InputDecoration(
                          labelText: 'Line ID (選填)',
                          errorText: lineError,
                        ),
                        validator: validateContactMethod,
                        onChanged: (_) => validateRealTime(),
                      ),
                      SizedBox(height: 24),
                      DropdownButtonFormField<String>(
                        decoration: InputDecoration(labelText: '預設通知方式'),
                        value: selectedNotificationMethod,
                        items: const [
                          DropdownMenuItem(value: 'mobile', child: Text('手機簡訊')),
                          DropdownMenuItem(value: 'email', child: Text('Email')),
                          DropdownMenuItem(value: 'line', child: Text('LINE')),
                        ],
                        onChanged: (val) {
                          if (val != null) {
                            setState(() => selectedNotificationMethod = val);
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    debounceTimer?.cancel();
                    Navigator.pop(context);
                  },
                  child: Text('取消'),
                ),
                ElevatedButton(
                  onPressed: () {
                    if (phoneError != null || emailError != null || lineError != null) return;
                    if (formKey.currentState!.validate()) {
                      debounceTimer?.cancel();
                      updateContact(
                        contact['id'].toString(),
                        nameController.text.trim(),
                        phoneController.text.trim(),
                        emailController.text.trim(),
                        lineIdController.text.trim(),
                        selectedNotificationMethod,
                      );
                      Navigator.pop(context);
                    }
                  },
                  child: Text('儲存'),
                ),
              ],
            );
          }
        );
      },
    );

  }

  void _showAddDialog() {
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    final emailController = TextEditingController();
    final lineIdController = TextEditingController();
    final searchController = TextEditingController();

    // Store selected user ID from search
    String? selectedContactUserId;
    String selectedNotificationMethod = 'mobile';

    showDialog(
      context: context,
      builder: (context) {
        return DefaultTabController(
          length: 2,
          child: StatefulBuilder(
            builder: (context, setState) {
              List<dynamic> searchResults = [];
              bool isSearching = false;
              final formKey = GlobalKey<FormState>();

              Timer? debounceTimer;
              String? phoneError;
              String? emailError;
              String? lineError;

              void validateRealTime() {
                setState(() {
                  phoneError = null;
                  emailError = null;
                  lineError = null;
                });

                if (debounceTimer?.isActive ?? false) debounceTimer!.cancel();
                debounceTimer = Timer(const Duration(milliseconds: 500), () async {
                  final phone = phoneController.text.trim();
                  final email = emailController.text.trim();
                  final lineId = lineIdController.text.trim();
                  
                  if (phone.isEmpty && email.isEmpty && lineId.isEmpty) return;
                  
                  try {
                    final result = await apiService.validateContact(phone, email, lineId);
                    
                    if (context.mounted && result['is_valid'] == false) {
                       setState(() {
                          final dup = result['duplicate_field'];
                          if (dup == 'phone') phoneError = '此號碼已存在';
                          else if (dup == 'email') emailError = '此Email已存在';
                          else if (dup == 'line') lineError = '此Line ID已存在';
                       });
                    }
                  } catch (e) {
                    // ignore
                  }
                });
              }

              // Helper for cross-field validation (reused logic)
              String? validateContactMethod(String? value) {
                if (phoneController.text.trim().isEmpty &&
                    emailController.text.trim().isEmpty &&
                    lineIdController.text.trim().isEmpty) {
                  return '請至少填寫一項';
                }
                return null;
              }

              Future<void> performSearch() async {
                if (searchController.text.isEmpty) return;

                setState(() => isSearching = true);
                try {
                  final results = await apiService.searchUsers(
                    searchController.text,
                  );
                  if (!context.mounted) return;
                  setState(() {
                    searchResults = results;
                    isSearching = false;
                  });
                } catch (e) {
                  if (!context.mounted) return;
                  setState(() => isSearching = false);
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(SnackBar(content: Text('Search failed: $e')));
                }
              }

              return AlertDialog(
                title: Text('Add Contact'),
                content: Container(
                  width: double.maxFinite,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TabBar(
                        labelColor: Colors.blue,
                        unselectedLabelColor: Colors.grey,
                        tabs: [
                          Tab(text: 'Manual'),
                          Tab(text: 'Invite Friend'),
                        ],
                      ),
                      Container(
                        height: 300,
                        child: TabBarView(
                          children: [
                            // Manual Tab
                            SingleChildScrollView(
                              child: Form(
                                key: formKey, // Define this key above inside builder or StatefulBuilder
                                child: Column(
                                  children: [
                                    TextFormField(
                                      controller: nameController,
                                      decoration: InputDecoration(
                                        labelText: 'Name/Nickname *',
                                      ),
                                      validator: (v) => v?.trim().isEmpty == true ? '請輸入姓名' : null,
                                    ),
                                    SizedBox(height: 24),
                                    TextFormField(
                                      controller: phoneController,
                                      decoration: InputDecoration(
                                        labelText: 'Phone',
                                        errorText: phoneError,
                                      ),
                                      keyboardType: TextInputType.phone,
                                      validator: validateContactMethod,
                                      onChanged: (_) => validateRealTime(),
                                    ),
                                    SizedBox(height: 24),
                                    TextFormField(
                                      controller: emailController,
                                      decoration: InputDecoration(
                                        labelText: 'Email (Optional)',
                                        errorText: emailError,
                                      ),
                                      keyboardType: TextInputType.emailAddress,
                                      validator: (v) {
                                        final emailErrorStr = FormValidators.validateEmail(v);
                                        if (emailErrorStr != null) return emailErrorStr;
                                        return validateContactMethod(v);
                                      },
                                      onChanged: (_) => validateRealTime(),
                                    ),
                                    SizedBox(height: 24),
                                      TextFormField(
                                        controller: lineIdController,
                                        decoration: InputDecoration(
                                          labelText: 'Line ID (Optional)',
                                          errorText: lineError,
                                        ),
                                        validator: validateContactMethod,
                                        onChanged: (_) => validateRealTime(),
                                      ),
                                      SizedBox(height: 24),
                                      DropdownButtonFormField<String>(
                                        decoration: InputDecoration(labelText: 'Default Notification Method'),
                                        value: selectedNotificationMethod,
                                        items: const [
                                          DropdownMenuItem(value: 'mobile', child: Text('SMS Message')),
                                          DropdownMenuItem(value: 'email', child: Text('Email')),
                                          DropdownMenuItem(value: 'line', child: Text('LINE')),
                                        ],
                                        onChanged: (val) {
                                          if (val != null) {
                                            setState(() => selectedNotificationMethod = val);
                                          }
                                        },
                                      ),
                                    ],
                                  ),
                              ),
                            ),

                            // Search Tab
                            Column(
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: TextField(
                                        controller: searchController,
                                        decoration: InputDecoration(
                                          labelText: 'Phone / Email / Line ID',
                                          suffixIcon: IconButton(
                                            icon: Icon(Icons.search),
                                            onPressed: performSearch,
                                          ),
                                        ),
                                        onSubmitted: (_) => performSearch(),
                                      ),
                                    ),
                                    ],
                                  ),
                                  SizedBox(height: 10),
                                  Expanded(
                                child: isSearching
                                    ? Center(
                                        child: CircularProgressIndicator(),
                                      )
                                    : searchResults.isEmpty
                                    ? Column(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          Text('No users found'),
                                          if (searchController.text.isNotEmpty) ...[
                                            SizedBox(height: 16),
                                            ElevatedButton.icon(
                                              icon: Icon(Icons.share),
                                              label: Text('Invite "${searchController.text}" to App'),
                                              onPressed: () => _inviteFriend(searchController.text),
                                            ),
                                            Padding(
                                              padding: const EdgeInsets.all(8.0),
                                              child: Text(
                                                'Send an invitation via Email or SMS',
                                                style: TextStyle(color: Colors.grey, fontSize: 12),
                                              ),
                                            ),
                                          ]
                                        ],
                                      )
                                    : ListView.builder(
                                          shrinkWrap: true,
                                          itemCount: searchResults.length,
                                          itemBuilder: (context, index) {
                                            final user = searchResults[index];
                                            return ListTile(
                                              leading: CircleAvatar(
                                                backgroundImage:
                                                    user['profile_image_path'] !=
                                                        null
                                                    ? NetworkImage(
                                                        user['profile_image_path'],
                                                      )
                                                    : null,
                                                child:
                                                    user['profile_image_path'] ==
                                                        null
                                                    ? Text(
                                                        user['full_name']?[0] ??
                                                            '?',
                                                      )
                                                    : null,
                                              ),
                                              title: Text(
                                                user['full_name'] ?? 'Unknown',
                                              ),
                                              subtitle: Text(
                                                user['phone'] ??
                                                    user['email'] ??
                                                    '',
                                              ),
                                              onTap: () {
                                                // Auto-fill fields and switch to Manual tab
                                                nameController.text =
                                                    user['full_name'] ?? '';
                                                phoneController.text =
                                                    user['phone'] ?? '';
                                                emailController.text =
                                                    user['email'] ?? '';
                                                lineIdController.text =
                                                    user['line_id'] ?? '';

                                                // Hidden field for relation
                                                selectedContactUserId =
                                                    user['user_id']; // Ensure backend supports this if needed

                                                // Use the DefaultTabController to switch tabs - but simpler: just show a snackbar and user can verify in Manual tab
                                                // Since we can't easily switch tab programmatically without a controller, we'll just populate.

                                                ScaffoldMessenger.of(
                                                  context,
                                                ).showSnackBar(
                                                  SnackBar(
                                                    content: Text(
                                                      'Details filled from ${user['full_name']}',
                                                    ),
                                                  ),
                                                );
                                              },
                                            );
                                          },
                                        ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () {
                      debounceTimer?.cancel();
                      Navigator.pop(context);
                    },
                    child: Text('Cancel'),
                  ),
                  ElevatedButton(
                    onPressed: () {
                      if (phoneError != null || emailError != null || lineError != null) return;

                      // If form is mounted (Manual tab), validate it
                      if (formKey.currentState != null) {
                         if (formKey.currentState!.validate()) {
                            // Proceed
                         } else {
                            return; // Show errors
                         }
                      } else {
                        // We are likely on Search tab or elsewhere.
                        // Check controllers manually.
                        if (nameController.text.trim().isEmpty) {
                           ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Please enter a name')));
                           // Ideally switch to tab 0 here, but we need TabController
                           DefaultTabController.of(context).animateTo(0);
                           return;
                        }
                        // Check at least one
                         if (phoneController.text.trim().isEmpty &&
                              emailController.text.trim().isEmpty &&
                              lineIdController.text.trim().isEmpty) {
                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('請至少填寫一項聯絡方式')));
                             DefaultTabController.of(context).animateTo(0);
                            return;
                        }
                      }
                      
                      // ... Proceed to add contact ...
                      
                      addContact(
                        nameController.text.trim(),
                        phoneController.text.trim(),
                        emailController.text.trim(),
                        lineIdController.text.trim(),
                        contactUserId: selectedContactUserId,
                        defaultNotificationMethod: selectedNotificationMethod,
                      );
                      debounceTimer?.cancel();
                      Navigator.pop(context);
                    },
                    child: Text('Add'),
                  ),
                ],
              );
            },
          ),
        );
      },
    );
  }

  void _toggleSelectionMode() {
    setState(() {
      isSelectionMode = !isSelectionMode;
      if (!isSelectionMode) {
        selectedContactIds.clear();
      }
    });
  }

  void _toggleContactSelection(int id) {
    setState(() {
      if (selectedContactIds.contains(id)) {
        selectedContactIds.remove(id);
        if (selectedContactIds.isEmpty) {
          isSelectionMode = false;
        }
      } else {
        selectedContactIds.add(id);
      }
    });
  }

  Future<void> _deleteSelectedContacts() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('刪除聯絡人'),
        content: Text('確定要刪除這 ${selectedContactIds.length} 位聯絡人嗎？\n注意：這些聯絡人參與的行程記錄也會一併被刪除，此動作無法復原。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('取消'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: Text('刪除', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      setState(() => isLoading = true);
      try {
        final headers = await apiService.getHeaders();
        // Use Future.wait to delete concurrently
        final deleteFutures = selectedContactIds.map((id) {
          return http.delete(
            Uri.parse('${ApiService.baseUrl}/contacts/$id'),
            headers: headers,
          );
        });

        final responses = await Future.wait(deleteFutures);

        // CHeck if all successful (or handled individually).
        // For simplicity, if any fail, we might want to know, but we'll refresh regardless.
        if (!mounted) return;
        
        bool allSuccess = responses.every(
          (r) => r.statusCode == 200 || r.statusCode == 204,
        );

        if (allSuccess) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('成功刪除 ${selectedContactIds.length} 位聯絡人')),
          );
        } else {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('部分聯絡人刪除失敗')));
        }

        setState(() {
          isSelectionMode = false;
          selectedContactIds.clear();
        });
        fetchContacts();
      } catch (e) {
        if (!mounted) return;
        setState(() => isLoading = false);
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('刪除失敗: $e')));
      }
    }
  }

  void _deleteContact(String friendId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('刪除聯絡人'),
        content: Text('確定要刪除這位聯絡人嗎？\n注意：此聯絡人參與的行程記錄也會一併被刪除，此動作無法復原。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('取消'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: Text('刪除', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final headers = await apiService.getHeaders();
      final response = await http.delete(
        Uri.parse('${ApiService.baseUrl}/contacts/$friendId'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        fetchContacts(); // Refresh
      } else {
        throw Exception('Failed to delete');
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error removing contact')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: isSelectionMode
            ? IconButton(
                icon: Icon(Icons.close),
                onPressed: _toggleSelectionMode,
              )
            : null,
        title: Text(
          isSelectionMode ? '已選擇 ${selectedContactIds.length} 項' : '我的聯絡人',
        ),
        actions: [
          if (isSelectionMode)
            IconButton(
              icon: Icon(Icons.delete),
              onPressed: selectedContactIds.isNotEmpty
                  ? _deleteSelectedContacts
                  : null,
            )
          else
            IconButton(
              icon: Icon(
                Icons.checklist,
              ), // Or Icons.select_all / Icons.playlist_add_check
              onPressed: _toggleSelectionMode,
              tooltip: '多選刪除',
            ),
        ],
      ),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : contacts.isEmpty
          ? Center(child: Text('尚無聯絡人，點擊右下角新增'))
          : ListView.builder(
              itemCount: contacts.length,
              itemBuilder: (context, index) {
                // Re-declare contact to fix scope issue
                final contact = contacts[index];
                final id = contact['id'] as int;
                final isSelected = selectedContactIds.contains(id);

                return ListTile(
                  onLongPress: () {
                    if (!isSelectionMode) {
                      _toggleSelectionMode();
                      _toggleContactSelection(id);
                    }
                  },
                  onTap: () {
                    if (isSelectionMode) {
                      _toggleContactSelection(id);
                    } else {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => ContactHistoryScreen(contact: contact),
                        ),
                      );
                    }
                  },
                  leading: isSelectionMode
                      ? Checkbox(
                          value: isSelected,
                          onChanged: (bool? value) {
                            _toggleContactSelection(id);
                          },
                        )
                      : CircleAvatar(
                          backgroundImage: contact['profile_image_path'] != null
                              ? NetworkImage(contact['profile_image_path'])
                              : null,
                          backgroundColor: Colors.grey[200],
                          child: contact['profile_image_path'] == null
                              ? Icon(Icons.person, color: Colors.grey[500])
                              : null,
                        ),
                  title: Text(contact['nick_name'] ?? 'Unknown'),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (contact['phone'] != null && contact['phone'].isNotEmpty)
                        Text(contact['phone']),
                      if (contact['email'] != null && contact['email'].isNotEmpty)
                        Text(contact['email']),
                      SizedBox(height: 4),
                      Text(
                        '預設通知: ${_getNotificationMethodLabel(contact['default_notification_method'])}', 
                        style: TextStyle(color: Colors.blueGrey, fontSize: 12)
                      ),
                    ],
                  ),
                  trailing: isSelectionMode
                      ? null
                      : Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: Icon(Icons.edit, color: Colors.blue),
                              onPressed: () => _showEditDialog(contact),
                            ),
                            IconButton(
                              icon: Icon(Icons.delete, color: Colors.grey),
                              onPressed: () {
                                _deleteContact(contact['id'].toString());
                              },
                            ),
                          ],
                        ),
                );
              },
            ),
      floatingActionButton: isSelectionMode
          ? null
          : FloatingActionButton(
              onPressed: _showAddDialog,
              child: Icon(Icons.person_add),
            ),
    );
  }

  String _getNotificationMethodLabel(String? method) {
    if (method == 'email') return 'Email';
    if (method == 'line') return 'LINE';
    return '手機簡訊';
  }
}
