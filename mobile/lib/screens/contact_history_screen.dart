import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/schedule.dart';
import '../services/api_service.dart';

class ContactHistoryScreen extends StatefulWidget {
  final Map<String, dynamic> contact;

  const ContactHistoryScreen({Key? key, required this.contact}) : super(key: key);

  @override
  _ContactHistoryScreenState createState() => _ContactHistoryScreenState();
}

class _ContactHistoryScreenState extends State<ContactHistoryScreen> {
  late Future<List<Schedule>> _historyFuture;
  final ApiService _apiService = ApiService();

  @override
  void initState() {
    super.initState();
    _historyFuture = _fetchHistory();
  }

  Future<List<Schedule>> _fetchHistory() async {
    return _apiService.getContactScheduleHistory(widget.contact['id']);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.contact['nick_name'] ?? '聯絡人紀錄'),
      ),
      body: Column(
        children: [
          // Top: Contact Info
          Container(
            padding: EdgeInsets.all(20),
            color: Colors.blue.shade50,
            child: Row(
              children: [
                 CircleAvatar(
                    radius: 30,
                    backgroundImage: widget.contact['profile_image_path'] != null
                        ? NetworkImage(widget.contact['profile_image_path'])
                        : null,
                    backgroundColor: Colors.grey[200],
                    child: widget.contact['profile_image_path'] == null
                        ? Icon(Icons.person, size: 30, color: Colors.grey[500])
                        : null,
                  ),
                SizedBox(width: 16),
                SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.contact['nick_name'] ?? 'Unknown',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (widget.contact['phone'] != null)
                        Text(
                          widget.contact['phone'], 
                          style: TextStyle(color: Colors.grey[700]),
                          overflow: TextOverflow.ellipsis,
                        ),
                      if (widget.contact['email'] != null)
                        Text(
                          widget.contact['email'], 
                          style: TextStyle(color: Colors.grey[700]),
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                )
              ],
            ),
          ),
          Divider(height: 1),
          Expanded(
            child: FutureBuilder<List<Schedule>>(
              future: _historyFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Center(child: CircularProgressIndicator());
                } else if (snapshot.hasError) {
                  return Center(child: Text('無法載入紀錄: ${snapshot.error}'));
                } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.history_toggle_off, size: 60, color: Colors.grey),
                        SizedBox(height: 16),
                        Text('尚無與此聯絡人的互動紀錄', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }

                final schedules = snapshot.data!;
                // Sort by date desc
                schedules.sort((a, b) => b.startTime.compareTo(a.startTime));

                return ListView.builder(
                  itemCount: schedules.length,
                  itemBuilder: (context, index) {
                    final schedule = schedules[index];
                    final dateStr = DateFormat('yyyy/MM/dd').format(schedule.startTime);
                    final timeStr = DateFormat('HH:mm').format(schedule.startTime);

                    return Card(
                      margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: ListTile(
                        leading: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(dateStr, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                            Text(timeStr, style: TextStyle(color: Colors.grey)),
                          ],
                        ),
                        title: Text(schedule.title),
                        subtitle: schedule.location != null ? 
                             Row(children: [Icon(Icons.location_on, size: 14), SizedBox(width: 4), Expanded(child: Text(schedule.location!, overflow: TextOverflow.ellipsis))]) 
                             : null,
                        // Could add onTap to view schedule details later
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
