import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class InvitationsScreen extends StatefulWidget {
  const InvitationsScreen({super.key});

  @override
  State<InvitationsScreen> createState() => _InvitationsScreenState();
}

class _InvitationsScreenState extends State<InvitationsScreen> {
  final _api = ApiService();
  List<Map<String, dynamic>> _invitations = [];
  bool _loading = true;
  final Set<String> _responding = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await _api.getMyInvitations();
      if (mounted) setState(() { _invitations = data; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _respond(String attendId, String action) async {
    setState(() => _responding.add(attendId));
    try {
      await _api.respondToInvitation(attendId, action);
      if (mounted) {
        setState(() {
          _invitations.removeWhere((i) => i['attend_id'] == attendId);
          _responding.remove(attendId);
        });
        final verb = action == 'accept' ? '已確認參與' : '已拒絕邀請';
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(verb)));
      }
    } catch (e) {
      if (mounted) {
        setState(() => _responding.remove(attendId));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('操作失敗：$e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('活動邀請'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _invitations.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.mail_outline, size: 64, color: Colors.grey[300]),
                      const SizedBox(height: 16),
                      Text('目前沒有待回覆的邀請', style: TextStyle(color: Colors.grey[600])),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _invitations.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, i) {
                      final inv = _invitations[i];
                      final attendId = inv['attend_id'] as String;
                      final isResponding = _responding.contains(attendId);

                      String? timeStr;
                      if (inv['start_time'] != null) {
                        try {
                          final dt = DateTime.parse(inv['start_time']);
                          timeStr = DateFormat('MM/dd HH:mm').format(dt);
                        } catch (_) {}
                      }

                      return Card(
                        elevation: 1,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12)),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  const Icon(Icons.person_outline,
                                      size: 16, color: Colors.black54),
                                  const SizedBox(width: 4),
                                  Text(
                                    '${inv['inviter_name']} 邀請您',
                                    style: const TextStyle(
                                        color: Colors.black54, fontSize: 13),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                inv['title'] ?? '',
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold, fontSize: 16),
                              ),
                              if (timeStr != null) ...[
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    const Icon(Icons.access_time,
                                        size: 14, color: Colors.black45),
                                    const SizedBox(width: 4),
                                    Text(timeStr,
                                        style: const TextStyle(
                                            color: Colors.black54,
                                            fontSize: 13)),
                                  ],
                                ),
                              ],
                              if (inv['location'] != null &&
                                  (inv['location'] as String).isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    const Icon(Icons.location_on_outlined,
                                        size: 14, color: Colors.black45),
                                    const SizedBox(width: 4),
                                    Expanded(
                                      child: Text(
                                        inv['location'],
                                        style: const TextStyle(
                                            color: Colors.black54,
                                            fontSize: 13),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                              const SizedBox(height: 14),
                              Row(
                                children: [
                                  Expanded(
                                    child: OutlinedButton(
                                      onPressed: isResponding
                                          ? null
                                          : () => _respond(attendId, 'decline'),
                                      style: OutlinedButton.styleFrom(
                                          foregroundColor: Colors.red[700]),
                                      child: const Text('拒絕'),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: ElevatedButton(
                                      onPressed: isResponding
                                          ? null
                                          : () => _respond(attendId, 'accept'),
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: Colors.black,
                                        foregroundColor: Colors.white,
                                      ),
                                      child: isResponding
                                          ? const SizedBox(
                                              width: 16,
                                              height: 16,
                                              child: CircularProgressIndicator(
                                                  strokeWidth: 2,
                                                  color: Colors.white))
                                          : const Text('確認參與'),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
