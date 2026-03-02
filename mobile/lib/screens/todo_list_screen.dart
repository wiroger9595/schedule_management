import 'package:flutter/material.dart';
import '../models/todo_comment.dart';
import '../services/api_service.dart';
import '../i18n/app_localizations.dart';

class TodoListScreen extends StatefulWidget {
  final bool isEmbedded;
  
  const TodoListScreen({Key? key, this.isEmbedded = false}) : super(key: key);

  @override
  _TodoListScreenState createState() => _TodoListScreenState();
}

class _TodoListScreenState extends State<TodoListScreen> {
  final ApiService _apiService = ApiService();
  List<TodoComment> _comments = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadComments();
  }

  Future<void> _loadComments() async {
    setState(() => _isLoading = true);
    try {
      final comments = await _apiService.getComments();
      setState(() {
        _comments = comments;
        _isLoading = false;
      });
    } catch (e) {
      print("Error loading comments: $e");
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${AppLocalizations.of(context)?.loadFailed ?? "Load failed"}: $e')),
        );
      }
    }
  }

  void _showAddDialog() {
    final TextEditingController _textController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(AppLocalizations.of(context)?.addTodo ?? 'Add Todo'),
          content: TextField(
            controller: _textController,
            decoration: InputDecoration(
              hintText: AppLocalizations.of(context)?.enterTodo ?? 'Enter todo item...',
              border: OutlineInputBorder(),
            ),
            maxLines: 2,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(AppLocalizations.of(context)?.cancel ?? 'Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                if (_textController.text.trim().isEmpty) return;
                Navigator.pop(context);
                try {
                  await _apiService.createComment(_textController.text.trim());
                  _loadComments();
                } catch (e) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('${AppLocalizations.of(context)?.addFailed ?? "Add failed"}: $e')),
                  );
                }
              },
              child: Text(AppLocalizations.of(context)?.save ?? 'Save'),
            ),
          ],
        );
      },
    );
  }

  void _showEditDialog(TodoComment comment) {
    final TextEditingController _textController = TextEditingController(text: comment.commentDescription);
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(AppLocalizations.of(context)?.editTodo ?? 'Edit Todo'),
          content: TextField(
            controller: _textController,
            decoration: InputDecoration(
              hintText: AppLocalizations.of(context)?.enterTodo ?? 'Enter todo item...',
              border: OutlineInputBorder(),
            ),
            maxLines: 2,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(AppLocalizations.of(context)?.cancel ?? 'Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                if (_textController.text.trim().isEmpty) return;
                Navigator.pop(context);
                try {
                  await _apiService.updateComment(comment.id, _textController.text.trim(), comment.status);
                  _loadComments();
                } catch (e) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('${AppLocalizations.of(context)?.updateFailed ?? "Update failed"}: $e')),
                  );
                }
              },
              child: Text(AppLocalizations.of(context)?.save ?? 'Save'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _updateStatus(TodoComment comment, String newStatus) async {
    try {
      await _apiService.updateComment(comment.id, comment.commentDescription, newStatus);
      _loadComments();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${AppLocalizations.of(context)?.updateFailed ?? "Update failed"}: $e')),
      );
    }
  }

  void _showStatusDialog(TodoComment comment) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(AppLocalizations.of(context)?.confirmTaskStatus ?? 'Confirm Task Status'),
          content: Text(AppLocalizations.of(context)?.isTaskCompleted ?? 'Is this task completed?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(AppLocalizations.of(context)?.cancel ?? 'Cancel', style: TextStyle(color: Colors.grey)),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                _updateStatus(comment, 'N'); // 'N' for cancelled/invalid
              },
              child: Text(AppLocalizations.of(context)?.voided ?? 'Void', style: TextStyle(color: Colors.red)),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                _updateStatus(comment, 'Y'); // 'Y' for completed
              },
              style: ElevatedButton.styleFrom(backgroundColor: Colors.green[50]),
              child: Text(AppLocalizations.of(context)?.completed ?? 'Completed', style: TextStyle(color: Colors.green[800])),
            ),
          ],
        );
      },
    );
  }

  Future<void> _deleteComment(TodoComment comment) async {
    // Legacy delete function if needed, but we now use status updates exclusively usually.
    try {
      await _apiService.deleteComment(comment.id);
      _loadComments();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${AppLocalizations.of(context)?.deleteFailed ?? "Delete failed"}: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: widget.isEmbedded ? null : AppBar(
        title: Text(AppLocalizations.of(context)?.todoList ?? 'Todo List'),
        flexibleSpace: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Colors.purple[700]!, Colors.blue[700]!],
            ),
          ),
        ),
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : _comments.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.checklist, size: 64, color: Colors.grey[400]),
                      SizedBox(height: 16),
                      Text(AppLocalizations.of(context)?.noTodos ?? 'No todo items', style: TextStyle(color: Colors.grey[600], fontSize: 16)),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: EdgeInsets.all(12),
                  itemCount: _comments.length,
                  itemBuilder: (context, index) {
                    final comment = _comments[index];
                    final bool isActive = comment.status == 'P';
                    final bool isCompleted = comment.status == 'Y';
                    final bool isCancelled = comment.status == 'N';

                    return Card(
                      elevation: isActive ? 2 : 0,
                      color: isActive ? Colors.white : Colors.grey[100],
                      margin: EdgeInsets.symmetric(vertical: 6),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: isActive ? Colors.purple[100] : Colors.grey[300],
                          child: Icon(
                            isCompleted ? Icons.check : (isCancelled ? Icons.close : Icons.note_alt_outlined),
                            color: isActive ? Colors.purple[700] : Colors.grey[600]
                          ),
                        ),
                        title: Text(
                          comment.commentDescription,
                          style: TextStyle(
                            fontSize: 16,
                            height: 1.3,
                            decoration: isActive ? TextDecoration.none : TextDecoration.lineThrough,
                            color: isActive ? Colors.black87 : Colors.grey[500],
                          ),
                        ),
                        subtitle: Text(
                          '${AppLocalizations.of(context)?.updatedAt ?? "Updated at"}: ${comment.updatedAt.toLocal().toString().split('.')[0]}',
                          style: TextStyle(color: Colors.grey[500], fontSize: 12),
                        ),
                        trailing: isActive
                            ? Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    icon: Icon(Icons.edit, color: Colors.blue),
                                    onPressed: () => _showEditDialog(comment),
                                    tooltip: AppLocalizations.of(context)?.edit ?? 'Edit',
                                  ),
                                  IconButton(
                                    icon: Icon(Icons.check_circle_outline, color: Colors.green),
                                    onPressed: () => _showStatusDialog(comment),
                                    tooltip: AppLocalizations.of(context)?.changeStatus ?? 'Change Status',
                                  ),
                                ],
                              )
                            : Chip(
                                label: Text(isCompleted ? (AppLocalizations.of(context)?.completed ?? 'Completed') : (AppLocalizations.of(context)?.voided ?? 'Void')),
                                backgroundColor: isCompleted ? Colors.green[100] : Colors.red[50],
                                labelStyle: TextStyle(
                                  color: isCompleted ? Colors.green[800] : Colors.red[800],
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddDialog,
        icon: Icon(Icons.add),
        label: Text(AppLocalizations.of(context)?.addTodo ?? 'Add Todo'),
        backgroundColor: Colors.purple[700],
      ),
    );
  }
}
