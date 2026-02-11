import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'profile_edit_screen.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import "../l10n/app_localizations.dart";

class ProfileScreen extends StatefulWidget {
  @override
  _ProfileScreenState createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _user;
  bool _isLoading = true;
  bool _hasUpdated = false;

  @override
  void initState() {
    super.initState();
    _loadUserInfo();
  }

  Future<void> _loadUserInfo() async {
    setState(() => _isLoading = true);
    try {
      final apiService = ApiService();
      final headers = await apiService.getHeaders();
      final response = await http.get(
        Uri.parse('${ApiService.baseUrl}/users/me'),
        headers: headers,
      );
      
      if (response.statusCode == 200) {
        setState(() {
          _user = jsonDecode(response.body);
          _isLoading = false;
        });
      }
    } catch (e) {
      print('Error loading user info: $e');
      setState(() => _isLoading = false);
    }
  }

  String _getLanguageName(String? language) {
    switch (language) {
      case 'zh-TW':
        return '繁體中文';
      case 'en':
        return 'English';
      case 'ja':
        return '日本語';
      default:
        return language ?? '未設定';
    }
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: () async {
        Navigator.pop(context, _hasUpdated);
        return false;
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(AppLocalizations.of(context)!.profile),
          actions: [
            if (_user != null)
              IconButton(
                icon: Icon(Icons.edit),
                onPressed: () async {
                  final result = await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => ProfileEditScreen(user: _user!),
                    ),
                  );
                  if (result == true) {
                    _hasUpdated = true;
                    _loadUserInfo(); // 重新載入
                  }
                },
              ),
          ],
        ),
        body: _isLoading
            ? Center(child: CircularProgressIndicator())
            : _user == null
                ? Center(child: Text(AppLocalizations.of(context)!.error))
                : SingleChildScrollView(
                    padding: EdgeInsets.all(16),
                    child: Column(
                      children: [
                        // 頭像（可點擊進入編輯）
                        GestureDetector(
                          onTap: () async {
                            final result = await Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => ProfileEditScreen(user: _user!),
                              ),
                            );
                            if (result == true) {
                              _hasUpdated = true;
                              _loadUserInfo(); // 重新載入
                            }
                          },
                          child: Stack(
                            children: [
                              CircleAvatar(
                                radius: 60,
                                backgroundImage: _user!['profile_image_path'] != null
                                    ? NetworkImage(_user!['profile_image_path'])
                                    : null,
                                backgroundColor: Colors.purple[100],
                                child: _user!['profile_image_path'] == null
                                    ? Icon(Icons.person, size: 80, color: Colors.purple[700])
                                    : null,
                              ),
                              // 提示按鈕
                              Positioned(
                                bottom: 0,
                                right: 0,
                                child: Container(
                                  padding: EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.purple[700],
                                    shape: BoxShape.circle,
                                  ),
                                  child: Icon(
                                    Icons.edit,
                                    color: Colors.white,
                                    size: 20,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        SizedBox(height: 24),
                        SizedBox(height: 24),
                        _buildInfoCard(AppLocalizations.of(context)!.accountNumber, _user!['account_number'] ?? 'N/A'),
                        _buildInfoCard(AppLocalizations.of(context)!.name, _user!['full_name'] ?? '-'),
                        _buildInfoCard(AppLocalizations.of(context)!.email, _user!['email'] ?? 'N/A'),
                        _buildInfoCard(AppLocalizations.of(context)!.phone, _user!['phone'] ?? '-'),
                        _buildInfoCard(AppLocalizations.of(context)!.lineId, _user!['line_id'] ?? '-'),
                        _buildInfoCard(AppLocalizations.of(context)!.language, _getLanguageName(_user!['language'])),
                      ],
                    ),
                  ),
      ),
    );
  }

  Widget _buildInfoCard(String label, String value) {
    return Card(
      margin: EdgeInsets.symmetric(vertical: 8),
      child: ListTile(
        title: Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 14)),
        subtitle: Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
      ),
    );
  }
}
