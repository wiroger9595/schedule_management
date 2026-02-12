import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/api_service.dart';

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

class _AttendeeSelectorState extends State<AttendeeSelector> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final ApiService apiService = ApiService();
  
  // Data
  List<dynamic> _allContacts = [];
  List<dynamic> _selectedContacts = [];
  bool _isLoadingContacts = true;
  
  // New Contact Form
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _lineIdController = TextEditingController();
  bool _isCreating = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _selectedContacts = List.from(widget.initialSelectedContacts);
    _fetchContacts();
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _lineIdController.dispose();
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
            _isLoadingContacts = false;
          });
        }
      } else {
        print('Failed to load contacts: ${response.statusCode}');
        if (mounted) setState(() => _isLoadingContacts = false);
      }
    } catch (e) {
      print('Error loading contacts: $e');
      if (mounted) setState(() => _isLoadingContacts = false);
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

  Future<void> _createContact() async {
    if (!_formKey.currentState!.validate()) return;
    
    // Validate at least one contact method
    if (_phoneController.text.isEmpty && _emailController.text.isEmpty && _lineIdController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('請至少輸入電話、Email 或 Line ID 其中一項')),
      );
      return;
    }

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
            
            // Switch to list tab
            _tabController.animateTo(0);
          });
          
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('聯絡人建立成功並已選取')),
          );
        }
      } else {
        throw Exception('Failed: ${response.body}');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isCreating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('建立失敗: $e')),
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
              '選擇參與者',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
          ),
          
          // Tabs
          TabBar(
            controller: _tabController,
            labelColor: Theme.of(context).primaryColor,
            unselectedLabelColor: Colors.grey,
            tabs: [
              Tab(text: '選擇聯絡人'),
              Tab(text: '新增聯絡人'),
            ],
          ),
          
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                // Tab 1: List
                _buildContactList(),
                
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
                    child: Text('取消'),
                  ),
                ),
                SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      widget.onSelectionChanged(_selectedContacts);
                      Navigator.pop(context);
                    },
                    child: Text('完成 (${_selectedContacts.length})'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContactList() {
    if (_isLoadingContacts) {
      return Center(child: CircularProgressIndicator());
    }
    
    if (_allContacts.isEmpty) {
      return Center(child: Text('尚無聯絡人，請由右側分頁新增'));
    }

    return ListView.builder(
      itemCount: _allContacts.length,
      itemBuilder: (context, index) {
        final contact = _allContacts[index];
        final id = contact['id'];
        final isSelected = _selectedContacts.any((c) => c['id'] == id);

        return ListTile(
          leading: CircleAvatar(
            child: Text(
              (contact['nick_name'] ?? contact['name'] ?? '?')[0].toUpperCase(),
            ),
          ),
          title: Text(contact['nick_name'] ?? contact['name'] ?? 'Unknown'),
          subtitle: Text(contact['phone'] ?? contact['email'] ?? ''),
          trailing: Checkbox(
            value: isSelected,
            onChanged: (val) => _toggleSelection(contact),
          ),
          onTap: () => _toggleSelection(contact),
        );
      },
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
                labelText: '姓名/暱稱 *',
                prefixIcon: Icon(Icons.person),
                border: OutlineInputBorder(),
              ),
              validator: (v) => v?.trim().isEmpty == true ? '請輸入姓名' : null,
            ),
            SizedBox(height: 16),
            TextFormField(
              controller: _phoneController,
              decoration: InputDecoration(
                labelText: '電話',
                prefixIcon: Icon(Icons.phone),
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.phone,
            ),
            SizedBox(height: 16),
            TextFormField(
              controller: _emailController,
              decoration: InputDecoration(
                labelText: 'Email',
                prefixIcon: Icon(Icons.email),
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.emailAddress,
            ),
            SizedBox(height: 16),
            TextFormField(
              controller: _lineIdController,
              decoration: InputDecoration(
                labelText: 'Line ID',
                prefixIcon: Icon(Icons.chat),
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                icon: _isCreating 
                    ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : Icon(Icons.save),
                label: Text(_isCreating ? '儲存中...' : '儲存並選取'),
                onPressed: _isCreating ? null : _createContact,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
