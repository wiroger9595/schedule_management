import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../models/schedule.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';

class ScheduleListTile extends StatelessWidget {
  final Schedule schedule;
  final VoidCallback? onTap;

  const ScheduleListTile({Key? key, required this.schedule, this.onTap})
      : super(key: key);

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(schedule.status);
    final cancelled = schedule.status == ScheduleStatus.cancel;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        decoration: BoxDecoration(
          color: cancelled ? AppTheme.surfaceVar : AppTheme.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.border),
        ),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── Left status stripe ──────────────────────────
              Container(
                width: 4,
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: const BorderRadius.only(
                    topLeft:    Radius.circular(16),
                    bottomLeft: Radius.circular(16),
                  ),
                ),
              ),
              // ── Content ────────────────────────────────────
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Title row
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Text(
                              schedule.title,
                              style: TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 16,
                                color: cancelled
                                    ? AppTheme.textMuted
                                    : AppTheme.textPrimary,
                                decoration: cancelled
                                    ? TextDecoration.lineThrough
                                    : null,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          _StatusPill(status: schedule.status, color: color),
                        ],
                      ),
                      const SizedBox(height: 8),

                      // Time
                      _InfoRow(
                        icon: Icons.schedule_rounded,
                        text: _formatDateRange(schedule.startTime, schedule.endTime),
                      ),

                      // Location
                      if (schedule.location != null) ...[
                        const SizedBox(height: 4),
                        _InfoRow(
                          icon: schedule.isOnline == true
                              ? Icons.videocam_outlined
                              : Icons.location_on_outlined,
                          text: schedule.location!,
                          color: schedule.isOnline == true
                              ? AppTheme.primary
                              : null,
                          maxLines: 1,
                        ),
                      ],

                      // Creator badge
                      if (schedule.isOwner == false) ...[
                        const SizedBox(height: 8),
                        _CreatorBadge(name: schedule.creatorName),
                      ],

                      // Attendees
                      if (schedule.attends != null &&
                          schedule.attends!.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        const Divider(height: 1),
                        const SizedBox(height: 10),
                        _AttendeesRow(attends: schedule.attends!),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
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
    if (sameDay) return '$startStr – ${DateFormat('HH:mm').format(end)}';
    return '$startStr\n→ ${DateFormat('yyyy-MM-dd HH:mm').format(end)}';
  }

  Color _statusColor(String status) {
    switch (status) {
      case ScheduleStatus.comingSoon:  return AppTheme.statusCS;
      case ScheduleStatus.active:      return AppTheme.statusA;
      case ScheduleStatus.pending:     return AppTheme.statusP;
      case ScheduleStatus.attend:      return AppTheme.statusAT;
      case ScheduleStatus.notGoing:    return AppTheme.statusNG;
      case ScheduleStatus.notAttended: return AppTheme.statusNA;
      case ScheduleStatus.cancel:      return AppTheme.statusC;
      default:                         return AppTheme.textMuted;
    }
  }
}

// ── Sub-widgets ─────────────────────────────────────────────────────────────

class _StatusPill extends StatelessWidget {
  final String status;
  final Color color;
  const _StatusPill({required this.status, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.35)),
      ),
      child: Text(
        _label(status),
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.2,
        ),
      ),
    );
  }

  String _label(String s) {
    switch (s) {
      case ScheduleStatus.comingSoon:  return 'statusComingSoon'.tr();
      case ScheduleStatus.active:      return 'statusActive'.tr();
      case ScheduleStatus.pending:     return 'statusPending'.tr();
      case ScheduleStatus.attend:      return 'statusAttend'.tr();
      case ScheduleStatus.notGoing:    return 'statusNotGoing'.tr();
      case ScheduleStatus.notAttended: return 'statusNotAttend'.tr();
      case ScheduleStatus.cancel:      return 'statusCancelled'.tr();
      default:                         return s;
    }
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color? color;
  final int maxLines;
  const _InfoRow({
    required this.icon,
    required this.text,
    this.color,
    this.maxLines = 2,
  });

  @override
  Widget build(BuildContext context) {
    final fg = color ?? AppTheme.textSecond;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 14, color: fg),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            text,
            style: TextStyle(fontSize: 13, color: fg, height: 1.4),
            maxLines: maxLines,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _CreatorBadge extends StatelessWidget {
  final String? name;
  const _CreatorBadge({this.name});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Colors.orange.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.orange.shade200),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.person_outline, size: 12, color: Colors.orange.shade700),
          const SizedBox(width: 4),
          Text(
            name ?? '他人建立',
            style: TextStyle(
              fontSize: 11,
              color: Colors.orange.shade700,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _AttendeesRow extends StatelessWidget {
  final List<dynamic> attends;
  const _AttendeesRow({required this.attends});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(Icons.group_outlined, size: 14, color: AppTheme.textMuted),
        const SizedBox(width: 8),
        Wrap(
          spacing: 4,
          runSpacing: 4,
          children: attends.map((a) {
            final name   = (a['nick_name'] ?? a['name'] ?? '?') as String;
            final status = (a['status'] as String?) ?? 'P';
            final ok  = status == 'AT';
            final no  = status == 'NG';
            final bg  = ok  ? AppTheme.statusAT.withOpacity(0.15)
                       : no ? AppTheme.statusC.withOpacity(0.12)
                            : AppTheme.border;
            final fg  = ok  ? AppTheme.statusAT
                       : no ? AppTheme.statusC
                            : AppTheme.textSecond;
            return Tooltip(
              message: ok ? '$name（已確認）' : no ? '$name（已拒絕）' : '$name（待回覆）',
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  CircleAvatar(
                    radius: 13,
                    backgroundColor: bg,
                    child: Text(
                      name.isNotEmpty ? name[0] : '?',
                      style: TextStyle(fontSize: 11, color: fg, fontWeight: FontWeight.w600),
                    ),
                  ),
                  if (ok || no)
                    Positioned(
                      right: -2,
                      bottom: -2,
                      child: Container(
                        padding: const EdgeInsets.all(1),
                        decoration: BoxDecoration(
                          color: ok ? AppTheme.statusAT : AppTheme.statusC,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 1.5),
                        ),
                        child: Icon(
                          ok ? Icons.check : Icons.close,
                          size: 7,
                          color: Colors.white,
                        ),
                      ),
                    ),
                ],
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}
