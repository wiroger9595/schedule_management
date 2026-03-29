import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'profile_edit_screen.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../widgets/user_avatar.dart';

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
        return 'traditionalChinese'.tr();
      case 'en':
        return 'English';
      case 'ja':
        return 'japanese'.tr();
      default:
        return language ?? 'notSet'.tr();
    }
  }

  String _getDefaultSendingName(String? code) {
    switch (code) {
      case 'line':
        return 'Line';
      case 'sms':
        return 'notificationSMSShort'.tr();
      case 'email':
        return 'Email';
      default:
        return code ?? 'Line'; // Default fallback
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
          title: Text('profile'.tr()),
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
            ? Center(child: Text('error'.tr()))
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
                            builder: (context) =>
                                ProfileEditScreen(user: _user!),
                          ),
                        );
                        if (result == true) {
                          _hasUpdated = true;
                          _loadUserInfo(); // 重新載入
                        }
                      },
                      child: Stack(
                        children: [
                          UserAvatar(
                            radius: 60,
                            imageUrl: _user!['profile_image_path'],
                          ),
                          // 提示按鈕
                          Positioned(
                            bottom: 0,
                            right: 0,
                            child: Container(
                              padding: EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.black,
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
                    _buildInfoCard(
                      'accountNumber'.tr(),
                      _user!['user_id'] ?? 'N/A',
                    ),
                    _buildInfoCard(
                      'name'.tr(),
                      _user!['full_name'] ?? '-',
                    ),
                    _buildInfoCard(
                      'email'.tr(),
                      _user!['email'] ?? 'N/A',
                    ),
                    _buildInfoCard(
                      'phone'.tr(),
                      _user!['phone'] ?? '-',
                    ),
                    _buildInfoCard(
                      'lineId'.tr(),
                      _user!['line_id'] ?? '-',
                    ),
                    _buildInfoCard(
                      'language'.tr(),
                      _getLanguageName(_user!['language']),
                    ),
                    _buildInfoCard(
                      'defaultNotificationMethod'.tr() ?? '預設通知方式',
                      _getDefaultSendingName(_user!['default_sending']),
                    ),
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
        title: Text(
          label,
          style: TextStyle(color: Colors.grey[600], fontSize: 14),
        ),
        subtitle: Text(
          value,
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }
}
