import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../models/schedule.dart';
import 'dart:convert';
import 'dart:convert';
import 'package:http/http.dart' as http;
import "../l10n/app_localizations.dart";
import '../utils/constants.dart';
import 'map_screen.dart';

class CalendarScreen extends StatefulWidget {
  @override
  _CalendarScreenState createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  CalendarFormat _calendarFormat = CalendarFormat.month;
  DateTime _focusedDay = DateTime.now();
  DateTime _selectedDay = DateTime.now();
  Map<DateTime, List<Schedule>> _schedules = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadSchedules();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadSchedules() async {
    try {
      final apiService = ApiService();
      final headers = await apiService.getHeaders();
      final response = await http.get(
        Uri.parse('${ApiService.baseUrl}/schedules'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        List<dynamic> data = jsonDecode(response.body);
        Map<DateTime, List<Schedule>> scheduleMap = {};

        for (var item in data) {
          Schedule schedule = Schedule.fromJson(item);
          DateTime date = DateTime(
            schedule.startTime.year,
            schedule.startTime.month,
            schedule.startTime.day,
          );

          if (scheduleMap[date] == null) {
            scheduleMap[date] = [];
          }
          scheduleMap[date]!.add(schedule);
        }

        setState(() {
          _schedules = scheduleMap;
          _isLoading = false;
        });
      }
    } catch (e) {
      print('Error loading schedules: $e');
      setState(() {
        _isLoading = false;
      });
    }
  }

  List<Schedule> _getSchedulesForDay(DateTime day) {
    DateTime normalizedDay = DateTime(day.year, day.month, day.day);
    return _schedules[normalizedDay] ?? [];
  }

  void _navigateToMapScreen(Schedule schedule) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => MapScreen(schedule: schedule),
      ),
    );
    // Refresh schedules on return
    _loadSchedules();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)!.calendar),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(icon: Icon(Icons.calendar_month), text: AppLocalizations.of(context)!.month),
            Tab(icon: Icon(Icons.view_week), text: AppLocalizations.of(context)!.week),
            Tab(icon: Icon(Icons.view_day), text: AppLocalizations.of(context)!.day),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.today),
            onPressed: () {
              setState(() {
                _focusedDay = DateTime.now();
                _selectedDay = DateTime.now();
              });
            },
          ),
        ],
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _buildMonthView(),
                _buildWeekView(),
                _buildDayView(),
              ],
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.pushNamed(context, '/add').then((_) => _loadSchedules());
        },
        child: Icon(Icons.add),
      ),
    );
  }

  Widget _buildMonthView() {
    return RefreshIndicator(
      onRefresh: _loadSchedules,
      child: SingleChildScrollView(
        child: Column(
          children: [
            TableCalendar(
              firstDay: DateTime.utc(2020, 1, 1),
              lastDay: DateTime.utc(2030, 12, 31),
              focusedDay: _focusedDay,
              selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
              calendarFormat: _calendarFormat,
              eventLoader: _getSchedulesForDay,
              onDaySelected: (selectedDay, focusedDay) {
                setState(() {
                  _selectedDay = selectedDay;
                  _focusedDay = focusedDay;
                });
              },
              onFormatChanged: (format) {
                setState(() {
                  _calendarFormat = format;
                });
              },
              onPageChanged: (focusedDay) {
                _focusedDay = focusedDay;
              },
              calendarStyle: CalendarStyle(
                todayDecoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.5),
                  shape: BoxShape.circle,
                ),
                selectedDecoration: BoxDecoration(
                  color: Colors.blue,
                  shape: BoxShape.circle,
                ),
                markerDecoration: BoxDecoration(
                  color: Colors.red,
                  shape: BoxShape.circle,
                ),
              ),
              headerStyle: HeaderStyle(
                formatButtonVisible: true,
                titleCentered: true,
                formatButtonShowsNext: false,
              ),
            ),
            Divider(),
            _buildScheduleList(_getSchedulesForDay(_selectedDay)),
          ],
        ),
      ),
    );
  }

  Widget _buildWeekView() {
    DateTime startOfWeek = _focusedDay.subtract(Duration(days: _focusedDay.weekday - 1));
    List<DateTime> weekDays = List.generate(7, (index) => startOfWeek.add(Duration(days: index)));

    return RefreshIndicator(
      onRefresh: _loadSchedules,
      child: Column(
        children: [
          Padding(
            padding: EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: Icon(Icons.chevron_left),
                  onPressed: () {
                    setState(() {
                      _focusedDay = _focusedDay.subtract(Duration(days: 7));
                    });
                  },
                ),
                Text(
                  '${DateFormat('yyyy年MM月').format(weekDays.first)} - ${DateFormat('MM月dd日').format(weekDays.last)}',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                IconButton(
                  icon: Icon(Icons.chevron_right),
                  onPressed: () {
                    setState(() {
                      _focusedDay = _focusedDay.add(Duration(days: 7));
                    });
                  },
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              children: weekDays.map((day) {
                List<Schedule> daySchedules = _getSchedulesForDay(day);
                bool isToday = isSameDay(day, DateTime.now());
                
                return Card(
                  margin: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  color: isToday ? Colors.blue.withOpacity(0.1) : null,
                  child: ExpansionTile(
                    leading: CircleAvatar(
                      backgroundColor: isToday ? Colors.blue : Colors.grey,
                      child: Text(
                        '${day.day}',
                        style: TextStyle(color: Colors.white),
                      ),
                    ),
                    title: Text(
                      DateFormat('EEEE').format(day),
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(AppLocalizations.of(context)!.eventsCount(daySchedules.length)),
                    children: [
                      if (daySchedules.isEmpty)
                        Padding(
                          padding: EdgeInsets.all(16),
                          child: Text(AppLocalizations.of(context)!.noEvents, style: TextStyle(color: Colors.grey)),
                        )
                      else
                        ...daySchedules.map((schedule) => ListTile(
                          dense: true,
                          leading: Icon(Icons.circle, size: 12, color: _getStatusColor(schedule.status)),
                          title: Text(schedule.title),
                          subtitle: Text(DateFormat('HH:mm').format(schedule.startTime)),
                          onTap: () => _navigateToMapScreen(schedule),
                        )),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDayView() {
    List<Schedule> daySchedules = _getSchedulesForDay(_selectedDay);
    daySchedules.sort((a, b) => a.startTime.compareTo(b.startTime));

    return RefreshIndicator(
      onRefresh: _loadSchedules,
      child: Column(
        children: [
          Padding(
            padding: EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: Icon(Icons.chevron_left),
                  onPressed: () {
                    setState(() {
                      _selectedDay = _selectedDay.subtract(Duration(days: 1));
                      _focusedDay = _selectedDay;
                    });
                  },
                ),
                Text(
                  DateFormat('yyyy年MM月dd日 EEEE').format(_selectedDay),
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                IconButton(
                  icon: Icon(Icons.chevron_right),
                  onPressed: () {
                    setState(() {
                      _selectedDay = _selectedDay.add(Duration(days: 1));
                      _focusedDay = _selectedDay;
                    });
                  },
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              itemCount: 24,
              itemBuilder: (context, hour) {
                // Find schedules for this hour
                List<Schedule> hourSchedules = daySchedules.where((s) => s.startTime.hour == hour).toList();
                
                return Container(
                  height: 100,
                  decoration: BoxDecoration(
                    border: Border(
                      top: BorderSide(color: Colors.grey.shade300),
                    ),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Time label
                      Container(
                        width: 60,
                        padding: EdgeInsets.all(8),
                        child: Text(
                          '${hour.toString().padLeft(2, '0')}:00',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        ),
                      ),
                      // Schedule slots
                      Expanded(
                        child: hourSchedules.isEmpty
                            ? Container()
                            : Column(
                                children: hourSchedules.map((schedule) {
                                  return Expanded(
                                    child: Container(
                                      margin: EdgeInsets.all(4),
                                      padding: EdgeInsets.all(8),
                                      decoration: BoxDecoration(
                                        color: _getStatusColor(schedule.status).withOpacity(0.2),
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(
                                          color: _getStatusColor(schedule.status),
                                          width: 2,
                                        ),
                                      ),
                                      child: GestureDetector(
                                        onTap: () => _navigateToMapScreen(schedule),
                                        child: SingleChildScrollView(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            mainAxisAlignment: MainAxisAlignment.center,
                                            children: [
                                              Text(
                                                schedule.title,
                                                style: TextStyle(
                                                  fontWeight: FontWeight.bold,
                                                  fontSize: 14,
                                                ),
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                              SizedBox(height: 2),
                                              Text(
                                                DateFormat('HH:mm').format(schedule.startTime),
                                                style: TextStyle(
                                                  fontSize: 12,
                                                  color: Colors.grey[700],
                                                ),
                                              ),
                                              if (schedule.location != null) ...[
                                                SizedBox(height: 2),
                                                Row(
                                                  children: [
                                                    Icon(Icons.location_on, size: 12, color: Colors.grey[600]),
                                                    SizedBox(width: 2),
                                                    Expanded(
                                                      child: Text(
                                                        schedule.location!,
                                                        style: TextStyle(fontSize: 10, color: Colors.grey[600]),
                                                        maxLines: 1,
                                                        overflow: TextOverflow.ellipsis,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ],
                                            ],
                                          ),
                                        ),
                                      ),
                                    ),
                                  );
                                }).toList(),
                              ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildScheduleList(List<Schedule> schedules) {
    if (schedules.isEmpty) {
      return Padding(
        padding: EdgeInsets.all(32),
        child: Text(
          AppLocalizations.of(context)!.noEvents,
          style: TextStyle(color: Colors.grey),
          textAlign: TextAlign.center,
        ),
      );
    }

    schedules.sort((a, b) => a.startTime.compareTo(b.startTime));

    return ListView.builder(
      shrinkWrap: true,
      physics: NeverScrollableScrollPhysics(),
      itemCount: schedules.length,
      itemBuilder: (context, index) {
        Schedule schedule = schedules[index];
        return ListTile(
          leading: Icon(
            Icons.event,
            color: _getStatusColor(schedule.status),
          ),
          title: Text(schedule.title),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(DateFormat('HH:mm').format(schedule.startTime)),
              if (schedule.location != null)
                Row(
                  children: [
                    Icon(Icons.location_on, size: 12),
                    SizedBox(width: 4),
                    Expanded(child: Text(schedule.location!)),
                  ],
                ),
            ],
          ),
          trailing: Chip(
            label: Text(
              _getStatusText(schedule.status),
              style: TextStyle(fontSize: 10),
            ),
            backgroundColor: _getStatusColor(schedule.status).withOpacity(0.2),
          ),
          onTap: () => _navigateToMapScreen(schedule),
        );
      },
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case ScheduleStatus.pending:
        return Colors.orange;
      case ScheduleStatus.active:
        return Colors.green;
      case ScheduleStatus.notGoing:
        return Colors.grey;
      case ScheduleStatus.cancel:
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _getStatusText(String status) {
    switch (status) {
      case ScheduleStatus.pending:
        return AppLocalizations.of(context)!.statusPending;
      case ScheduleStatus.active:
        return AppLocalizations.of(context)!.statusActive;
      case ScheduleStatus.notGoing:
        return AppLocalizations.of(context)!.statusNotGoing;
      case ScheduleStatus.cancel:
        return AppLocalizations.of(context)!.statusCancelled;
      default:
        return status;
    }
  }
}
