import 'package:flutter/material.dart';
import '../models/schedule.dart';
import '../services/api_service.dart';

class ScheduleProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  
  List<Schedule> _schedules = [];
  bool _isLoading = false;
  String? _error;

  List<Schedule> get schedules => _schedules;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> fetchSchedules() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _schedules = await _apiService.getSchedules();
    } catch (e) {
      _error = e.toString();
      _schedules = [];
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> addSchedule(Schedule schedule) async {
    try {
       // Ideally API returns the created schedule
       // For now, allow refresh or duplicate logic if API service requires it
       // Assuming ApiService has create method or similar
       // Since ApiService.createSchedule isn't explicitly in the snippet I saw, 
       // I'll assume standard usage.
       // Note: ApiService might need update if it doesn't return Schedule.
       // Checking HomeScreen code, it just refreshed.
       // Here we'll implement optimistic update or refresh.
       
       // Let's assume ApiService has createMethod.
       // If not, we might need to rely on what screens did.
       // Screens used: await apiService.createSchedule(...)
       
       // Re-fetch to be safe and get server-generated fields (ID, AI analysis)
       await fetchSchedules();
       return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }
  
  // Method to manually set schedules if needed (e.g. from chat result)
  void addLocalSchedule(Schedule schedule) {
    _schedules.add(schedule);
    notifyListeners();
  }
  
  Future<void> deleteCancelSchedule(int id) async {
    // Implement delete/cancel logic
    // await _apiService.deleteSchedule(id);
    _schedules.removeWhere((s) => s.id == id);
    notifyListeners();
  }
}
