import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/schedule.dart';
import '../models/todo_comment.dart';
import '../config/app_config.dart';

import 'dart:async';
import 'auth_service.dart';

class ApiService {
  final AuthService _authService = AuthService();
  static final StreamController<void> onUnauthorized =
      StreamController<void>.broadcast();

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
      onUnauthorized.add(null);
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
      onUnauthorized.add(null);
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
      onUnauthorized.add(null);
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

  Future<void> deleteSchedule(String id) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/schedules/$id'),
      headers: await getHeaders(),
    );
    if (response.statusCode == 401) {
      await _authService.logout();
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else if (response.statusCode != 200) {
      throw Exception('刪除失敗 (${response.statusCode})');
    }
  }

  Future<void> updateStatus(String id, String status,
      {String? cancelReason}) async {
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
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else if (response.statusCode != 200) {
      throw Exception('Failed to update status');
    }
  }

  Future<Map<String, dynamic>> estimateTravelTime(
      double lat1, double lon1, double lat2, double lon2, String mode) async {
    final response = await http.get(
      Uri.parse(
          '$baseUrl/estimate/?lat1=$lat1&lon1=$lon1&lat2=$lat2&lon2=$lon2&mode=$mode'),
      headers: await getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(
          'Failed to get estimate: ${response.statusCode} - ${response.body}');
    }
  }

  Future<Map<String, dynamic>> estimateAllTravelTimes(
      double lat1, double lon1, double lat2, double lon2) async {
    final response = await http.get(
      Uri.parse(
          '$baseUrl/estimate/all?lat1=$lat1&lon1=$lon1&lat2=$lat2&lon2=$lon2'),
      headers: await getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(
          'Failed to get all estimates: ${response.statusCode} - ${response.body}');
    }
  }

  Future<Map<String, dynamic>> chatWithAI(String message,
      {Map<String, dynamic>? currentContext,
      List<Map<String, String>>? conversationHistory,
      bool forceCreate = false,
      bool confirmLocation = false,
      bool confirmDelete = false,
      double? latitude,
      double? longitude,
      List<Map<String, dynamic>>? scheduleList}) async {
    final scheduleId = currentContext?['schedule_id'] as String?;
    // Only strip schedule_id (sent as top-level field); keep delete_schedule_id in current_data
    // so the confirm_delete path on the backend can read it
    final contextWithoutId = currentContext != null
        ? (Map<String, dynamic>.from(currentContext)..remove('schedule_id'))
        : null;
    final body = {
      'message': message,
      if (contextWithoutId != null) 'current_data': contextWithoutId,
      if (conversationHistory != null && conversationHistory.isNotEmpty)
        'conversation_history': conversationHistory,
      'force_create': forceCreate,
      'confirm_location': confirmLocation,
      'confirm_delete': confirmDelete,
      'latitude': latitude,
      'longitude': longitude,
      if (scheduleId != null) 'schedule_id': scheduleId,
      if (scheduleList != null && scheduleList.isNotEmpty) 'schedule_list': scheduleList,
    };

    final response = await http.post(
      Uri.parse('$baseUrl/schedules/chat'),
      headers: await getHeaders(),
      body: jsonEncode(body),
    ).timeout(const Duration(seconds: 40));

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
    } else if (response.statusCode == 401) {
      await _authService.logout();
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to load contacts');
    }
  }

  Future<Map<String, dynamic>> createContact(
      String name, String phone, String email, String lineId,
      {String? contactUserId}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/contacts/'),
      headers: await getHeaders(),
      body: jsonEncode({
        'nick_name': name,
        'phone': phone,
        'email': email,
        'line_id': lineId,
        if (contactUserId != null) 'contact_user_id': contactUserId,
      }),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return jsonDecode(response.body);
    } else if (response.statusCode == 401) {
      await _authService.logout();
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to create contact');
    }
  }

  Future<Map<String, dynamic>> updateContact(
      int id, Map<String, dynamic> data) async {
    final response = await http.put(
      Uri.parse('$baseUrl/contacts/$id'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else if (response.statusCode == 401) {
      await _authService.logout();
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to update contact');
    }
  }

  Future<void> deleteContact(int id) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/contacts/$id'),
      headers: await getHeaders(),
    );
    if (response.statusCode == 401) {
      await _authService.logout();
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else if (response.statusCode != 200 && response.statusCode != 204) {
      throw Exception('Failed to delete contact');
    }
  }

  Future<void> deleteContacts(List<int> ids) async {
    final headers = await getHeaders();
    final responses = await Future.wait(
      ids.map((id) => http.delete(
        Uri.parse('$baseUrl/contacts/$id'),
        headers: headers,
      )),
    );
    final failed = responses.where(
      (r) => r.statusCode != 200 && r.statusCode != 204,
    );
    if (failed.isNotEmpty) {
      throw Exception('Failed to delete ${failed.length} contacts');
    }
  }

  Future<Map<String, dynamic>> getMyProfile() async {
    final response = await http.get(
      Uri.parse('$baseUrl/users/me'),
      headers: await getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else if (response.statusCode == 401) {
      await _authService.logout();
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to load profile');
    }
  }

  Future<Map<String, dynamic>> updateMyProfile(
      Map<String, dynamic> data) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/users/me'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else if (response.statusCode == 401) {
      await _authService.logout();
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to update profile: ${response.statusCode}');
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

  Future<void> resetPassword(
      String email, String code, String newPassword) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/reset-password'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(
          {'email': email, 'code': code, 'new_password': newPassword}),
    );

    if (response.statusCode != 200) {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to reset password');
    }
  }

  Future<List<Map<String, dynamic>>> getNearbyPlaces(
      double lat, double lon) async {
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

  Future<void> updateFcmToken(String token) async {
    final response = await http.post(
      Uri.parse('$baseUrl/users/me/fcm-token'),
      headers: await getHeaders(),
      body: jsonEncode({'fcm_token': token}),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to update FCM token');
    }
  }

  Future<List<Map<String, dynamic>>> getMyInvitations() async {
    final response = await http.get(
      Uri.parse('$baseUrl/users/me/invitations'),
      headers: await getHeaders(),
    );
    debugPrint('[Invitations] status=${response.statusCode} body=${response.body}');
    if (response.statusCode == 200) {
      return (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
    } else {
      throw Exception('邀請載入失敗 (${response.statusCode}): ${response.body}');
    }
  }

  Future<void> respondToInvitation(String attendId, String action) async {
    final response = await http.post(
      Uri.parse('$baseUrl/users/me/invitations/$attendId/respond?action=$action'),
      headers: await getHeaders(),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to respond to invitation');
    }
  }

  Future<List<Map<String, dynamic>>> searchPlaces(
      String query, double? lat, double? lon) async {
    final headers = await getHeaders();
    String url = '$baseUrl/estimate/search?q=$query';
    if (lat != null && lon != null) {
      url += '&lat=$lat&lon=$lon';
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

  Future<Map<String, dynamic>> validateContact(
      String? phone, String? email, String? lineId,
      {int? excludeContactId}) async {
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

  Future<Map<String, dynamic>> checkEmailUser(String email) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/contacts/check-email?email=${Uri.encodeComponent(email)}'),
        headers: await getHeaders(),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return {'found': false};
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
      onUnauthorized.add(null);
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
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to create comment');
    }
  }

  Future<TodoComment> updateComment(
      int id, String description, String status) async {
    final response = await http.put(
      Uri.parse('$baseUrl/comments/$id'),
      headers: await getHeaders(),
      body: jsonEncode({'comment_description': description, 'status': status}),
    );
    if (response.statusCode == 200) {
      return TodoComment.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 401) {
      await _authService.logout();
      onUnauthorized.add(null);
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
      onUnauthorized.add(null);
      throw Exception('Unauthorized');
    } else if (response.statusCode != 200) {
      throw Exception('Failed to delete comment');
    }
  }
}
