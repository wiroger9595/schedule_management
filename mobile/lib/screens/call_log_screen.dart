import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:call_log/call_log.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:intl/intl.dart';
import 'dart:io';
import 'package:flutter/foundation.dart';

class CallLogScreen extends StatefulWidget {
  @override
  _CallLogScreenState createState() => _CallLogScreenState();
}

class _CallLogScreenState extends State<CallLogScreen> {
  List<CallLogEntry> _callLogs = [];
  bool _isLoading = true;
  bool _permissionDenied = false;
  bool _isIOS = !kIsWeb && Platform.isIOS;

  @override
  void initState() {
    super.initState();
    _loadCallLogs();
  }

  Future<void> _loadCallLogs() async {
    if (_isIOS) {
      setState(() {
        _isLoading = false;
      });
      return;
    }

    // Request permission
    var status = await Permission.phone.status;
    if (!status.isGranted) {
      status = await Permission.phone.request();
    }

    if (status.isGranted) {
      try {
        Iterable<CallLogEntry> entries = await CallLog.get();
        setState(() {
          _callLogs = entries.take(100).toList(); // Limit to 100 recent calls
          _isLoading = false;
          _permissionDenied = false;
        });
      } catch (e) {
        debugPrint('Error fetching call logs: $e');
        setState(() {
          _isLoading = false;
          _permissionDenied = true;
        });
      }
    } else {
      setState(() {
        _isLoading = false;
        _permissionDenied = true;
      });
    }
  }

  IconData _getCallIcon(CallType? type) {
    switch (type) {
      case CallType.incoming:
        return Icons.call_received;
      case CallType.outgoing:
        return Icons.call_made;
      case CallType.missed:
        return Icons.call_missed;
      case CallType.rejected:
        return Icons.call_missed_outgoing;
      default:
        return Icons.phone;
    }
  }

  Color _getCallColor(CallType? type) {
    switch (type) {
      case CallType.incoming:
        return Colors.green;
      case CallType.outgoing:
        return Colors.black87;
      case CallType.missed:
        return Colors.red;
      case CallType.rejected:
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }

  String _getCallTypeText(CallType? type) {
    switch (type) {
      case CallType.incoming:
        return 'incoming'.tr();
      case CallType.outgoing:
        return 'outgoing'.tr();
      case CallType.missed:
        return 'missed'.tr();
      case CallType.rejected:
        return 'rejected'.tr();
      default:
        return 'unknown'.tr();
    }
  }

  String _formatDuration(int? seconds) {
    if (seconds == null || seconds == 0)
      return 'notConnected'.tr();

    int hours = seconds ~/ 3600;
    int minutes = (seconds % 3600) ~/ 60;
    int secs = seconds % 60;

    if (hours > 0) {
      return '$hours ${'hours'.tr()} $minutes ${'minutes'.tr()} $secs ${'seconds'.tr()}';
    } else if (minutes > 0) {
      return '$minutes ${'minutes'.tr()} $secs ${'seconds'.tr()}';
    } else {
      return '$secs ${'seconds'.tr()}';
    }
  }

  String _formatTimestamp(int? timestamp) {
    if (timestamp == null) return '';

    DateTime dateTime = DateTime.fromMillisecondsSinceEpoch(timestamp);
    DateTime now = DateTime.now();
    DateTime today = DateTime(now.year, now.month, now.day);
    DateTime yesterday = today.subtract(Duration(days: 1));
    DateTime callDate = DateTime(dateTime.year, dateTime.month, dateTime.day);

    if (callDate == today) {
      return '${'today'.tr()} ${DateFormat('HH:mm').format(dateTime)}';
    } else if (callDate == yesterday) {
      return '${'yesterday'.tr()} ${DateFormat('HH:mm').format(dateTime)}';
    } else {
      return DateFormat('MM/dd HH:mm').format(dateTime);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('callLog'.tr()),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _isIOS
                ? null
                : () {
                    setState(() {
                      _isLoading = true;
                    });
                    _loadCallLogs();
                  },
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isIOS) {
      return Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.phone_disabled, size: 80, color: Colors.grey[400]),
              SizedBox(height: 24),
              Text(
                'iosLimitation'.tr(),
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 16),
              Text(
                'iosLimitationDesc'.tr(),
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16, color: Colors.grey[600]),
              ),
              SizedBox(height: 8),
              Text(
                'androidOnly'.tr(),
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: Colors.grey[500]),
              ),
            ],
          ),
        ),
      );
    }

    if (_isLoading) {
      return Center(child: CircularProgressIndicator());
    }

    if (_permissionDenied) {
      return Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.block, size: 80, color: Colors.red[300]),
              SizedBox(height: 24),
              Text(
                'permissionRequired'.tr(),
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 16),
              Text(
                'permissionDesc'.tr(),
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16, color: Colors.grey[600]),
              ),
              SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: () async {
                  await openAppSettings();
                },
                icon: Icon(Icons.settings),
                label: Text('openSettings'.tr()),
              ),
            ],
          ),
        ),
      );
    }

    if (_callLogs.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.phone_disabled, size: 80, color: Colors.grey[400]),
            SizedBox(height: 16),
            Text(
              'noCallLogs'.tr(),
              style: TextStyle(fontSize: 18, color: Colors.grey[600]),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadCallLogs,
      child: ListView.builder(
        itemCount: _callLogs.length,
        itemBuilder: (context, index) {
          CallLogEntry entry = _callLogs[index];
          return ListTile(
            leading: CircleAvatar(
              backgroundColor: _getCallColor(entry.callType)?.withOpacity(0.2),
              child: Icon(
                _getCallIcon(entry.callType),
                color: _getCallColor(entry.callType),
              ),
            ),
            title: Text(
              entry.name ??
                  entry.number ??
                  'unknownNumber'.tr(),
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (entry.name != null && entry.number != null)
                  Text(entry.number!, style: TextStyle(fontSize: 12)),
                SizedBox(height: 2),
                Row(
                  children: [
                    Text(
                      _getCallTypeText(entry.callType),
                      style: TextStyle(
                        color: _getCallColor(entry.callType),
                        fontSize: 12,
                      ),
                    ),
                    Text(' • ', style: TextStyle(fontSize: 12)),
                    Text(
                      _formatDuration(entry.duration),
                      style: TextStyle(fontSize: 12),
                    ),
                  ],
                ),
              ],
            ),
            trailing: Text(
              _formatTimestamp(entry.timestamp),
              style: TextStyle(fontSize: 12, color: Colors.grey[600]),
            ),
            onTap: () {
              // Could add action to call back
            },
          );
        },
      ),
    );
  }
}
