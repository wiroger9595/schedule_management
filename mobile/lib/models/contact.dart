class Contact {
  final int? id;
  final String? contractId;
  final String? userId;
  final String? contactUserId;
  final String? nickName;
  final String? phone;
  final String? email;
  final String? lineId;
  final String? comment;
  final DateTime? createdAt;

  Contact({
    this.id,
    this.contractId,
    this.userId,
    this.contactUserId,
    this.nickName,
    this.phone,
    this.email,
    this.lineId,
    this.comment,
    this.createdAt,
  });

  factory Contact.fromJson(Map<String, dynamic> json) {
    return Contact(
      id: json['id'] as int?,
      contractId: json['contract_id'] as String?,
      userId: json['user_id'] as String?,
      contactUserId: json['contact_user_id'] as String?,
      nickName: json['nick_name'] as String?,
      phone: json['phone'] as String?,
      email: json['email'] as String?,
      lineId: json['line_id'] as String?,
      comment: json['comment'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
      if (contractId != null) 'contract_id': contractId,
      if (userId != null) 'user_id': userId,
      if (contactUserId != null) 'contact_user_id': contactUserId,
      if (nickName != null) 'nick_name': nickName,
      if (phone != null) 'phone': phone,
      if (email != null) 'email': email,
      if (lineId != null) 'line_id': lineId,
      if (comment != null) 'comment': comment,
    };
  }

  Contact copyWith({
    int? id,
    String? contractId,
    String? userId,
    String? contactUserId,
    String? nickName,
    String? phone,
    String? email,
    String? lineId,
    String? comment,
    DateTime? createdAt,
  }) {
    return Contact(
      id: id ?? this.id,
      contractId: contractId ?? this.contractId,
      userId: userId ?? this.userId,
      contactUserId: contactUserId ?? this.contactUserId,
      nickName: nickName ?? this.nickName,
      phone: phone ?? this.phone,
      email: email ?? this.email,
      lineId: lineId ?? this.lineId,
      comment: comment ?? this.comment,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}
