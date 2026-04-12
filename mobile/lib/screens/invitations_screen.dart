import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../widgets/app_drawer.dart';

class InvitationsScreen extends StatefulWidget {
  const InvitationsScreen({super.key});

  @override
  State<InvitationsScreen> createState() => _InvitationsScreenState();
}

class _InvitationsScreenState extends State<InvitationsScreen>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  List<Map<String, dynamic>> _invitations = [];
  bool _loading = true;
  String? _error;
  final Set<String> _responding = {};
  TabController? _tabController;

  static const _tabs = ['P', 'AT', 'NG'];
  static const _tabLabels = ['待回覆', '已接受', '已拒絕'];

  @override
  void initState() {
    super.initState();
    _tabController ??= TabController(length: 3, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabController?.dispose();
    super.dispose();
  }

  Future<void> _logout() async {
    if (!mounted) return;
    await Provider.of<AuthProvider>(context, listen: false).logout();
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/login');
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final data = await _api.getMyInvitations();
      if (mounted) setState(() { _invitations = data; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _loading = false; _error = e.toString(); });
    }
  }

  Future<void> _respond(String attendId, String action) async {
    setState(() => _responding.add(attendId));
    try {
      await _api.respondToInvitation(attendId, action);
      if (mounted) {
        // Update status locally instead of removing
        setState(() {
          final idx = _invitations.indexWhere((i) => i['attend_id'] == attendId);
          if (idx != -1) {
            _invitations[idx] = Map.from(_invitations[idx])
              ..['status'] = action == 'accept' ? 'AT' : 'NG';
          }
          _responding.remove(attendId);
        });
        // Switch to the corresponding tab
        _tabController?.animateTo(action == 'accept' ? 1 : 2);
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

  List<Map<String, dynamic>> _filtered(String status) =>
      _invitations.where((i) => i['status'] == status).toList();

  int _count(String status) => _filtered(status).length;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('invitations'.tr()),
        bottom: TabBar(
          controller: _tabController!,
          tabs: List.generate(3, (i) {
            final count = _count(_tabs[i]);
            return Tab(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_tabLabels[i]),
                  if (count > 0) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: Colors.white30,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text('$count',
                          style: const TextStyle(fontSize: 11, color: Colors.white)),
                    ),
                  ],
                ],
              ),
            );
          }),
        ),
      ),
      drawer: AppDrawer(onLogout: _logout),
      floatingActionButton: FloatingActionButton(
        heroTag: 'ai_chat',
        onPressed: () => Navigator.pushNamed(context, '/home'),
        backgroundColor: Colors.black,
        child: const Icon(Icons.smart_toy_outlined, color: Colors.white),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline, size: 48, color: Colors.red[300]),
                      const SizedBox(height: 12),
                      Text(_error!, style: const TextStyle(color: Colors.red)),
                      const SizedBox(height: 16),
                      ElevatedButton(onPressed: _load, child: const Text('重試')),
                    ],
                  ),
                )
              : TabBarView(
                  controller: _tabController!,
                  children: _tabs.map((status) {
                    final items = _filtered(status);
                    if (items.isEmpty) {
                      return Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.mail_outline, size: 64, color: Colors.grey[300]),
                            const SizedBox(height: 16),
                            Text(
                              status == 'P' ? '目前沒有待回覆的邀請'
                                  : status == 'AT' ? '沒有已接受的邀請'
                                  : '沒有已拒絕的邀請',
                              style: TextStyle(color: Colors.grey[600]),
                            ),
                          ],
                        ),
                      );
                    }
                    return RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: items.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, i) => _buildCard(items[i], status),
                      ),
                    );
                  }).toList(),
                ),
    );
  }

  Widget _buildCard(Map<String, dynamic> inv, String status) {
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
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.person_outline, size: 16, color: Colors.black54),
                const SizedBox(width: 4),
                Text('${inv['inviter_name']} 邀請您',
                    style: const TextStyle(color: Colors.black54, fontSize: 13)),
                const Spacer(),
                if (status == 'AT')
                  _statusChip('已接受', Colors.green)
                else if (status == 'NG')
                  _statusChip('已拒絕', Colors.red),
              ],
            ),
            const SizedBox(height: 6),
            Text(inv['title'] ?? '',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            if (timeStr != null) ...[
              const SizedBox(height: 4),
              Row(children: [
                const Icon(Icons.access_time, size: 14, color: Colors.black45),
                const SizedBox(width: 4),
                Text(timeStr,
                    style: const TextStyle(color: Colors.black54, fontSize: 13)),
              ]),
            ],
            if (inv['location'] != null && (inv['location'] as String).isNotEmpty) ...[
              const SizedBox(height: 4),
              Row(children: [
                const Icon(Icons.location_on_outlined, size: 14, color: Colors.black45),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(inv['location'],
                      style: const TextStyle(color: Colors.black54, fontSize: 13),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                ),
              ]),
            ],
            if (status == 'P') ...[
              const SizedBox(height: 14),
              Row(children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: isResponding ? null : () => _respond(attendId, 'decline'),
                    style: OutlinedButton.styleFrom(foregroundColor: Colors.red[700]),
                    child: const Text('拒絕'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: isResponding ? null : () => _respond(attendId, 'accept'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.black,
                      foregroundColor: Colors.white,
                    ),
                    child: isResponding
                        ? const SizedBox(
                            width: 16, height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Text('確認參與'),
                  ),
                ),
              ]),
            ] else ...[
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: isResponding ? null : () => _respond(attendId, status == 'AT' ? 'decline' : 'accept'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: status == 'AT' ? Colors.red[700] : Colors.black,
                  ),
                  child: isResponding
                      ? const SizedBox(
                          width: 16, height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : Text(status == 'AT' ? '改為拒絕' : '改為接受'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _statusChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        border: Border.all(color: color.withValues(alpha: 0.4)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 12)),
    );
  }
}
