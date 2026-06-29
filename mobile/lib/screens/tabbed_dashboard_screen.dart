import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'calendar_screen.dart';
import 'todo_list_screen.dart';
import '../theme/app_theme.dart';
import 'main_shell.dart';

class TabbedDashboardScreen extends StatefulWidget {
  final int initialTabIndex;
  const TabbedDashboardScreen({Key? key, this.initialTabIndex = 0}) : super(key: key);

  @override
  _TabbedDashboardScreenState createState() => _TabbedDashboardScreenState();
}

class _TabbedDashboardScreenState extends State<TabbedDashboardScreen>
    with SingleTickerProviderStateMixin {
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
      if (!_tabController.indexIsChanging) setState(() {});
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.surface,
        automaticallyImplyLeading: false,
        leading: IconButton(
          icon: const Icon(Icons.menu_rounded),
          color: AppTheme.textSecond,
          onPressed: () => MainShellState.scaffoldKey.currentState?.openDrawer(),
        ),
        title: Text(
          'calendar'.tr(),
          style: const TextStyle(
            color: AppTheme.textPrimary,
            fontWeight: FontWeight.w700,
            fontSize: 18,
          ),
        ),
        bottom: TabBar(
          controller: _tabController,
          labelColor: AppTheme.primary,
          unselectedLabelColor: AppTheme.textMuted,
          indicatorColor: AppTheme.primary,
          indicatorSize: TabBarIndicatorSize.label,
          indicatorWeight: 2.5,
          labelStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          unselectedLabelStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w400),
          tabs: [
            Tab(text: 'calendar'.tr()),
            Tab(text: 'todoList'.tr()),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          CalendarScreen(isEmbedded: true),
          TodoListScreen(isEmbedded: true),
        ],
      ),
    );
  }
}
