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

  Future<void> updateStatus(String id, String status) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/schedules/$id'),
      headers: await getHeaders(), // Optimized to use getter
      body: jsonEncode({'status': status}),
    );
    if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else if (response.statusCode != 200) {
      throw Exception('Failed to update status');
    }
  }
}
