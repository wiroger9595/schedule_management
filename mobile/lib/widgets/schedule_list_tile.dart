import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/schedule.dart';
import '../i18n/app_localizations.dart';
import '../utils/constants.dart';

/// Reusable schedule card widget extracted from HomeScreen.
/// Displays a single schedule item with title, time, location, status, and attendees.
class ScheduleListTile extends StatelessWidget {
  final Schedule schedule;
  final VoidCallback? onTap;

  const ScheduleListTile({
    Key? key,
    required this.schedule,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      elevation: 4,
      color: schedule.status == ScheduleStatus.cancel ? Colors.grey[200] : null,
      child: ListTile(
        contentPadding: EdgeInsets.all(16),
        title: Text(
          schedule.title,
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(height: 8),
            Row(
              children: [
                Icon(Icons.access_time, size: 16, color: Colors.grey),
                SizedBox(width: 8),
                Text(
                  schedule.endTime != null
                      ? '${DateFormat('yyyy-MM-dd HH:mm').format(schedule.startTime)} - ${DateFormat('HH:mm').format(schedule.endTime!)}'
                      : DateFormat('yyyy-MM-dd HH:mm').format(schedule.startTime),
                ),
              ],
            ),
            if (schedule.location != null) ...[
              SizedBox(height: 4),
              Row(
                children: [
                  Icon(Icons.location_on, size: 16, color: Colors.grey),
                  SizedBox(width: 8),
                  Expanded(child: Text(schedule.location!)),
                ],
              ),
            ],
            SizedBox(height: 8),
            Container(
              padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: _getStatusColor(schedule.status),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                _getStatusText(context, schedule.status),
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            if (schedule.attends != null && schedule.attends!.isNotEmpty) ...[
              SizedBox(height: 8),
              Divider(),
              SizedBox(height: 4),
              Row(
                children: [
                  Icon(Icons.people, size: 16, color: Colors.grey),
                  SizedBox(width: 8),
                  Expanded(
                    child: Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      children: schedule.attends!.map((attendee) {
                        final name = attendee['nick_name'] ??
                            attendee['name'] ??
                            '?';
                        return Tooltip(
                          message: name,
                          child: CircleAvatar(
                            radius: 12,
                            backgroundColor: Colors.blue[100],
                            child: Text(
                              name.isNotEmpty ? name[0] : '?',
                              style: TextStyle(
                                fontSize: 10,
                                color: Colors.blue[800],
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
        onTap: onTap,
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case ScheduleStatus.pending:
        return const Color.fromARGB(255, 66, 233, 0);
      case ScheduleStatus.attend:
        return const Color.fromARGB(255, 39, 45, 39);
      case ScheduleStatus.notAttended:
        return const Color.fromARGB(255, 213, 145, 43);
      case ScheduleStatus.active:
        return const Color.fromARGB(255, 41, 69, 80);
      case ScheduleStatus.notGoing:
        return const Color.fromARGB(255, 189, 203, 131);
      case ScheduleStatus.cancel:
        return Colors.red;
      case ScheduleStatus.comingSoon:
        return Colors.amber[800]!;
      default:
        return Colors.grey;
    }
  }

  String _getStatusText(BuildContext context, String status) {
    switch (status) {
      case ScheduleStatus.pending:
        return AppLocalizations.of(context)!.statusPending;
      case ScheduleStatus.attend:
        return AppLocalizations.of(context)!.statusAttend;
      case ScheduleStatus.notAttended:
        return AppLocalizations.of(context)!.statusNotAttend;
      case ScheduleStatus.active:
        return AppLocalizations.of(context)!.statusActive;
      case ScheduleStatus.notGoing:
        return AppLocalizations.of(context)!.statusNotGoing;
      case ScheduleStatus.cancel:
        return AppLocalizations.of(context)!.statusCancelled;
      case ScheduleStatus.comingSoon:
        return AppLocalizations.of(context)!.statusComingSoon;
      default:
        return status;
    }
  }
}
