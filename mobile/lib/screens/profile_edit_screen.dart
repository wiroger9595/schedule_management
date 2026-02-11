import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'dart:convert';
import '../services/api_service.dart';
import "../l10n/app_localizations.dart";
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

class ProfileEditScreen extends StatefulWidget {
  final Map<String, dynamic> user;
  
  ProfileEditScreen({required this.user});

  @override
  _ProfileEditScreenState createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends State<ProfileEditScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _phoneController;
  late TextEditingController _lineIdController;
  String _selectedLanguage = 'zh-TW';
  File? _imageFile;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.user['full_name']);
    _phoneController = TextEditingController(text: widget.user['phone']);
    _lineIdController = TextEditingController(text: widget.user['line_id']);
    _selectedLanguage = widget.user['language'] ?? 'zh-TW';
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _lineIdController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 800,
      maxHeight: 800,
      imageQuality: 85,
    );
    
    if (pickedFile != null) {
      setState(() {
        _imageFile = File(pickedFile.path);
      });
    }
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() => _isLoading = true);
    
    try {
      final apiService = ApiService();
      final headers = await apiService.getHeaders();
      
      // 上傳圖片（如果有選擇）
      if (_imageFile != null) {
        var request = http.MultipartRequest(
          'POST',
          Uri.parse('${ApiService.baseUrl}/users/upload-photo'),
        );
        request.headers.addAll(headers);
        
        // 讀取檔案並設定正確的 MIME type
        final bytes = await _imageFile!.readAsBytes();
        final fileName = _imageFile!.path.split('/').last;
        final mimeType = fileName.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg';
        
        request.files.add(
          http.MultipartFile.fromBytes(
            'file',
            bytes,
            filename: fileName,
            contentType: MediaType.parse(mimeType),
          )
        );
        
        final streamedResponse = await request.send();
        final response = await http.Response.fromStream(streamedResponse);
        
        if (response.statusCode != 200) {
          throw Exception('圖片上傳失敗');
        }
      }
      
      // 更新其他資料
      // headers['Content-Type'] = 'application/json'; // Handled by provider
      final auth = Provider.of<AuthProvider>(context, listen: false);
      await auth.updateProfile({
          'full_name': _nameController.text,
          'phone': _phoneController.text,
          'line_id': _lineIdController.text.isNotEmpty ? _lineIdController.text : null,
          'language': _selectedLanguage,
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context)!.profileUpdated)),
        );
        Navigator.pop(context, true); // 返回並通知更新成功
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('儲存失敗：$e')),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  String _getLanguageName(String code) {
    switch (code) {
      case 'zh-TW':
        return '繁體中文';
      case 'en':
        return 'English';
      case 'ja':
        return '日本語';
      default:
        return code;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)!.edit),
        actions: [
          IconButton(
            icon: Icon(Icons.check),
            onPressed: _isLoading ? null : _saveProfile,
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: EdgeInsets.all(16),
          children: [
            // 頭像選擇
            Center(
              child: Stack(
                children: [
                  CircleAvatar(
                    radius: 60,
                    backgroundImage: _imageFile != null
                        ? FileImage(_imageFile!)
                        : (widget.user['profile_image_path'] != null
                            ? NetworkImage(widget.user['profile_image_path'])
                            : null) as ImageProvider?,
                    backgroundColor: Colors.purple[100],
                    child: _imageFile == null && widget.user['profile_image_path'] == null
                        ? Icon(Icons.person, size: 60, color: Colors.purple[700])
                        : null,
                  ),
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: FloatingActionButton(
                      mini: true,
                      onPressed: _pickImage,
                      backgroundColor: Colors.purple[700],
                      child: Icon(Icons.camera_alt, size: 20),
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(height: 32),
            
            // 用戶帳號（唯讀）
            Card(
              child: ListTile(
                title: Text(AppLocalizations.of(context)!.accountNumber, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
                subtitle: Text(
                  widget.user['account_number'] ?? 'N/A',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
            ),
            SizedBox(height: 16),
            
            // 姓名
            TextFormField(
              controller: _nameController,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.name,
                prefixIcon: Icon(Icons.person),
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 16),
            
            // Email（唯讀）
            TextFormField(
              initialValue: widget.user['email'],
              decoration: InputDecoration(
                labelText: '${AppLocalizations.of(context)!.email} *',
                prefixIcon: Icon(Icons.email),
                border: OutlineInputBorder(),
              ),
              enabled: false,
            ),
            SizedBox(height: 16),
            
            // 電話（必填）
            TextFormField(
              controller: _phoneController,
              decoration: InputDecoration(
                labelText: '${AppLocalizations.of(context)!.phone} *',
                prefixIcon: Icon(Icons.phone),
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.phone,
              validator: (value) =>
                  value?.isEmpty ?? true ? '${AppLocalizations.of(context)!.phone} is required' : null,
            ),
            SizedBox(height: 16),
            
            // Line ID
            TextFormField(
              controller: _lineIdController,
              decoration: InputDecoration(
                labelText: '${AppLocalizations.of(context)!.lineId}',
                prefixIcon: Icon(Icons.chat),
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 16),
            
            // 語言選擇
            DropdownButtonFormField<String>(
              value: _selectedLanguage,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.language,
                prefixIcon: Icon(Icons.language),
                border: OutlineInputBorder(),
              ),
              items: [
                DropdownMenuItem(value: 'zh-TW', child: Text('繁體中文')),
                DropdownMenuItem(value: 'en', child: Text('English')),
                DropdownMenuItem(value: 'ja', child: Text('日本語')),
              ],
              onChanged: (value) {
                setState(() => _selectedLanguage = value!);
              },
            ),
            SizedBox(height: 32),
            
            // 儲存按鈕
            SizedBox(
              height: 50,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _saveProfile,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.purple[700],
                ),
                child: _isLoading
                    ? SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : Text(AppLocalizations.of(context)!.save, style: TextStyle(fontSize: 18, color: Colors.white)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
