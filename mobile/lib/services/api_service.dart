import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/schedule.dart';
import 'dart:io';

import 'auth_service.dart';

class ApiService {
  final AuthService _authService = AuthService();

  static String get baseUrl {
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:3000/api';
    } else {
      // Use localhost for iOS simulator (resolves to host machine)
      // For real device, change to your Mac's IP: http://10.0.0.7:3000/api
      return 'http://localhost:3000/api';
    }
  }

  Future<Map<String, String>> getHeaders() async {
    String? token = await _authService.getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<List<Schedule>> getSchedules() async {
    final response = await http.get(
      Uri.parse('$baseUrl/schedules'),
      headers: await getHeaders(),
    );
    if (response.statusCode == 200) {
      List<dynamic> body = jsonDecode(response.body);
      return body.map((dynamic item) => Schedule.fromJson(item)).toList();
    } else if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to load schedules');
    }
  }

  Future<Schedule> createSchedule(Schedule schedule) async {
    final response = await http.post(
      Uri.parse('$baseUrl/schedules'),
      headers: await getHeaders(),
      body: jsonEncode(schedule.toJson()),
    );
    if (response.statusCode == 200) {
      return Schedule.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to create schedule');
    }
  }

  Future<Schedule> updateSchedule(String id, Map<String, dynamic> data) async {
    final response = await http.put(
      Uri.parse('$baseUrl/schedules/$id'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    if (response.statusCode == 200) {
      return Schedule.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to update schedule: ${response.body}');
    }
  }

  Future<void> updateStatus(String id, String status, {String? cancelReason}) async {
    final body = {
      'status': status,
      if (cancelReason != null) 'cancel_reason': cancelReason,
    };

    final response = await http.patch(
      Uri.parse('$baseUrl/schedules/$id/status'),
      headers: await getHeaders(),
      body: jsonEncode(body),
    );
    if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else if (response.statusCode != 200) {
      throw Exception('Failed to update status');
    }
  }

  Future<Map<String, dynamic>> estimateTravelTime(double lat1, double lon1, double lat2, double lon2, String mode) async {
    final response = await http.get(
      Uri.parse('$baseUrl/estimate/?lat1=$lat1&lon1=$lon1&lat2=$lat2&lon2=$lon2&mode=$mode'),
      headers: await getHeaders(),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get estimate: ${response.statusCode} - ${response.body}');
    }
  }

  Future<Map<String, dynamic>> estimateAllTravelTimes(double lat1, double lon1, double lat2, double lon2) async {
    final response = await http.get(
      Uri.parse('$baseUrl/estimate/all?lat1=$lat1&lon1=$lon1&lat2=$lat2&lon2=$lon2'),
      headers: await getHeaders(),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get all estimates: ${response.statusCode} - ${response.body}');
    }
  }

  Future<Map<String, dynamic>> chatWithAI(String message) async {
    final response = await http.post(
      Uri.parse('$baseUrl/schedules/chat'),
      headers: await getHeaders(),
      body: jsonEncode({'message': message}),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Unknown error');
    }
  }
  Future<List<dynamic>> searchUsers(String query) async {
    final response = await http.get(
      Uri.parse('$baseUrl/users/search?q=$query'),
      headers: await getHeaders(),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to search users');
    }
  }

  Future<void> forgotPassword(String email) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/forgot-password'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email}),
    );
    
    if (response.statusCode != 200) {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to send reset code');
    }
  }

  Future<void> resetPassword(String email, String code, String newPassword) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/reset-password'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'code': code,
        'new_password': newPassword
      }),
    );
    
    if (response.statusCode != 200) {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to reset password');
    }
  }
}

