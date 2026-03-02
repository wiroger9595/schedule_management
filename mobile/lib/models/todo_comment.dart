class TodoComment {
  final int id;
  final String commentId;
  final String commentDescription;
  final String userId;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;

  TodoComment({
    required this.id,
    required this.commentId,
    required this.commentDescription,
    required this.userId,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  factory TodoComment.fromJson(Map<String, dynamic> json) {
    return TodoComment(
      id: json['id'],
      commentId: json['comment_id'],
      commentDescription: json['comment_description'],
      userId: json['user_id'],
      status: json['status'] ?? 'P',
      createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : DateTime.now(),
      updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'comment_description': commentDescription,
      'status': status,
    };
  }
}
