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
        Uri.parse('${ApiService.baseUrl}/contacts'),
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  Future<void> addContact(String email) async {
    try {
      final headers = await apiService.getHeaders();
      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/contacts'),
        headers: headers,
        body: jsonEncode({'email': email}),
      );

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Contact added successfully')),
        );
        fetchContacts(); // Refresh list
      } else {
        final error = jsonDecode(response.body)['detail'];
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $error')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  void _showAddDialog() {
    final emailController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('新增聯絡人'),
        content: TextField(
          controller: emailController,
          decoration: InputDecoration(
            labelText: '好友 Email',
            hintText: 'user@example.com',
          ),
          keyboardType: TextInputType.emailAddress,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              if (emailController.text.isNotEmpty) {
                addContact(emailController.text.trim());
                Navigator.pop(context);
              }
            },
            child: Text('新增'),
          ),
        ],
      ),
    );
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error removing contact')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('我的聯絡人'),
      ),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : contacts.isEmpty
              ? Center(child: Text('尚無聯絡人，點擊右下角新增'))
              : ListView.builder(
                  itemCount: contacts.length,
                  itemBuilder: (context, index) {
                    final contact = contacts[index];
                    return ListTile(
                      leading: CircleAvatar(
                        backgroundImage: contact['profile_picture'] != null
                            ? NetworkImage(contact['profile_picture'])
                            : null,
                        child: contact['profile_picture'] == null
                            ? Icon(Icons.person)
                            : null,
                      ),
                      title: Text(contact['full_name'] ?? 'Unknown User'),
                      subtitle: Text(contact['email']),
                      trailing: IconButton(
                        icon: Icon(Icons.delete, color: Colors.grey),
                        onPressed: () {
                          // Confirm dialog could be added here
                          _deleteContact(contact['id']);
                        },
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddDialog,
        child: Icon(Icons.person_add),
      ),
    );
  }
}
