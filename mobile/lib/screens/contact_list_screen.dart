import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/api_service.dart';

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
        setState(() {
          contacts = jsonDecode(response.body);
          isLoading = false;
        });
      } else {
        throw Exception('Failed to load contacts');
      }
    } catch (e) {
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
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Contact added successfully')));
        fetchContacts(); // Refresh list
      } else {
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
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Contact updated successfully')));
        fetchContacts(); // Refresh list
      } else {
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

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('編輯聯絡人'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: InputDecoration(labelText: '姓名/暱稱'),
              ),
              TextField(
                controller: phoneController,
                decoration: InputDecoration(labelText: '電話'),
                keyboardType: TextInputType.phone,
              ),
              TextField(
                controller: emailController,
                decoration: InputDecoration(labelText: 'Email (選填)'),
                keyboardType: TextInputType.emailAddress,
              ),
              TextField(
                controller: lineIdController,
                decoration: InputDecoration(labelText: 'Line ID (選填)'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              if (nameController.text.isNotEmpty ||
                  phoneController.text.isNotEmpty) {
                updateContact(
                  contact['id'].toString(),
                  nameController.text.trim(),
                  phoneController.text.trim(),
                  emailController.text.trim(),
                  lineIdController.text.trim(),
                );
                Navigator.pop(context);
              } else {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('請至少輸入姓名或電話')));
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

              Future<void> performSearch() async {
                if (searchController.text.isEmpty) return;

                setState(() => isSearching = true);
                try {
                  final results = await apiService.searchUsers(
                    searchController.text,
                  );
                  setState(() {
                    searchResults = results;
                    isSearching = false;
                  });
                } catch (e) {
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
                              child: Column(
                                children: [
                                  TextField(
                                    controller: nameController,
                                    decoration: InputDecoration(
                                      labelText: 'Name/Nickname',
                                    ),
                                  ),
                                  TextField(
                                    controller: phoneController,
                                    decoration: InputDecoration(
                                      labelText: 'Phone',
                                    ),
                                    keyboardType: TextInputType.phone,
                                  ),
                                  TextField(
                                    controller: emailController,
                                    decoration: InputDecoration(
                                      labelText: 'Email (Optional)',
                                    ),
                                    keyboardType: TextInputType.emailAddress,
                                  ),
                                  TextField(
                                    controller: lineIdController,
                                    decoration: InputDecoration(
                                      labelText: 'Line ID (Optional)',
                                    ),
                                  ),
                                ],
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
                                      ? Center(child: Text('No users found'))
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
                      if (nameController.text.isNotEmpty ||
                          phoneController.text.isNotEmpty) {
                        // TODO: Update addContact to accept contact_user_id if needed
                        addContact(
                          nameController.text.trim(),
                          phoneController.text.trim(),
                          emailController.text.trim(),
                          lineIdController.text.trim(),
                          contactUserId: selectedContactUserId,
                        );
                        Navigator.pop(context);
                      } else {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Please enter at least Name or Phone',
                            ),
                          ),
                        );
                      }
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
                          child: Text(
                            contact['nick_name'] != null &&
                                    contact['nick_name'].isNotEmpty
                                ? contact['nick_name'][0]
                                : '?',
                          ),
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
