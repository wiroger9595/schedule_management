import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import '../models/todo_comment.dart';
import '../services/api_service.dart';

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
          SnackBar(content: Text('${'loadFailed'.tr()}: $e')),
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
          title: Text('addTodo'.tr()),
          content: TextField(
            controller: _textController,
            decoration: InputDecoration(
              hintText: 'enterTodo'.tr(),
              border: OutlineInputBorder(),
            ),
            maxLines: 2,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('cancel'.tr()),
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
                    SnackBar(content: Text('${'addFailed'.tr()}: $e')),
                  );
                }
              },
              child: Text('save'.tr()),
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
          title: Text('editTodo'.tr()),
          content: TextField(
            controller: _textController,
            decoration: InputDecoration(
              hintText: 'enterTodo'.tr(),
              border: OutlineInputBorder(),
            ),
            maxLines: 2,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('cancel'.tr()),
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
                    SnackBar(content: Text('${'updateFailed'.tr()}: $e')),
                  );
                }
              },
              child: Text('save'.tr()),
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
        SnackBar(content: Text('${'updateFailed'.tr()}: $e')),
      );
    }
  }

  void _showStatusDialog(TodoComment comment) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text('confirmTaskStatus'.tr()),
          content: Text('isTaskCompleted'.tr()),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('cancel'.tr(), style: TextStyle(color: Colors.grey)),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                _updateStatus(comment, 'N'); // 'N' for cancelled/invalid
              },
              child: Text('voided'.tr(), style: TextStyle(color: Colors.red)),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                _updateStatus(comment, 'Y'); // 'Y' for completed
              },
              style: ElevatedButton.styleFrom(backgroundColor: Colors.green[50]),
              child: Text('completed'.tr(), style: TextStyle(color: Colors.green[800])),
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
        SnackBar(content: Text('${'deleteFailed'.tr()}: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: widget.isEmbedded ? null : AppBar(
        title: Text('todoList'.tr()),
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
                      Text('noTodos'.tr(), style: TextStyle(color: Colors.grey[600], fontSize: 16)),
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
                          backgroundColor: isActive ? Colors.grey[200] : Colors.grey[300],
                          child: Icon(
                            isCompleted ? Icons.check : (isCancelled ? Icons.close : Icons.note_alt_outlined),
                            color: isActive ? Colors.black87 : Colors.grey[600]
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
                          '${'updatedAt'.tr()}: ${comment.updatedAt.toLocal().toString().split('.')[0]}',
                          style: TextStyle(color: Colors.grey[500], fontSize: 12),
                        ),
                        trailing: isActive
                            ? Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    icon: Icon(Icons.edit, color: Colors.black87),
                                    onPressed: () => _showEditDialog(comment),
                                    tooltip: 'edit'.tr(),
                                  ),
                                  IconButton(
                                    icon: Icon(Icons.check_circle_outline, color: Colors.green),
                                    onPressed: () => _showStatusDialog(comment),
                                    tooltip: 'changeStatus'.tr(),
                                  ),
                                ],
                              )
                            : Chip(
                                label: Text(isCompleted ? ('completed'.tr()) : ('voided'.tr())),
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
      floatingActionButton: widget.isEmbedded
          ? null
          : FloatingActionButton.extended(
              onPressed: _showAddDialog,
              icon: Icon(Icons.add),
              label: Text('addTodo'.tr()),
              backgroundColor: Colors.black,
            ),
    );
  }
}
