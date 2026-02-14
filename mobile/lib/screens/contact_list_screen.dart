import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:url_launcher/url_launcher.dart';
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
  }) async {
    try {
      final headers = await apiService.getHeaders();
      final body = {
        'nick_name': name,
        'phone': phone,
        'email': email,
        'line_id': lineId,
        'contact_user_id': contactUserId,
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
  ) async {
    try {
      final headers = await apiService.getHeaders();
      final body = {
        'nick_name': name,
        'phone': phone,
        'email': email,
        'line_id': lineId,
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
      builder: (context) => AlertDialog(
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
                  decoration: InputDecoration(labelText: '電話'),
                  keyboardType: TextInputType.phone,
                  validator: validateContactMethod,
                  onChanged: (_) => setState((){}),
                ),
                SizedBox(height: 24),
                TextFormField(
                  controller: emailController,
                  decoration: InputDecoration(labelText: 'Email (選填)'),
                  keyboardType: TextInputType.emailAddress,
                  validator: (v) {
                    final emailError = FormValidators.validateEmail(v);
                    if (emailError != null) return emailError;
                    return validateContactMethod(v);
                  },
                  onChanged: (_) => setState((){}),
                ),
                SizedBox(height: 24),
                TextFormField(
                  controller: lineIdController,
                  decoration: InputDecoration(labelText: 'Line ID (選填)'),
                  validator: validateContactMethod,
                  onChanged: (_) => setState((){}),
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              if (formKey.currentState!.validate()) {
                updateContact(
                  contact['id'].toString(),
                  nameController.text.trim(),
                  phoneController.text.trim(),
                  emailController.text.trim(),
                  lineIdController.text.trim(),
                );
                Navigator.pop(context);
              }
            },
            child: Text('儲存'),
          ),
        ],
      ),
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
                                      ),
                                      keyboardType: TextInputType.phone,
                                      validator: validateContactMethod,
                                      onChanged: (_) => setState((){}),
                                    ),
                                    SizedBox(height: 24),
                                    TextFormField(
                                      controller: emailController,
                                      decoration: InputDecoration(
                                        labelText: 'Email (Optional)',
                                      ),
                                      keyboardType: TextInputType.emailAddress,
                                      validator: (v) {
                                        final emailError = FormValidators.validateEmail(v);
                                        if (emailError != null) return emailError;
                                        return validateContactMethod(v);
                                      },
                                      onChanged: (_) => setState((){}),
                                    ),
                                    SizedBox(height: 24),
                                    TextFormField(
                                      controller: lineIdController,
                                      decoration: InputDecoration(
                                        labelText: 'Line ID (Optional)',
                                      ),
                                      validator: validateContactMethod,
                                      onChanged: (_) => setState((){}),
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
                    onPressed: () => Navigator.pop(context),
                    child: Text('Cancel'),
                  ),
                  ElevatedButton(
                    onPressed: () {
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
                      );
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
        content: Text('確定要刪除這 ${selectedContactIds.length} 位聯絡人嗎？此動作無法復原。'),
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
                      if (contact['phone'] != null &&
                          contact['phone'].isNotEmpty)
                        Text(contact['phone']),
                      if (contact['email'] != null &&
                          contact['email'].isNotEmpty)
                        Text(contact['email']),
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
}
