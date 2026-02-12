class Attend {
  final int? id;
  final String? attendId;
  final String? scheduleId;
  final String? userId;
  final int? contactId;
  final String? name;
  final String? email;
  final String? phone;
  final String? lineId;
  final String? status;
  final DateTime? updatedAt;

  Attend({
    this.id,
    this.attendId,
    this.scheduleId,
    this.userId,
    this.contactId,
    this.name,
    this.email,
    this.phone,
    this.lineId,
    this.status,
    this.updatedAt,
  });

  factory Attend.fromJson(Map<String, dynamic> json) {
    return Attend(
      id: json['id'] as int?,
      attendId: json['attend_id'] as String?,
      scheduleId: json['schedule_id'] as String?,
      userId: json['user_id'] as String?,
      contactId: json['contact_id'] as int?,
      name: json['name'] as String?,
      email: json['email'] as String?,
      phone: json['phone'] as String?,
      lineId: json['line_id'] as String?,
      status: json['status'] as String?,
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
      if (attendId != null) 'attend_id': attendId,
      if (scheduleId != null) 'schedule_id': scheduleId,
      if (userId != null) 'user_id': userId,
      if (contactId != null) 'contact_id': contactId,
      if (name != null) 'name': name,
      if (email != null) 'email': email,
      if (phone != null) 'phone': phone,
      if (lineId != null) 'line_id': lineId,
      if (status != null) 'status': status,
    };
  }
}
