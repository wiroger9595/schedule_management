import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../models/schedule.dart';
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
                Text(_formatDateRange(schedule.startTime, schedule.endTime)),
              ],
            ),
            if (schedule.location != null) ...[
              SizedBox(height: 4),
              Row(
                children: [
                  Icon(
                    (schedule.isOnline == true) ? Icons.video_call : Icons.location_on,
                    size: 16,
                    color: Colors.grey,
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      schedule.location!,
                      style: (schedule.isOnline == true)
                          ? TextStyle(
                              color: Colors.blue,
                              decoration: TextDecoration.underline,
                            )
                          : null,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
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
                        final status = attendee['status'] as String? ?? 'P';
                        final confirmed = status == 'AT';
                        final declined = status == 'NG';
                        return Tooltip(
                          message: confirmed
                              ? '$name（已確認）'
                              : declined
                                  ? '$name（已拒絕）'
                                  : '$name（待回覆）',
                          child: Stack(
                            clipBehavior: Clip.none,
                            children: [
                              CircleAvatar(
                                radius: 12,
                                backgroundColor: confirmed
                                    ? Colors.green[100]
                                    : declined
                                        ? Colors.red[100]
                                        : Colors.grey[300],
                                child: Text(
                                  name.isNotEmpty ? name[0] : '?',
                                  style: TextStyle(
                                    fontSize: 10,
                                    color: Colors.black87,
                                  ),
                                ),
                              ),
                              if (confirmed)
                                Positioned(
                                  right: -2,
                                  bottom: -2,
                                  child: Container(
                                    decoration: const BoxDecoration(
                                        color: Colors.green,
                                        shape: BoxShape.circle),
                                    child: const Icon(Icons.check,
                                        size: 8, color: Colors.white),
                                  ),
                                )
                              else if (declined)
                                Positioned(
                                  right: -2,
                                  bottom: -2,
                                  child: Container(
                                    decoration: const BoxDecoration(
                                        color: Colors.red,
                                        shape: BoxShape.circle),
                                    child: const Icon(Icons.close,
                                        size: 8, color: Colors.white),
                                  ),
                                ),
                            ],
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

  String _formatDateRange(DateTime start, DateTime? end) {
    final sameDay = end != null &&
        start.year == end.year &&
        start.month == end.month &&
        start.day == end.day;

    final startStr = DateFormat('yyyy-MM-dd HH:mm').format(start);
    if (end == null) return startStr;
    if (sameDay) return '$startStr - ${DateFormat('HH:mm').format(end)}';
    return '$startStr\n→ ${DateFormat('yyyy-MM-dd HH:mm').format(end)}';
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
        return 'statusPending'.tr();
      case ScheduleStatus.attend:
        return 'statusAttend'.tr();
      case ScheduleStatus.notAttended:
        return 'statusNotAttend'.tr();
      case ScheduleStatus.active:
        return 'statusActive'.tr();
      case ScheduleStatus.notGoing:
        return 'statusNotGoing'.tr();
      case ScheduleStatus.cancel:
        return 'statusCancelled'.tr();
      case ScheduleStatus.comingSoon:
        return 'statusComingSoon'.tr();
      default:
        return status;
    }
  }
}
