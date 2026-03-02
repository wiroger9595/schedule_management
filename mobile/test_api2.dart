import 'dart:convert';
import 'package:http/http.dart' as http;

Future<void> main() async {
  // We simulate what _buildMentionList does.
  String jsonResponse = '[{"id": 1, "nick_name": "my contact", "phone": "123", "email": null}, {"id": 2, "nick_name": "John Doe", "phone": null, "email": "a@b.com"}, {"id": 3, "nick_name": null, "phone": "0911"}]';
  List<dynamic> contacts = jsonDecode(jsonResponse);
  
  String mentionQuery = ''; // empty query should return all
  final filteredContacts = contacts.where((c) {
      final name = (c['nick_name'] ?? '').toString().toLowerCase();
      return name.contains(mentionQuery);
  }).toList();
  
  print("Filtered contacts length: \${filteredContacts.length}");
  
  mentionQuery = 'my';
  final filteredContacts2 = contacts.where((c) {
      final name = (c['nick_name'] ?? '').toString().toLowerCase();
      return name.contains(mentionQuery);
  }).toList();
  
  print("Filtered contacts length for 'my': \${filteredContacts2.length}");
}
