import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/schedule.dart';
import '../models/todo_comment.dart';
import '../config/app_config.dart';

import 'auth_service.dart';

class ApiService {
  final AuthService _authService = AuthService();

  static String get baseUrl => AppConfig.baseUrl;

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
      try {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? 'Failed to create schedule');
      } catch (_) {
        throw Exception('Failed to create schedule');
      }
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
      try {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? 'Failed to update schedule');
      } catch (_) {
        throw Exception('Failed to update schedule: ${response.body}');
      }
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

  Future<Map<String, dynamic>> chatWithAI(String message, {Map<String, dynamic>? currentContext, bool forceCreate = false, double? latitude, double? longitude}) async {
    final body = {
      'message': message,
      if (currentContext != null) 'current_data': currentContext,
      'force_create': forceCreate,
      'latitude': latitude,
      'longitude': longitude
    };

    final response = await http.post(
      Uri.parse('$baseUrl/schedules/chat'),
      headers: await getHeaders(),
      body: jsonEncode(body),
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

  Future<List<dynamic>> getContacts() async {
    final response = await http.get(
      Uri.parse('$baseUrl/contacts/'),
      headers: await getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load contacts');
    }
  }

  Future<Map<String, dynamic>> createContact(String name, String phone, String email, String lineId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/contacts/'),
      headers: await getHeaders(),
      body: jsonEncode({
        'nick_name': name,
        'phone': phone,
        'email': email,
        'line_id': lineId,
      }),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to create contact');
    }
  }

  Future<String> reverseGeocode(double lat, double lon) async {
    final response = await http.get(
      Uri.parse('$baseUrl/estimate/reverse?lat=$lat&lon=$lon'),
      headers: await getHeaders(),
    );
    
    if (response.statusCode == 200) {
      final body = jsonDecode(response.body);
      return body['address'];
    } else {
      throw Exception('Failed to reverse geocode');
    }
  }

  Future<List<Schedule>> getContactScheduleHistory(int contactId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/contacts/$contactId/schedules'),
      headers: await getHeaders(),
    );
    
    if (response.statusCode == 200) {
      List<dynamic> body = jsonDecode(response.body);
      return body.map((dynamic item) => Schedule.fromJson(item)).toList();
    } else {
      throw Exception('Failed to load contact history');
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
  Future<List<Map<String, dynamic>>> getNearbyPlaces(double lat, double lon) async {
    final headers = await getHeaders();
    final response = await http.get(
      Uri.parse('$baseUrl/estimate/nearby?lat=$lat&lon=$lon&radius=300'),
      headers: headers,
    );
    
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load nearby places');
    }
  }

  Future<List<Map<String, dynamic>>> searchPlaces(String query, double? lat, double? lon, {double? zoom}) async {
    final headers = await getHeaders();
    String url = '$baseUrl/estimate/search?q=$query';
    if (lat != null && lon != null) {
      url += '&lat=$lat&lon=$lon';
    }
    if (zoom != null) {
      url += '&zoom=$zoom';
    }

    final response = await http.get(
      Uri.parse(url),
      headers: headers,
    );
    
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to search places');
    }
  }

  Future<Map<String, dynamic>> validateContact(String? phone, String? email, String? lineId, {int? excludeContactId}) async {
    final body = {
      if (phone != null && phone.isNotEmpty) 'phone': phone,
      if (email != null && email.isNotEmpty) 'email': email,
      if (lineId != null && lineId.isNotEmpty) 'line_id': lineId,
      if (excludeContactId != null) 'exclude_contact_id': excludeContactId,
    };

    final response = await http.post(
      Uri.parse('$baseUrl/contacts/validate'),
      headers: await getHeaders(),
      body: jsonEncode(body),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to validate contact');
    }
  }

  // --- Todo List / Comments ---

  Future<List<TodoComment>> getComments() async {
    final response = await http.get(
      Uri.parse('$baseUrl/comments'),
      headers: await getHeaders(),
    );
    if (response.statusCode == 200) {
      List<dynamic> body = jsonDecode(response.body);
      return body.map((dynamic item) => TodoComment.fromJson(item)).toList();
    } else if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to load comments');
    }
  }

  Future<TodoComment> createComment(String description) async {
    final response = await http.post(
      Uri.parse('$baseUrl/comments'),
      headers: await getHeaders(),
      body: jsonEncode({'comment_description': description, 'status': 'P'}),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return TodoComment.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to create comment');
    }
  }

  Future<TodoComment> updateComment(int id, String description, String status) async {
    final response = await http.put(
      Uri.parse('$baseUrl/comments/$id'),
      headers: await getHeaders(),
      body: jsonEncode({'comment_description': description, 'status': status}),
    );
    if (response.statusCode == 200) {
      return TodoComment.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to update comment');
    }
  }

  Future<void> deleteComment(int id) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/comments/$id'),
      headers: await getHeaders(),
    );
    if (response.statusCode == 401) {
      await _authService.logout();
      throw Exception('Unauthorized');
    } else if (response.statusCode != 200) {
      throw Exception('Failed to delete comment');
    }
  }
}


