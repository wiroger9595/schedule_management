class Schedule {
  final String id;
  final String title;
  final String? description;
  final DateTime startTime;
  final DateTime? endTime;
  final String? location;
  final double? latitude;
  final double? longitude;
  final String status;
  final String transportMode; // car, motorcycle, transit, bike, walk
  final List<String>? attendeeIds;
  final String? contactName;
  final String? contactEmail;
  final String? contactPhone;
  final String? contactLineId;

  final String? cancelReason;

  Schedule({
    required this.id,
    required this.title,
    this.description,
    required this.startTime,
    this.endTime,
    this.location,
    this.latitude,
    this.longitude,
    required this.status,
    required this.transportMode,
    this.attendeeIds,
    this.cancelReason,
    this.contactName,
    this.contactEmail,
    this.contactPhone,
    this.contactLineId,
  });

  factory Schedule.fromJson(Map<String, dynamic> json) {
    return Schedule(
      id: json['id'],
      title: json['title'],
      description: json['description'],
      startTime: DateTime.parse(json['start_time'] ?? json['startTime']),
      endTime: json['end_time'] != null 
          ? DateTime.parse(json['end_time']) 
          : (json['endTime'] != null ? DateTime.parse(json['endTime']) : null),
      location: json['location'],
      latitude: json['latitude']?.toDouble(),
      longitude: json['longitude']?.toDouble(),
      status: json['status'] ?? 'P',
      transportMode: json['transport_mode'] ?? json['transportMode'] ?? 'car',
      cancelReason: json['cancel_reason'],
      contactName: json['contact_name'],
      contactEmail: json['contact_email'],
      contactPhone: json['contact_phone'],
      contactLineId: json['contact_line_id'],
      attendeeIds: (json['attendee_ids'] as List<dynamic>?)?.map((e) => e as String).toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'start_time': startTime.toIso8601String(),
      'location': location,
      'latitude': latitude,
      'longitude': longitude,
      'transport_mode': transportMode,
      'attendee_ids': attendeeIds,
      'cancel_reason': cancelReason,
      'contact_name': contactName,
      'contact_email': contactEmail,
      'contact_phone': contactPhone,
      'contact_line_id': contactLineId,
    };
  }
}
