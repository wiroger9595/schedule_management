import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import '../services/api_service.dart';
import '../utils/form_validators.dart';

class AttendeeSelector extends StatefulWidget {
  final List<dynamic> initialSelectedContacts;
  final Function(List<dynamic>) onSelectionChanged;

  const AttendeeSelector({
    Key? key,
    this.initialSelectedContacts = const [],
    required this.onSelectionChanged,
  }) : super(key: key);

  @override
  _AttendeeSelectorState createState() => _AttendeeSelectorState();
}

class _AttendeeSelectorState extends State<AttendeeSelector>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final ApiService apiService = ApiService();

  // Data
  List<dynamic> _allContacts = [];
  List<dynamic> _selectedContacts = [];

  // User search
  final TextEditingController _userSearchCtrl = TextEditingController();
  List<dynamic> _userSearchResults = [];
  bool _isSearchingUsers = false;
  bool _hasSearchedUsers = false;
  String? _addingUserId;

  // New Contact Form
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _lineIdController = TextEditingController();
  bool _isCreating = false;

  // Validation
  Timer? _debounceTimer;
  String? _phoneError;
  String? _emailError;
  String? _lineError;

  String? _validateContactMethod(String? value) {
    if (_phoneController.text.trim().isEmpty &&
        _emailController.text.trim().isEmpty &&
        _lineIdController.text.trim().isEmpty) {
      return 'phoneEmailRequired'.tr();
    }
    return null;
  }

  void _validateRealTime() {
    setState(() {
      _phoneError = null;
      _emailError = null;
      _lineError = null;
    });

    if (_debounceTimer?.isActive ?? false) _debounceTimer!.cancel();

    _debounceTimer = Timer(const Duration(milliseconds: 500), () async {
      final phone = _phoneController.text.trim();
      final email = _emailController.text.trim();
      final lineId = _lineIdController.text.trim();

      if (phone.isEmpty && email.isEmpty && lineId.isEmpty) return;

      try {
        final result = await apiService.validateContact(phone, email, lineId);

        if (mounted && result['is_valid'] == false) {
          setState(() {
            final dup = result['duplicate_field'];
            if (dup == 'phone')
              _phoneError = 'phoneExists'.tr();
            else if (dup == 'email')
              _emailError = 'emailExists'.tr();
            else if (dup == 'line') _lineError = 'lineExists'.tr();
          });
        }
      } catch (e) {
        // ignore
      }
    });
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _selectedContacts = List.from(widget.initialSelectedContacts);
    _fetchContacts();
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _tabController.dispose();
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _lineIdController.dispose();
    _userSearchCtrl.dispose();
    super.dispose();
  }

  Future<void> _fetchContacts() async {
    try {
      final headers = await apiService.getHeaders();
      final response = await http.get(
        Uri.parse('${ApiService.baseUrl}/contacts/'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _allContacts = jsonDecode(response.body);
          });
        }
      } else {
        debugPrint('Failed to load contacts: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error loading contacts: $e');
    }
  }

  void _toggleSelection(dynamic contact) {
    setState(() {
      final id = contact['id'];
      final existingIndex = _selectedContacts.indexWhere((c) => c['id'] == id);

      if (existingIndex >= 0) {
        _selectedContacts.removeAt(existingIndex);
      } else {
        _selectedContacts.add(contact);
      }
      widget.onSelectionChanged(_selectedContacts);
    });
  }

  Future<void> _searchUsers() async {
    final q = _userSearchCtrl.text.trim();
    if (q.isEmpty) {
      setState(() {
        _userSearchResults = [];
        _hasSearchedUsers = false;
      });
      return;
    }
    setState(() => _isSearchingUsers = true);
    try {
      final results = await apiService.searchUsers(q);
      if (mounted) {
        setState(() {
          _userSearchResults = results;
          _hasSearchedUsers = true;
          _isSearchingUsers = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isSearchingUsers = false);
    }
  }

  bool _isUserSelected(Map<String, dynamic> user) {
    final userId = user['user_id'] as String?;
    final email = user['email'] as String?;
    return _selectedContacts.any((c) =>
        c['contact_user_id'] == userId ||
        (email != null && email.isNotEmpty && c['email'] == email));
  }

  Future<void> _addSearchedUser(Map<String, dynamic> user) async {
    if (_isUserSelected(user)) return;
    final userId = user['user_id'] as String?;
    final email = user['email'] as String?;

    final existing = _allContacts.firstWhere(
      (c) =>
          c['contact_user_id'] == userId ||
          (email != null && email.isNotEmpty && c['email'] == email),
      orElse: () => null,
    );
    if (existing != null) {
      setState(() {
        _selectedContacts.add(existing);
        widget.onSelectionChanged(_selectedContacts);
      });
      return;
    }

    setState(() => _addingUserId = userId);
    try {
      final newContact = await apiService.createContact(
        (user['full_name'] as String?) ?? '',
        '',
        email ?? '',
        '',
        contactUserId: userId,
      );
      if (mounted) {
        setState(() {
          _allContacts.add(newContact);
          _selectedContacts.add(newContact);
          widget.onSelectionChanged(_selectedContacts);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('createFailed'.tr(namedArgs: {'error': e.toString()}))),
        );
      }
    } finally {
      if (mounted) setState(() => _addingUserId = null);
    }
  }

  Future<void> _createContact() async {
    if (!_formKey.currentState!.validate()) return;

    // Validation is now handled by the Form fields directly
    // Force validation to show errors if fields are empty
    // if (!_formKey.currentState!.validate()) return; is already at the top

    setState(() => _isCreating = true);

    try {
      final headers = await apiService.getHeaders();
      final body = {
        'nick_name': _nameController.text.trim(),
        'phone': _phoneController.text.trim(),
        'email': _emailController.text.trim(),
        'line_id': _lineIdController.text.trim(),
      };

      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/contacts/'),
        headers: headers,
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        final newContact = jsonDecode(response.body);

        // Refresh list and auto-select
        await _fetchContacts();

        if (mounted) {
          setState(() {
            _selectedContacts.add(newContact);
            widget.onSelectionChanged(_selectedContacts);

            // Reset form
            _nameController.clear();
            _phoneController.clear();
            _emailController.clear();
            _lineIdController.clear();
            _isCreating = false;
          });

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('contactCreatedSelected'.tr())),
          );
        }
      } else {
        throw Exception('Failed: ${response.body}');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isCreating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('createFailed'.tr(namedArgs: {'error': e.toString()}))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.75,
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
      ),
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              'selectParticipants'.tr(),
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
          ),

          // Selected attendees
          if (_selectedContacts.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: _selectedContacts.map((c) {
                    final name = (c['nick_name'] as String?)?.isNotEmpty == true
                        ? c['nick_name'] as String
                        : (c['email'] as String?) ?? '?';
                    return Chip(
                      label: Text(name, style: TextStyle(fontSize: 12)),
                      onDeleted: () => _toggleSelection(c),
                      deleteIconColor: Colors.red[700],
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      padding: EdgeInsets.symmetric(horizontal: 4),
                    );
                  }).toList(),
                ),
              ),
            ),
          if (_selectedContacts.isNotEmpty) SizedBox(height: 8),

          // Tabs
          TabBar(
            controller: _tabController,
            labelColor: Theme.of(context).primaryColor,
            unselectedLabelColor: Colors.grey,
            tabs: [
              Tab(text: 'searchUsers'.tr()),
              Tab(text: 'addContact'.tr()),
            ],
          ),

          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                // Tab 1: Search registered users
                _buildUserSearchTab(),

                // Tab 2: Create Form
                _buildCreateForm(),
              ],
            ),
          ),

          // Action Buttons
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text('cancel'.tr()),
                  ),
                ),
                SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      widget.onSelectionChanged(_selectedContacts);
                      Navigator.pop(context);
                    },
                    child: Text('doneCount'.tr(namedArgs: {'count': _selectedContacts.length.toString()})),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildUserSearchTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _userSearchCtrl,
                  decoration: InputDecoration(
                    hintText: 'searchUsersHint'.tr(),
                    isDense: true,
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    border:
                        OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onSubmitted: (_) => _searchUsers(),
                ),
              ),
              SizedBox(width: 8),
              _isSearchingUsers
                  ? SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : IconButton(
                      onPressed: _searchUsers,
                      icon: Icon(Icons.search),
                    ),
            ],
          ),
          SizedBox(height: 12),
          Expanded(
            child: _userSearchResults.isEmpty
                ? Center(
                    child: Text(
                      _hasSearchedUsers ? 'usersNotFound'.tr() : '',
                      style: TextStyle(color: Colors.grey),
                    ),
                  )
                : ListView.builder(
                    itemCount: _userSearchResults.length,
                    itemBuilder: (context, index) {
                      final user =
                          _userSearchResults[index] as Map<String, dynamic>;
                      final name = (user['full_name'] as String?) ?? '';
                      final email = (user['email'] as String?) ?? '';
                      final userId = user['user_id'] as String?;
                      final selected = _isUserSelected(user);
                      final adding = _addingUserId == userId;

                      return ListTile(
                        leading: CircleAvatar(
                          backgroundImage: user['profile_image_path'] != null
                              ? NetworkImage(user['profile_image_path'])
                              : null,
                          backgroundColor: Colors.grey[200],
                          child: user['profile_image_path'] == null
                              ? Icon(Icons.person, color: Colors.grey[500])
                              : null,
                        ),
                        title: Text(name.isNotEmpty ? name : email),
                        subtitle: name.isNotEmpty ? Text(email) : null,
                        trailing: adding
                            ? SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2))
                            : selected
                                ? Icon(Icons.check_circle, color: Colors.green)
                                : IconButton(
                                    icon: Icon(Icons.add_circle_outline),
                                    onPressed: () => _addSearchedUser(user),
                                  ),
                        onTap: (adding || selected)
                            ? null
                            : () => _addSearchedUser(user),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildCreateForm() {
    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Form(
        key: _formKey,
        child: Column(
          children: [
            TextFormField(
              controller: _nameController,
              decoration: InputDecoration(
                labelText: 'enterName'.tr(),
                prefixIcon: Icon(Icons.person),
                border: OutlineInputBorder(),
              ),
              validator: (v) => v?.trim().isEmpty == true ? 'enterName'.tr() : null,
            ),
            SizedBox(height: 16),
            TextFormField(
              controller: _phoneController,
              decoration: InputDecoration(
                labelText: 'phone'.tr(),
                prefixIcon: Icon(Icons.phone),
                border: OutlineInputBorder(),
                errorText: _phoneError,
              ),
              keyboardType: TextInputType.phone,
              validator: _validateContactMethod,
              onChanged: (_) => _validateRealTime(),
            ),
            SizedBox(height: 16),
            TextFormField(
              controller: _emailController,
              decoration: InputDecoration(
                labelText: 'Email',
                prefixIcon: Icon(Icons.email),
                border: OutlineInputBorder(),
                errorText: _emailError,
              ),
              keyboardType: TextInputType.emailAddress,
              validator: (value) {
                final emailError = FormValidators.validateEmail(value);
                if (emailError != null) return emailError;
                return _validateContactMethod(value);
              },
              onChanged: (_) => _validateRealTime(),
            ),
            SizedBox(height: 16),
            TextFormField(
              controller: _lineIdController,
              decoration: InputDecoration(
                labelText: 'Line ID',
                prefixIcon: Icon(Icons.chat),
                border: OutlineInputBorder(),
                errorText: _lineError,
              ),
              validator: _validateContactMethod,
              onChanged: (_) => _validateRealTime(),
            ),
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                icon: _isCreating
                    ? SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : Icon(Icons.save),
                label: Text(_isCreating ? 'saving'.tr() : 'saveAndSelect'.tr()),
                onPressed: _isCreating ? null : _createContact,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
