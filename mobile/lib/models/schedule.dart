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
  final List<String>? attendIds;
  final List<Map<String, dynamic>>? attends; // Added attends list
  final String? contactName;
  final String? contactEmail;
  final String? contactPhone;
  final String? contactLineId;

  final String? cancelReason;
  final bool? isOnline;
  final bool? isOwner;
  final String? creatorName;

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
    this.attendIds,
    this.attends,
    this.cancelReason,
    this.contactName,
    this.contactEmail,
    this.contactPhone,
    this.contactLineId,
    this.isOnline,
    this.isOwner,
    this.creatorName,
  });

  factory Schedule.fromJson(Map<String, dynamic> json) {
    return Schedule(
      id: json['id'] as String? ?? '', // Handle possible mismatch
      title: json['title'] as String? ?? 'No Title', // Handle null title
      description: json['description'] as String?,
      startTime: DateTime.parse(json['start_time'] ?? json['startTime'] ?? DateTime.now().toIso8601String()),
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'])
          : (json['endTime'] != null ? DateTime.parse(json['endTime']) : null),
      location: json['location'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      status: _normalizeStatus(json['status'] as String?),
      transportMode: json['transport_mode'] as String? ?? json['transportMode'] as String? ?? 'car',
      cancelReason: json['cancel_reason'] as String?,
      contactName: json['contact_name'] as String?,
      contactEmail: json['contact_email'] as String?,
      contactPhone: json['contact_phone'] as String?,
      contactLineId: json['contact_line_id'] as String?,
      attendIds: (json['attend_ids'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList(),
      attends: (json['attends'] as List<dynamic>?)
          ?.map((e) => e as Map<String, dynamic>)
          .toList(),
      isOnline: json['is_online'] == true,
      isOwner: json['is_owner'] != false,
      creatorName: json['creator_name'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'start_time': startTime.toIso8601String(),
      'end_time': endTime?.toIso8601String(),
      'location': location,
      'latitude': latitude,
      'longitude': longitude,
      'transport_mode': transportMode,
      'attend_ids': attendIds,
      'attends': attends,
      'cancel_reason': cancelReason,
      'is_online': isOnline,
      'contact_name': contactName,
      'contact_email': contactEmail,
      'contact_phone': contactPhone,
      'contact_line_id': contactLineId,
      'is_owner': isOwner,
      'creator_name': creatorName,
    };
  }

  static String _normalizeStatus(String? status) {
    if (status == null || status == 'P') return 'PD';
    return status;
  }
}
