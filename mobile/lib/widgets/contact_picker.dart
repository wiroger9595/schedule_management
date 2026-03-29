import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/api_service.dart';

class ContactPicker extends StatefulWidget {
  final List<String> initialSelectedIds;
  final Function(List<Map<String, dynamic>>) onSelectionChanged;

  const ContactPicker({
    Key? key,
    this.initialSelectedIds = const [],
    required this.onSelectionChanged,
  }) : super(key: key);

  @override
  _ContactPickerState createState() => _ContactPickerState();
}

class _ContactPickerState extends State<ContactPicker> {
  final ApiService apiService = ApiService();
  List<dynamic> contacts = [];
  Set<String> selectedIds = {};
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    selectedIds = widget.initialSelectedIds.toSet();
    fetchContacts();
  }

  Future<void> fetchContacts() async {
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
      print('Error loading contacts: $e');
    }
  }

  void _confirmSelection() {
    final selectedContacts = contacts
        .where((c) => selectedIds.contains(c['id'].toString()))
        .map((c) => c as Map<String, dynamic>)
        .toList();
    widget.onSelectionChanged(selectedContacts);
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.7,
      padding: EdgeInsets.all(16),
      child: Column(
        children: [
          Text(
            'inviteFriends'.tr(),
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 16),
          Expanded(
            child: isLoading
                ? Center(child: CircularProgressIndicator())
                : contacts.isEmpty
                ? Center(child: Text('noContacts'.tr()))
                : ListView.builder(
                    itemCount: contacts.length,
                    itemBuilder: (context, index) {
                      final contact = contacts[index];
                      final String id = contact['id'].toString();
                      final isSelected = selectedIds.contains(id);

                      return ListTile(
                        leading: CircleAvatar(
                          backgroundImage: contact['profile_picture'] != null
                              ? NetworkImage(contact['profile_picture'])
                              : null,
                          child: contact['profile_picture'] == null
                              ? Icon(Icons.person)
                              : null,
                        ),
                        title: Text(
                          contact['nick_name'] ??
                              contact['contact_user_id'] ??
                              'Unknown',
                        ),
                        subtitle: Text(contact['email'] ?? ''),
                        trailing: Checkbox(
                          value: isSelected,
                          onChanged: (val) {
                            setState(() {
                              if (val == true) {
                                selectedIds.add(id);
                              } else {
                                selectedIds.remove(id);
                              }
                            });
                          },
                        ),
                        onTap: () {
                          setState(() {
                            if (isSelected) {
                              selectedIds.remove(id);
                            } else {
                              selectedIds.add(id);
                            }
                          });
                        },
                      );
                    },
                  ),
          ),
          ElevatedButton(
            onPressed: _confirmSelection,
            style: ElevatedButton.styleFrom(
              minimumSize: Size(double.infinity, 50),
            ),
            child: Text('confirmCount'.tr(namedArgs: {'count': selectedIds.length.toString()})),
          ),
        ],
      ),
    );
  }
}
