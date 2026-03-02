import 'package:flutter/material.dart';
import '../i18n/app_localizations.dart';
import 'calendar_screen.dart';
import 'todo_list_screen.dart';
import '../widgets/app_drawer.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

class TabbedDashboardScreen extends StatefulWidget {
  final int initialTabIndex;
  
  const TabbedDashboardScreen({Key? key, this.initialTabIndex = 0}) : super(key: key);

  @override
  _TabbedDashboardScreenState createState() => _TabbedDashboardScreenState();
}

class _TabbedDashboardScreenState extends State<TabbedDashboardScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: 2,
      vsync: this,
      initialIndex: widget.initialTabIndex,
    );
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) {
        setState(() {}); // Rebuild to update AppBar title
      }
    });
  }

  @override
  void dispose() {
    _tabController.removeListener(() {});
    _tabController.dispose();
    super.dispose();
  }

  void _logout() async {
    await Provider.of<AuthProvider>(context, listen: false).logout();
    Navigator.pushReplacementNamed(context, '/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TabBar(
          controller: _tabController,
          labelColor: Colors.black,
          unselectedLabelColor: Colors.grey,
          indicatorSize: TabBarIndicatorSize.label,
          indicatorWeight: 3.0,
          indicatorColor: Colors.black,
          isScrollable: true,
          labelPadding: EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          tabs: [
            Tab(
              child: Text(AppLocalizations.of(context)?.calendar ?? 'Calendar', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
            Tab(
              child: Text(AppLocalizations.of(context)?.todoList ?? 'Todo List', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        centerTitle: true,
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: IconThemeData(color: Colors.black87),
      ),
      drawer: AppDrawer(onLogout: _logout),
      body: TabBarView(
        controller: _tabController,
        children: [
          // Inner contents. Since these are whole screens, we ensure they don't have overlapping AppBars.
          CalendarScreen(isEmbedded: true),
          TodoListScreen(isEmbedded: true),
        ],
      ),
    );
  }
}
