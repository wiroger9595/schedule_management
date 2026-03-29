import 'package:easy_localization/easy_localization.dart';
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
    final String inviteBody =
        'Hey! I use this app to manage my schedules. Join me here: https://example.com/download';

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
        .map((e) =>
            '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}')
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
    final formKey = GlobalKey<FormState>();

    // 狀態變數宣告在 builder 外，避免 setState 時重置
    String selectedNotificationMethod =
        contact['default_notification_method'] ?? 'mobile';
    Timer? debounceTimer;
    String? phoneError;
    String? emailError;
    String? lineError;

    String? validateContactMethod(String? value) {
      if (phoneController.text.trim().isEmpty &&
          emailController.text.trim().isEmpty &&
          lineIdController.text.trim().isEmpty) {
        return 'phoneOrEmailHint'.tr();
      }
      return null;
    }

    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(builder: (context, setState) {
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
                    excludeContactId: contact['id']);

                if (context.mounted && result['is_valid'] == false) {
                  setState(() {
                    final dup = result['duplicate_field'];
                    if (dup == 'phone') {
                      phoneError = 'phoneExists'.tr();
                    } else if (dup == 'email') {
                      emailError = 'emailExists'.tr();
                    } else if (dup == 'line') {
                      lineError = 'lineExists'.tr();
                    }
                  });
                }
              } catch (_) {}
            });
          }

          return Dialog(
            insetPadding:
                const EdgeInsets.symmetric(horizontal: 20, vertical: 40),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('editContact'.tr(),
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 16),
                  SingleChildScrollView(
                    child: Form(
                      key: formKey,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          TextFormField(
                            controller: nameController,
                            decoration: InputDecoration(
                              labelText: 'enterName'.tr(),
                              border: const OutlineInputBorder(),
                            ),
                            textInputAction: TextInputAction.next,
                            validator: (v) =>
                                v?.trim().isEmpty == true ? 'enterName'.tr() : null,
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: phoneController,
                            decoration: InputDecoration(
                              labelText: '電話',
                              border: const OutlineInputBorder(),
                              errorText: phoneError,
                            ),
                            keyboardType: TextInputType.phone,
                            textInputAction: TextInputAction.next,
                            validator: validateContactMethod,
                            onChanged: (_) => validateRealTime(),
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: emailController,
                            decoration: InputDecoration(
                              labelText: 'Email（選填）',
                              border: const OutlineInputBorder(),
                              errorText: emailError,
                            ),
                            keyboardType: TextInputType.emailAddress,
                            textInputAction: TextInputAction.next,
                            validator: (v) {
                              final err = FormValidators.validateEmail(v);
                              if (err != null) return err;
                              return validateContactMethod(v);
                            },
                            onChanged: (_) => validateRealTime(),
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: lineIdController,
                            decoration: InputDecoration(
                              labelText: 'lineOptional'.tr(),
                              border: const OutlineInputBorder(),
                              errorText: lineError,
                            ),
                            textInputAction: TextInputAction.next,
                            validator: validateContactMethod,
                            onChanged: (_) => validateRealTime(),
                          ),
                          const SizedBox(height: 16),
                          DropdownButtonFormField<String>(
                            decoration: InputDecoration(
                              labelText: 'defaultNotificationMethod'.tr(),
                              border: const OutlineInputBorder(),
                            ),
                            value: selectedNotificationMethod,
                            items: [
                              DropdownMenuItem(
                                  value: 'mobile', child: Text('notificationSMS'.tr())),
                              DropdownMenuItem(
                                  value: 'email', child: Text('notificationEmail'.tr())),
                              DropdownMenuItem(
                                  value: 'line', child: Text('notificationLine'.tr())),
                            ],
                            onChanged: (val) {
                              if (val != null) {
                                setState(() => selectedNotificationMethod = val);
                              }
                            },
                          ),
                          const SizedBox(height: 8),
                        ],
                      ),
                    ),
                  ),
                  const Divider(height: 1),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () {
                          debounceTimer?.cancel();
                          Navigator.pop(context);
                        },
                        child: Text('cancel'.tr()),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: () {
                          if (phoneError != null ||
                              emailError != null ||
                              lineError != null) return;
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
                        child: Text('save'.tr()),
                      ),
                      const SizedBox(width: 4),
                    ],
                  ),
                ],
              ),
            ),
          );
        });
      },
    );
  }

  void _showAddDialog() {
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    final emailController = TextEditingController();
    final lineIdController = TextEditingController();
    final searchController = TextEditingController();
    final formKey = GlobalKey<FormState>();

    // 所有狀態變數宣告在 builder 外，避免 setState 時重置
    String? selectedContactUserId;
    String selectedNotificationMethod = 'mobile';
    String? lastCheckedEmail;
    bool emailMatchDialogShowing = false;
    Timer? debounceTimer;
    String? phoneError;
    String? emailError;
    String? lineError;
    List<dynamic> searchResults = [];
    bool isSearching = false;

    showDialog(
      context: context,
      builder: (context) {
        return DefaultTabController(
          length: 2,
          child: StatefulBuilder(
            builder: (context, setState) {
              void validateRealTime() {
                setState(() {
                  phoneError = null;
                  emailError = null;
                  lineError = null;
                });

                if (debounceTimer?.isActive ?? false) debounceTimer!.cancel();
                debounceTimer =
                    Timer(const Duration(milliseconds: 600), () async {
                  final phone = phoneController.text.trim();
                  final email = emailController.text.trim();
                  final lineId = lineIdController.text.trim();

                  if (phone.isEmpty && email.isEmpty && lineId.isEmpty) return;

                  // 1. 重複聯絡人驗證
                  try {
                    final result =
                        await apiService.validateContact(phone, email, lineId);
                    if (context.mounted && result['is_valid'] == false) {
                      setState(() {
                        final dup = result['duplicate_field'];
                        if (dup == 'phone')
                          phoneError = 'phoneExists'.tr();
                        else if (dup == 'email')
                          emailError = 'emailExists'.tr();
                        else if (dup == 'line') lineError = 'lineExists'.tr();
                      });
                    }
                  } catch (_) {}

                  // 2. email 完整時查找是否為已註冊用戶
                  if (email.isNotEmpty &&
                      email.contains('@') &&
                      email.contains('.') &&
                      email != lastCheckedEmail &&
                      !emailMatchDialogShowing) {
                    lastCheckedEmail = email;
                    if (selectedContactUserId != null) {
                      setState(() => selectedContactUserId = null);
                    }

                    try {
                      final userResult =
                          await apiService.checkEmailUser(email);
                      if (!context.mounted) return;

                      if (userResult['found'] == true) {
                        emailMatchDialogShowing = true;
                        final confirmed = await showDialog<bool>(
                          context: context,
                          barrierDismissible: false,
                          builder: (ctx) => AlertDialog(
                            title: Row(
                              children: [
                                Icon(Icons.person_search,
                                    color: Colors.black87, size: 22),
                                SizedBox(width: 8),
                                Text('foundUser'.tr()),
                              ],
                            ),
                            content: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('thisEmailIsUser'.tr()),
                                SizedBox(height: 10),
                                ListTile(
                                  contentPadding: EdgeInsets.zero,
                                  leading: CircleAvatar(
                                    child: Text(
                                      (userResult['full_name'] as String? ??
                                              '?')[0]
                                          .toUpperCase(),
                                    ),
                                  ),
                                  title: Text(
                                    userResult['full_name'] ?? '',
                                    style:
                                        TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  subtitle: Text(email),
                                ),
                                SizedBox(height: 8),
                                Text('isKnownUser'.tr(),
                                    style: TextStyle(
                                        color: Colors.grey[600],
                                        fontSize: 13)),
                              ],
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(ctx, false),
                                child: Text('dontKnow'.tr()),
                              ),
                              ElevatedButton(
                                onPressed: () => Navigator.pop(ctx, true),
                                child: Text('linkUser'.tr()),
                              ),
                            ],
                          ),
                        );

                        emailMatchDialogShowing = false;
                        if (!context.mounted) return;

                        if (confirmed == true) {
                          setState(() {
                            selectedContactUserId = userResult['user_id'];
                            if (nameController.text.trim().isEmpty) {
                              nameController.text =
                                  userResult['full_name'] ?? '';
                            }
                          });
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                  'linkedWithUser'.tr(namedArgs: {'name': userResult['full_name'] ?? ''})),
                              backgroundColor: Colors.green,
                            ),
                          );
                        }
                      }
                    } catch (_) {
                      emailMatchDialogShowing = false;
                    }
                  }
                });
              }

              // Helper for cross-field validation (reused logic)
              String? validateContactMethod(String? value) {
                if (phoneController.text.trim().isEmpty &&
                    emailController.text.trim().isEmpty) {
                  return 'phoneEmailRequired'.tr();
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

              final screenHeight = MediaQuery.of(context).size.height;

              return Dialog(
                insetPadding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 40),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('addContact'.tr(),
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 12),
                      TabBar(
                        labelColor: Colors.black,
                        unselectedLabelColor: Colors.grey,
                        indicatorColor: Colors.black,
                        tabs: [
                          Tab(text: 'manualEntry'.tr()),
                          Tab(text: 'searchUser'.tr()),
                        ],
                      ),
                      SizedBox(
                        height: screenHeight * 0.55,
                        child: TabBarView(
                          children: [
                            // Manual Tab
                            SingleChildScrollView(
                              padding: const EdgeInsets.only(top: 16),
                              child: Form(
                                key: formKey,
                                child: Column(
                                  children: [
                                    Container(
                                      width: double.infinity,
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 12, vertical: 8),
                                      decoration: BoxDecoration(
                                        color: Colors.amber[50],
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(
                                            color: Colors.amber[300]!),
                                      ),
                                      child: Row(
                                        children: [
                                          const Icon(Icons.info_outline,
                                              size: 16, color: Colors.black54),
                                          const SizedBox(width: 8),
                                          Text('phoneOrEmailHint'.tr(),
                                              style: const TextStyle(
                                                  fontSize: 13,
                                                  color: Colors.black87)),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(height: 16),
                                    TextFormField(
                                      controller: nameController,
                                      decoration: InputDecoration(
                                        labelText: 'enterName'.tr(),
                                        border: const OutlineInputBorder(),
                                      ),
                                      textInputAction: TextInputAction.next,
                                      validator: (v) =>
                                          v?.trim().isEmpty == true
                                              ? 'enterName'.tr()
                                              : null,
                                    ),
                                    const SizedBox(height: 16),
                                    TextFormField(
                                      controller: phoneController,
                                      decoration: InputDecoration(
                                        labelText: 'phoneStar'.tr(),
                                        border: const OutlineInputBorder(),
                                        errorText: phoneError,
                                      ),
                                      keyboardType: TextInputType.phone,
                                      textInputAction: TextInputAction.next,
                                      validator: validateContactMethod,
                                      onChanged: (_) => validateRealTime(),
                                    ),
                                    const SizedBox(height: 16),
                                    TextFormField(
                                      controller: emailController,
                                      decoration: InputDecoration(
                                        labelText: 'emailStar'.tr(),
                                        border: const OutlineInputBorder(),
                                        errorText: emailError,
                                        suffixIcon:
                                            selectedContactUserId != null
                                                ? Tooltip(
                                                    message: 'linkedWithUser'.tr(namedArgs: {'name': ''}),
                                                    child: Icon(
                                                        Icons.verified_user,
                                                        color: Colors.green),
                                                  )
                                                : null,
                                      ),
                                      keyboardType: TextInputType.emailAddress,
                                      textInputAction: TextInputAction.next,
                                      validator: (v) {
                                        final err =
                                            FormValidators.validateEmail(v);
                                        if (err != null) return err;
                                        return validateContactMethod(v);
                                      },
                                      onChanged: (val) {
                                        if (val.trim().isEmpty) {
                                          setState(() {
                                            selectedContactUserId = null;
                                            lastCheckedEmail = null;
                                          });
                                        }
                                        validateRealTime();
                                      },
                                    ),
                                    const SizedBox(height: 16),
                                    TextFormField(
                                      controller: lineIdController,
                                      decoration: InputDecoration(
                                        labelText: 'lineOptional'.tr(),
                                        border: const OutlineInputBorder(),
                                        errorText: lineError,
                                      ),
                                      textInputAction: TextInputAction.next,
                                      validator: validateContactMethod,
                                      onChanged: (_) => validateRealTime(),
                                    ),
                                    const SizedBox(height: 16),
                                    DropdownButtonFormField<String>(
                                      decoration: InputDecoration(
                                        labelText: 'defaultNotificationMethod'.tr(),
                                        border: const OutlineInputBorder(),
                                      ),
                                      value: selectedNotificationMethod,
                                      items: [
                                        DropdownMenuItem(
                                            value: 'mobile',
                                            child: Text('notificationSMS'.tr())),
                                        DropdownMenuItem(
                                            value: 'email',
                                            child: Text('notificationEmail'.tr())),
                                        DropdownMenuItem(
                                            value: 'line',
                                            child: Text('notificationLine'.tr())),
                                      ],
                                      onChanged: (val) {
                                        if (val != null) {
                                          setState(() =>
                                              selectedNotificationMethod = val);
                                        }
                                      },
                                    ),
                                    const SizedBox(height: 8),
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
                                              mainAxisAlignment:
                                                  MainAxisAlignment.center,
                                              children: [
                                                Text('No users found'),
                                                if (searchController
                                                    .text.isNotEmpty) ...[
                                                  SizedBox(height: 16),
                                                  ElevatedButton.icon(
                                                    icon: Icon(Icons.share),
                                                    label: Text(
                                                        'Invite "${searchController.text}" to App'),
                                                    onPressed: () =>
                                                        _inviteFriend(
                                                            searchController
                                                                .text),
                                                  ),
                                                  Padding(
                                                    padding:
                                                        const EdgeInsets.all(
                                                            8.0),
                                                    child: Text(
                                                      'Send an invitation via Email or SMS',
                                                      style: TextStyle(
                                                          color: Colors.grey,
                                                          fontSize: 12),
                                                    ),
                                                  ),
                                                ]
                                              ],
                                            )
                                          : ListView.builder(
                                              shrinkWrap: true,
                                              itemCount: searchResults.length,
                                              itemBuilder: (context, index) {
                                                final user =
                                                    searchResults[index];
                                                return ListTile(
                                                  leading: CircleAvatar(
                                                    backgroundImage:
                                                        user['profile_image_path'] !=
                                                                null
                                                            ? NetworkImage(
                                                                user[
                                                                    'profile_image_path'],
                                                              )
                                                            : null,
                                                    child:
                                                        user['profile_image_path'] ==
                                                                null
                                                            ? Text(
                                                                user['full_name']
                                                                        ?[0] ??
                                                                    '?',
                                                              )
                                                            : null,
                                                  ),
                                                  title: Text(
                                                    user['full_name'] ??
                                                        'Unknown',
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
                                                    selectedContactUserId = user[
                                                        'user_id']; // Ensure backend supports this if needed

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
                      // ── 底部按鈕區 ──
                      const Divider(height: 1),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          TextButton(
                            onPressed: () {
                              debounceTimer?.cancel();
                              Navigator.pop(context);
                            },
                            child: Text('cancel'.tr()),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: () {
                              if (phoneError != null ||
                                  emailError != null ||
                                  lineError != null) return;

                              if (formKey.currentState != null) {
                                if (!formKey.currentState!.validate()) return;
                              } else {
                                if (nameController.text.trim().isEmpty) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('enterName'.tr())));
                                  DefaultTabController.of(context).animateTo(0);
                                  return;
                                }
                                if (phoneController.text.trim().isEmpty &&
                                    emailController.text.trim().isEmpty) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                          content: Text('phoneEmailRequired'.tr())));
                                  DefaultTabController.of(context).animateTo(0);
                                  return;
                                }
                              }

                              addContact(
                                nameController.text.trim(),
                                phoneController.text.trim(),
                                emailController.text.trim(),
                                lineIdController.text.trim(),
                                contactUserId: selectedContactUserId,
                                defaultNotificationMethod:
                                    selectedNotificationMethod,
                              );
                              debounceTimer?.cancel();
                              Navigator.pop(context);
                            },
                            child: Text('add'.tr()),
                          ),
                          const SizedBox(width: 4),
                        ],
                      ),
                    ],
                  ),
                ),
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
        title: Text('deleteContact'.tr()),
        content: Text(
            '確定要刪除這 ${selectedContactIds.length} 位聯絡人嗎？\n注意：這些聯絡人參與的行程記錄也會一併被刪除，此動作無法復原。'),
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
          ).showSnackBar(SnackBar(content: Text('someDeleteFailed'.tr())));
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
        title: Text('deleteContact'.tr()),
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
          isSelectionMode ? 'selectedCount'.tr(namedArgs: {'count': selectedContactIds.length.toString()}) : 'myContacts'.tr(),
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
              tooltip: 'deleteSelected'.tr(),
            ),
        ],
      ),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : contacts.isEmpty
              ? Center(child: Text('noContacts'.tr()))
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
                              builder: (context) =>
                                  ContactHistoryScreen(contact: contact),
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
                              backgroundImage: contact['profile_image_path'] !=
                                      null
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
                          SizedBox(height: 4),
                          Text(
                              '預設通知: ${_getNotificationMethodLabel(contact['default_notification_method'])}',
                              style: TextStyle(
                                  color: Colors.grey[600], fontSize: 12)),
                        ],
                      ),
                      trailing: isSelectionMode
                          ? null
                          : Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: Icon(Icons.edit, color: Colors.black87),
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
    return 'notificationSMS'.tr();
  }
}
